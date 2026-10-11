# v5.39 validation

Verified locally on October 8, 2026. Adds per-clip scheduling in Publishing while retaining publishing now. Earlier v5.36–v5.38 changes remain in the working tree. Model weights, dependencies and analysis-cache VERSION 10 are unchanged.

## Behavior

- Each clip can switch to **Schedule this post**. The form saves the exact export, displayed title/inline hashtags, description, destination and audience with a future date/time. Scheduling timezone defaults to this Mac's **America/Chicago** and is saved locally.
- Uses timezone rules to store UTC timestamps. Past or timezone-less dates are rejected. Skipped and repeated daylight-saving clock times need another time. Selected date/time values persist through page refreshes.
- YouTube uploads privately immediately with `status.publishAt`. A confirmed schedule appears as Scheduled; a processed private scheduled video is not marked Published/Used until public release is confirmed. An absent platform schedule remains Needs check. Uploaded schedules can be managed or cancelled in YouTube Studio. A late interrupted upload cannot send more bytes using an expired posting time.
- Instagram saves a local schedule without sending a network request. A separate elected background runner posts when due, survives browser closure and restarts pending work when the app opens. The Mac must remain awake and online. More than one hour late requires a new schedule. Cancellation returns an unstarted schedule to Draft and preserves its video/text.
- Local schedules retain upload receipts and continue only the original processed container. Missing receipts, disconnected accounts, changed files and uncertain publication require attention; they cannot start a duplicate upload. Shared upload locks serialize scheduling, cancellation and posting.
- **Scheduled posts**, workspace history and the original Publishing history show posting times and account/status details. Publishing now retains its existing flow.

## Checks

- Full regression suite: **516 tests passed in 86.655 seconds**, including the first 21 scheduling cases (`work/v539-validation/full-tests.log`).
- Final scheduling suite: **22 passed**, including an additional real background-runner start/restart test with an isolated temporary database and a future test schedule. Both test children were stopped after confirming persistence and runner election; no test clip was uploaded.
- Covers timezone/DST conversion, past dates, audience checks, YouTube metadata/private scheduling/receipts/publication confirmation, missing schedules, duplicate attempts, expired upload continuation, Instagram due/not-due behavior, locks, late jobs, authentication/file/account failures, uncertain publication, processing continuation, crash recovery, cancellation, failed reset and both UI schedule/cancel paths.
- Existing publishing workspace **20 tests** and social publisher **15 tests** passed independently; they are also included in the full suite. Ruff, `git diff --check` and dependency consistency checks passed.
- Live Chrome showed **v5.39**, America/Chicago scheduling, the schedule toggle, date/time controls and **Schedule to Indy Audible**. Inspected an existing scheduled YouTube receipt and its October 9, 12:30 PM local posting time in **Scheduled posts** without checking/changing it through the platform API. Screenshot: `work/v539-validation/scheduling.jpg`.
- Compared **598 existing video/audio/caption/transcript/model files** before and after live UI verification: none missing or changed. The existing scheduled receipt stayed identical. Another receipt appeared during live app use; validation did not press Publish/Schedule or upload any real clip. Evidence: `work/v539-validation/preservation.json`.
- Existing Streamlit deprecation and macOS FFmpeg/malloc notices still occur during checks.

## Sources and limits

- YouTube's native scheduling behavior follows the official [video status/publishAt documentation](https://developers.google.com/youtube/v3/docs/videos). Existing Google audit/account restrictions remain. A saved schedule is not a guarantee of eventual publication or a completed platform processing check.
- Scheduling/publication transport tests use mocked platform responses. The live schedule was inspected from its existing saved receipt; no new real platform upload or future public-release test was performed by validation.
- Instagram scheduling uses the existing publisher at the due time and requires the Mac awake/online. Shutdown/sleep can delay a post; more than one hour late pauses for rescheduling. This is not hosted scheduling.
- This release does not add automatic channel posting, bulk scheduling, TikTok direct posting or the future two-posts-per-hour rule. It preserves all local transcription, inference and editing.
