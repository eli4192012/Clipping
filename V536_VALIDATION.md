# v5.36 validation · Automatic channel clips and recovery

## Changes

Connected channels display the actual count of existing captioned exports, current queue progress, scheduled retries and Open clips buttons for saved selections. Opening a selection uses its original project, settings and result file. Upload history is ordered by publication time. The existing discovery → serial download → transcript → AI selection → captioned export pipeline remains local.

Watched upload failures for resumable analysis time limits and recognized temporary HTTP/network errors automatically retry up to three times, after 1, 5 and 25 minutes. Other videos can run before a delayed retry. Enabled channel watchers recover previously failed uploads with those errors. Manual projects, permanent errors, completed/removed videos and explicit queue pauses retain their behavior. Each retry still checks source integrity, channel ownership and publication eligibility.

Topic review uses a progress-based deadline: changed review events renew the one-hour inactivity allowance. Rewriting an identical event does not renew it. A 24-hour overall ceiling remains. Other worker tasks retain their existing wall-clock deadlines. Transcript and completed editorial caches are reused.

An HTTP 403 from the preferred download gets one fresh extraction using available HLS streaming formats. The 720p and 4 GB limits remain. The implementation uses the already installed yt-dlp 2026.8.19, yt-dlp-ejs 0.8.0 and Node 26.4.0; no cookies, account login or dependency upgrades were introduced. The upstream [EJS setup guide](https://github.com/yt-dlp/yt-dlp/wiki/EJS) describes the existing JavaScript challenge support.

## Checks

- **464 tests passed in 146.449 seconds**, including real child-process progress/deadline tests, automatic retry backoff/budget/pause tests, legacy failure recovery, source preservation, channel UI navigation and the discovery-to-real-FFmpeg captioned export integration. The integration uses saved transcript/analysis fixtures and mocked YouTube transport; it does not claim fresh end-to-end AI inference on a future upload.
- After the final retry-wait wording adjustment, **13 channel/queue UI tests passed in 25.044 seconds**. The adjustment displays waiting for its turn when a retry is due, rather than implying an immediate start during another local job.
- After isolating progress parsing from callback errors, **14 worker/watchdog tests passed**. A failing progress callback stops and reaps the worker rather than being mistaken for a malformed progress event. This final targeted check supplements the full-suite run above.
- Ruff, pip dependency checks, pinned-install/core import checks and git diff whitespace checks passed. Existing AV class warnings and Streamlit test-context/deprecation warnings remain.
- Live metadata and bounded 1 KB network probes for the previously failed Buckner/Taylor upload succeeded for both selected HTTPS media formats and alternative HLS manifests. This verifies current access, not a completed download or immunity from future YouTube refusals. The fallback itself is covered by failure/success tests.
- The running app displayed v5.36, the connected Colts channel, **11 existing ready clips** (7 and 4 from two completed uploads), and both interrupted videos scheduled to retry. Open clips restored saved state in Streamlit UI tests. Further browser click/screenshot verification was interrupted by the browser connection; no screenshot is claimed.

## Runtime and preservation

The detached watcher was restarted with the new implementation. The channel remains enabled. The two existing failed upload receipts became delayed retry entries with the same IDs, source references and caches; the queue runner is waiting on the existing heavy-job lock while the user's foreground AI job continues. No foreground worker or app server was stopped. These two full real retries have not finished during validation.

A before/after inventory of **714 existing media, transcript, caption, posting-copy and model files** found no missing files and no size/modification-time changes. Queue/watch databases were backed up under ignored work/v536-validation before migration. Queue retry fields are added without clearing stored projects, settings, results, exports or pause intent. Tests, logs, runtime snapshots and backups remain local and ignored by Git. The UI badge is v5.36; analysis-cache modes.VERSION remains 10.

The Mac must remain on, awake and online. Persistent/private/unavailable YouTube content, exhausted retries, model faults or a paused queue can still require attention. No automatic publication, cloud hosting or new closed-lid behavior was added.
