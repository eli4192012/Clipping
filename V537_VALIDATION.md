# v5.37 validation

Verified locally on October 8, 2026. Transcription, models and editing remain local; no dependencies or model weights changed. The analysis-cache VERSION remains 10. Earlier v5.36 changes are retained in the working tree.

## Recovery of the reported video

- Project: `data/youtube-6l7V9Eusyt8`, the Jack Doyle podcast. The failed foreground run reached moment 62 of 63 and reported its old processing time limit. Its source, Higher quality transcript, proposal list, 22 approved edit decisions and 62 attempt records were present.
- Used only matching saved Higher quality edits with the original 30–80 second settings and Qwen3 editor. Recovery did not load model weights or run inference. Existing overlap/coverage selection kept 18 distinct clip suggestions and excluded four overlapping edits.
- Saved the recovered selection under a separate `clips-…-recovered.json` filename with a partial-analysis report and the original settings in the project library. Full analysis and remaining visual/sound review are explicitly unfinished. Suggestions are renderable; they are not claimed to be 18 already exported MP4 files.
- Queued the original Higher quality settings for continuation, receipt `b58eabb3968641778e87b179f42689d7`, ahead of the other waiting upload. The running Balanced job was left intact and progressed from moment 47 to moment 64 of 81 during this work. Both runs share the existing serial heavy-job lock. The unfinished decision and previously unsuccessful checks may run again; approved decisions and transcription are reused.
- Compared 198 existing source, transcript and cache files with the before-recovery inventory: none missing or changed. Inventory, receipt and runtime evidence are under ignored `work/v537-recovery/`. Existing exports were not altered.

## Checks

- Full regression suite: **473 tests passed in 89.954 seconds** (`work/v537-recovery/full-tests.log`).
- Final recovery tests, including two additional processing-page regressions: **9 passed**. Covers approved-only recovery without inference, exact quality/model/duration identity, corrupt/unapproved cache rejection, separate final-result preservation, saved settings, no duplicate queue receipt, paused queue behavior, partial-result UI, failed-page refresh and already queued recovery.
- Worker tests: **8 passed**. A real child worker can finish after exceeding the configured wall time when review progress changes, including a topics caller that omits the newer timeout flag. Repeated unchanged progress still times out; callback failures still stop the child. The inherited heavy-job lock remains unchanged.
- Ruff, `git diff --check`, dependency consistency and pinned dependency/import checks passed. Existing Streamlit deprecation messages and the existing macOS duplicate FFmpeg-library class notices still appear during tests/import checks.
- Live Chrome UI showed v5.37, the saved-work recovery screen and the correct original queue continuation. Opened **Open recovered clips** and verified the collection displays **18** clips with an unfinished-analysis notice. Screenshot: `work/v537-recovery/recovered-clips.jpg`. Browser input briefly timed out on Rerun, but the resulting state confirmed that the rerun completed.

## Limits

- Full completion and automatic export of the queued continuations were still pending at validation time. No speed improvement, final clip count or remaining-time promise is made.
- Recovery supports cached Shorts Editor speech edits in Interview and Podcast modes. Missing/invalid/unapproved edits are not presented as checked clips. Sports and other incomplete analysis still retain their original source/transcript and can be resumed, but do not receive a partial speech-edit snapshot.
- Healthy topic reviews retain the existing one-hour inactivity and 24-hour total safety limits. Other worker deadlines remain unchanged. A stopped unfinished check can require another local inference call.
