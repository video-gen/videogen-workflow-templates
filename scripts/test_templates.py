"""Run imported templates in real n8n against a local, synthetic API fixture."""
import copy
import http.server
import json
import os
import pathlib
import subprocess
import threading
import time
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNTIME = pathlib.Path(os.environ.get('SCOUT_N8N_RUNTIME', str(ROOT)))
BIN = str(RUNTIME / 'node_modules/.bin/n8n')
WORK = RUNTIME / 'fixture-tests'
WORK.mkdir(exist_ok=True)
(ROOT / 'evidence').mkdir(exist_ok=True)
EVENTS = []

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        EVENTS.append({'method':'POST','path':self.path,'body':body,'auth':self.headers.get('Authorization') == 'Bearer synthetic-test-token'})
        self.send_json({'workflowRunId':'vg_work_fixture','projectId':'vg_proj_fixture','projectUrl':'https://app.videogen.io/project/vg_proj_fixture','status':'pending'})

    def do_GET(self):
        EVENTS.append({'method':'GET','path':self.path,'auth':self.headers.get('Authorization') == 'Bearer synthetic-test-token'})
        scenario = self.path.split('/')[1]
        if self.path.endswith('/download'):
            self.send_response(200)
            self.send_header('Content-Type','video/mp4')
            self.end_headers()
            self.wfile.write(b'\x00\x00\x00\x18ftypmp42SCOUT-SYNTHETIC-FIXTURE')
            return
        count = sum(e['path']==self.path for e in EVENTS)
        status = {'failure':'failed','cancelled':'cancelled','unknown':'surprise','timeout':'running','poll':'running' if count==1 else 'succeeded'}.get(scenario,'succeeded')
        self.send_json({'workflowRunId':'vg_work_wrong' if scenario=='wrongid' else 'vg_work_fixture','projectId':'vg_proj_fixture','projectUrl':'https://app.videogen.io/project/vg_proj_fixture','status':status,'downloadUrl':None if scenario=='missingurl' else 'https://files.videogen.test/fixture.mp4','progressPercentage':100 if status=='succeeded' else 50,'error':None})

    def send_json(self, value):
        self.send_response(200)
        self.send_header('Content-Type','application/json')
        self.end_headers()
        self.wfile.write(json.dumps(value).encode())

server = http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
base = f'http://127.0.0.1:{server.server_port}'
env = dict(os.environ, N8N_USER_FOLDER=str(RUNTIME/'test-user'), N8N_DIAGNOSTICS_ENABLED='false',
           N8N_VERSION_NOTIFICATIONS_ENABLED='false', N8N_TEMPLATES_ENABLED='false',
           N8N_LOG_LEVEL='error', N8N_RUNNERS_TASK_TIMEOUT='60', N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS='true')

def cli(*args, label):
    p = subprocess.run([BIN,*args],env=env,text=True,capture_output=True,timeout=180)
    (WORK/(label+'.log')).write_text(p.stdout+'\n'+p.stderr)
    return p

credentials = [{'id':'ScoutFixtureCredential','name':'Scout fixture auth','type':'httpHeaderAuth','data':{'name':'Authorization','value':'Bearer synthetic-test-token'}}]
(WORK/'credentials.json').write_text(json.dumps(credentials))
imported = cli('import:credentials','--input='+str(WORK/'credentials.json'),label='import-credentials')
if imported.returncode:
    raise SystemExit('Credential fixture import failed: '+imported.stdout[-2000:]+imported.stderr[-1000:])

templates = sorted((ROOT/'templates').glob('*.json'))
cases = [(p,'success') for p in templates]
cases += [(templates[0],s) for s in ['poll','failure','cancelled','unknown','timeout','wrongid','missingurl','unapproved','invalidinput']]
workflows = []
case_ids = []
for index,(path,scenario) in enumerate(cases):
    flow = json.loads(path.read_text())
    flow['id']='ScoutFixture'+str(index)
    flow['versionId']=str(uuid.uuid4())
    flow['name'] += ' fixture '+scenario
    for n in flow['nodes']:
        p=n['parameters']
        if n['name']=='Approved input':
            data=json.loads(p['jsonOutput'])
            data['approved']=scenario!='unapproved'
            if 'fileId' in data:
                data['fileId']='vg_file_fixture'
            if scenario=='invalidinput':
                data['script']=''
            p['jsonOutput']=json.dumps(data)
        elif n['name']=='Start VideoGen workflow':
            p['url']=base+'/'+scenario+'/start'
            n['credentials']={'httpHeaderAuth':{'id':'ScoutFixtureCredential','name':'Scout fixture auth'}}
        elif n['name']=='Get VideoGen run':
            p['url']=base+'/'+scenario+'/run'
            n['credentials']={'httpHeaderAuth':{'id':'ScoutFixtureCredential','name':'Scout fixture auth'}}
        elif n['name']=='Download finished MP4':
            p['url']=base+'/'+scenario+'/download'
        elif n['name']=='Prepare request' and scenario=='timeout':
            p['jsCode']=p['jsCode'].replace('Date.now() + 15 * 60 * 1000','Date.now() - 1')
    workflows.append(flow)
    case_ids.append((flow['id'],path.name,scenario))
(WORK/'workflows.json').write_text(json.dumps(workflows))
imported=cli('import:workflow','--input='+str(WORK/'workflows.json'),label='import-workflows')
if imported.returncode:
    raise SystemExit('Workflow import failed: '+imported.stdout[-2000:]+imported.stderr[-1000:])

results=[]
for flowid,filename,scenario in case_ids:
    start=len(EVENTS)
    execution=cli('execute','--id='+flowid,'--rawOutput',label=flowid+'-'+scenario)
    events=copy.deepcopy(EVENTS[start:])
    output=execution.stdout+'\n'+execution.stderr
    expected_success=scenario in ['success','poll']
    downloads=sum(e['path'].endswith('/download') for e in events)
    posts=[e for e in events if e['method']=='POST']
    guarded=scenario in ['unapproved','invalidinput']
    ok=(execution.returncode==0 if expected_success else execution.returncode!=0)
    ok=ok and downloads==(1 if expected_success else 0) and len(posts)==(0 if guarded else 1)
    ok=ok and all(e['auth'] for e in events if not e['path'].endswith('/download'))
    if posts:
        (WORK/(flowid+'-request.json')).write_text(json.dumps(posts[0]['body'],indent=2))
    result={'template':filename,'scenario':scenario,'passed':ok,'exitCode':execution.returncode,'postCount':len(posts),'downloadCount':downloads,'requestBodies':[e['body'] for e in posts]}
    results.append(result)
    print(json.dumps({k:v for k,v in result.items() if k!='requestBodies'}),flush=True)
    if not ok:
        print(output[-3500:],flush=True)
        break

server.shutdown()
(ROOT/'evidence'/'n8n-fixture-test-results.json').write_text(json.dumps({'runtime':'n8n 2.43.7','scope':'Actual n8n imports and executions against local synthetic HTTP API fixtures; no live VideoGen key used.','results':results},indent=2)+'\n')
if not all(r['passed'] for r in results) or len(results)!=len(cases):
    raise SystemExit(1)
