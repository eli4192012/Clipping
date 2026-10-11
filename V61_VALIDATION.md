# v6.1 validation

## What changed

- Normal queued video exports now prepare posting copy before the job completes: analysis, captioned exports, then AI titles with inline hashtags and descriptions. Progress follows those actual stages.
- A finished export opened in the editor queues missing text. Publishing also queues missing copy for existing exports in its selected projects. These text-only jobs use final saved speech and frozen export identities; they do not need the original source, a new analysis, transcription or rendering.
- Publishing reads checked AI-copy caches directly, including copy generated in the clip editor. Saved manual copy and reviewed drafts take precedence. The background writer checks again before saving so a manual edit made during inference is retained.
- Durable queue entries deduplicate automatic work by export and AI identity. Successful text is saved independently. Failed drafts remain visible with their reason and need an explicit retry or edit. Explicit queue pauses remain effective. Large clip lists show 12 clips per page, and the queue distinguishes copy-only jobs from clipping work.

## Verification

- Full suite: **526 tests passed in 94.003 seconds**. One earlier run caught a stale assertion expecting the previous queue API; that assertion was updated and the full suite passed.
- Final focused verification after pagination, progress-label and manual-copy adjustments: **30 publishing tests passed**, and **37 queue/export/UI tests passed**. These include two additional regression tests beyond the full-suite run.
- Covered automatic enqueue without blocking the page, repeat refreshes, bounded failure/retry, explicit pauses, direct AI-cache reuse, manual edits during generation, incomplete manual copy, existing posting receipts, changed export rejection, source-free older exports, paginated lists, and real captioned FFmpeg exports followed by saved posting copy.
- Syntax compilation and `git diff --check` passed. UI version is **v6.1**. Model weights, the posting-writer version and analysis-cache VERSION remain unchanged.

## Live local run

- Opening Publishing started **21 text-only project jobs for 138 missing posting packages** in the currently selected collection. No Prepare button was needed. The detached serial worker was observed writing and saving copy while the browser remained usable.
- The first project's six missing packages produced five saved AI packages and one evidence-ID validation failure. That failure stayed visible, and the next project continued processing. Refreshes did not create duplicate jobs or retry the rejected draft automatically.
- A later snapshot indexed **157 exports**, with **26 saved posting packages**, **3 review flags**, and no catalog errors. These are partial live results; the remaining backlog was still processing. This release does not claim every package in the backlog has finished.
- Live Publishing displayed a generated title containing #Colts, #NFL, #Football and #fyp, a filled description, and the existing Publish to Indy Audible button. Screenshot: `work/v61-validation/publishing.jpg`.
- **586 source/media/transcript/model files** retained their original sizes and modification times. All **17 saved posting records** matched the pre-validation snapshot, including scheduled and published receipts. No real Publish or Schedule action was performed during validation.

## Practical limits

AI writing takes additional local processing time. Keep the Mac awake while the backlog runs; completed text stays saved. The existing writer can still produce weak or inaccurate wording, even when its model-based source check accepts it. Review a prepared package before publishing. Rejected output is kept out of new saved posting text; the app does not substitute raw transcript text as a description. Clips without speech and incomplete manual drafts need manual text.

Evidence logs and snapshots are under `work/v61-validation/`. Existing source videos, transcripts, exports and posting history remain available.
