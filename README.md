# VideoGen n8n workflow templates

Three importable workflows for turning approved source material into finished MP4s. They use only core n8n nodes, so no community-node installation is required.

## Templates

- [Create a narrated video from an approved script with VideoGen](templates/approved-script-to-narrated-video.json): Turn approved onboarding, product, or educational narration into an editable video and download its MP4. The script is spoken verbatim; the template does not write or summarize an article.
- [Convert an approved training deck to a narrated video with VideoGen](templates/training-deck-to-narrated-video.json): Convert an uploaded PDF or PowerPoint training deck into narrated video, wait for the export, and download the MP4.
- [Create a captioned video from an approved voiceover with VideoGen](templates/voiceover-to-captioned-video.json): Illustrate an existing approved voiceover with stock visuals and captions, then download the finished MP4 without replacing the original narration.

## Setup

1. Import a JSON file into n8n.
2. Create an **HTTP Header Auth** credential with **Name** `Authorization` and **Value** `Bearer YOUR_VIDEOGEN_API_KEY`. Get your own API key at https://app.videogen.io/api. Select the same credential on **Start VideoGen workflow** and **Get VideoGen run**.
3. Edit **Approved input**. Replace the sample script or uploaded file ID and set `approved` to `true` after review.
4. Run the workflow manually. The final node downloads the video into n8n binary property `data`.
5. Add a storage node such as Google Drive or S3 if the file must persist beyond the execution. A signed download link is not permanent storage.

Video generation is paid and consumes VideoGen credits. These workflows do not buy credits or change subscriptions. One manual execution starts one paid workflow; choose a short test input first. Automatic retries are enabled only for read-only status requests, never the generation POST. If a start response is lost, inspect your VideoGen runs before retrying.

## Input details

### Create a narrated video from an approved script with VideoGen

Replace `script` with your final narration. Set `approved` to true after review. This template requests stock visuals, narration, captions, and MP4 export. No avatar or generated video clips are requested.

### Convert an approved training deck to a narrated video with VideoGen

Upload your PDF or PowerPoint through VideoGen first and wait until processing finishes. Put its `vg_file_...` ID in `fileId`. Replace `slideScripts` with one approved narration string per slide. Delete the entire `slideScripts` field to use embedded speaker notes instead. An empty array makes every slide silent; missing entries make the remaining slides silent. File upload is a prerequisite and is not performed by this template.

### Create a captioned video from an approved voiceover with VideoGen

Upload your voiceover audio through VideoGen first and wait until processing finishes. Put its `vg_file_...` ID in `fileId`, select the correct language, and set `approved` to true. File upload is a prerequisite and is not performed by this template.

## Completion and recovery

Each workflow requests `autoExport: true`, polls the exact saved run ID, and downloads only after a successful export with an HTTPS download URL. Failure, cancellation, unknown status, mismatched IDs, or a 15-minute polling deadline stop the workflow. A local timeout does not cancel a remote job. Retrieve the original run ID to recover an existing export instead of starting another paid generation.

The workflows are inactive and manually triggered on import. Before adapting them to a scheduled or event trigger, add deduplication for the source record, persist the run ID, and handle errors. The templates do not provide a production job queue or automatic source-file upload.

## Documentation and verification

- [VideoGen API documentation](https://docs.videogen.io/)
- [API schema](https://api.videogen.io/openapi.json)
- [Official n8n node](https://github.com/video-gen/n8n-nodes-videogen), an alternative to these core-node recipes

See `VALIDATION.md` for the exact test environment and scope. Never put API keys, OAuth tokens, or signed download URLs into a public workflow or issue.

## License

MIT. Maintained for VideoGen. The JSON files contain synthetic sample narration and no private user material.

## Reproduce the fixture tests

Requires Node.js 22 or newer and Python 3. Install the pinned n8n development dependency, then run the tests in an isolated local user folder:

```sh
npm install --no-audit --no-fund
SCOUT_N8N_RUNTIME="$PWD" npm test
```

The fixture test suite starts a local HTTP server and uses synthetic authentication. It makes no paid VideoGen generation calls.

## Sample output

[Download the 9.6-second onboarding sample](examples/onboarding-sample.mp4). This is a separate live-service smoke test using AI illustrations, captions, and transitions. It is not the output of a live authenticated n8n execution or of the stock-visual recipe.
