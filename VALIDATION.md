# Validation

Verified on October 18, 2026 with n8n 2.43.7 and Node.js 24.15.0.

## Actual n8n execution tests

All three templates were imported into a temporary local n8n instance. Test copies executed against a local HTTP fixture using a synthetic HTTP Header Auth credential. The fixture checks authentication, captures request bodies, supplies API-shaped responses, and returns a synthetic binary file at the download step.

All 12 checks passed:

1. Approved script: one generation request, successful completion, binary download.
2. Uploaded training deck: one generation request, successful completion, binary download.
3. Uploaded voiceover: one generation request, successful completion, binary download.
4. Pending/running result: wait and poll again, then download once; no repeated generation POST.
5. Failed result: stop with no download.
6. Cancelled result: stop with no download.
7. Unknown status: stop with no download.
8. Polling deadline: stop with no download.
9. Mismatched workflow ID: stop with no download.
10. Successful status without a download URL: stop with no download.
11. Unapproved input: stop before any generation request.
12. Empty script: stop before any generation request.

The original production JSON files were also imported and exported through n8n. Nodes, connections, and settings were compared with the original files and were unchanged. Instance-specific export metadata was removed before publication.

## API schema checks

The three captured success-path request bodies were validated against `ScriptToVideoRequest`, `SlideshowToVideoRequest`, and `VoiceoverToVideoRequest` from the public live OpenAPI document at https://api.videogen.io/openapi.json. All passed.

## Live-service scope

A separate short onboarding script was generated successfully through the connected VideoGen service using AI illustrations. This checks service access and generation independently of n8n. It is not a live authenticated execution of the three published n8n templates, and it uses a different visual configuration from the stock-visual templates.

No live n8n VideoGen API credential was available in this execution environment. Live account authentication, stock selection, real media file ingestion, and final visual quality for each customer's input remain deployment checks. The deck and voiceover templates require an already uploaded and processed VideoGen file ID.

## Operational limits

- Generation uses paid VideoGen credits.
- A lost POST response may still correspond to a running paid job. The generation POST has no automatic retry.
- The 15-minute polling deadline does not cancel the remote job.
- Signed URLs expire. The workflow downloads the binary; attach durable storage for production retention.
- File uploads, source deduplication, scheduling, and source-record persistence are outside these manually triggered recipes.
