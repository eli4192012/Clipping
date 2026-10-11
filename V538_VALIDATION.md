# v5.38 validation

Verified locally on October 8, 2026. Adds a dedicated Publishing workspace using the existing local queue, AI writer and YouTube/Instagram publishing backend. Earlier v5.36 and v5.37 work is retained. Model weights, dependencies and analysis-cache VERSION 10 are unchanged.

## Behavior

- Select multiple saved projects; selection, destination and new-post settings persist locally. Finished exports, exact final speech and saved manual/current AI posting text appear in one workspace.
- Preparation uses completed saved analysis, reuses existing captioned exports and only generates missing posting text. It runs in the durable local video queue and respects a paused queue. Partial recovered analysis is not submitted for automatic preparation.
- Each clip has editable title with inline hashtags, description, optional preview and one Publish button. The button saves the displayed text and uploads the exact export using the existing publisher. YouTube audience must be chosen before publishing; new-post visibility starts private.
- Existing posting attempts move to history. Receipt checks and continuation use the original upload; an additional check under the upload lock prevents competing tabs from posting another version of the same source clip.
- Failed AI checks preserve successful text and media. A newer preparation attempt replaces an older preparation warning. Confirmed publication retains the existing Used marker.

## Checks

- Full regression suite: **493 tests passed in 60.373 seconds**, before the final status-display regression was added (`work/v538-validation/final-full-tests.log`).
- Final workspace suite: **20 tests passed**. Covers project selection, exact export metadata, older captioned exports, reuse without inference/transcription, manual text, source-check failures, frozen posting text, mocked YouTube metadata/receipt, changed media, missing audience/copy, duplicate attempts under the upload lock, Instagram captions and draft title edits, durable preparation, paused queues, partial-analysis exclusion, one-button UI behavior, manual editing and successful retry status.
- Ruff, `git diff --check`, dependency consistency and pinned dependency/import checks passed. Existing Streamlit deprecations and macOS FFmpeg-library notices still appear during checks.
- Cataloged **157 exports across 28 saved projects with no catalog errors**. Compared **714 existing media, transcript, caption, posting and model files** against the existing before-change inventory: none missing or changed. Evidence is in `work/v538-validation/runtime-check.json`.
- Live Chrome UI showed **v5.38**, Publishing, the selected Sauce Gardner/Tyler Warren project, Indy Audible destination, visibility/audience choices and ready/missing/history lists. The workspace refreshes as local preparation changes. Screenshot: `work/v538-validation/publishing.jpg`.
- Live preparation reused this project's **four existing exports** and saved source-checked text for **three clips**. The fourth failed the AI writer's evidence check. A single retry reused the three successful copies and four exports; the remaining failure stayed visible with manual text fields available. Both queue receipts and the outcome are saved in `work/v538-validation/preparation-results.json`. No analysis or transcription was repeated.
- Existing active queue processing and foreground work were left intact. The earlier recovery continuation and following watched upload completed their existing work during this session.

## Limits

- **No real social upload or publication was performed.** Upload calls and account metadata were verified with mocked transport; the live connected destination was inspected read-only. End-to-end platform acceptance is not claimed.
- Direct publishing supports the existing YouTube and Instagram integrations. TikTok still uses the existing separate posting package. Existing Google audit/account requirements remain in effect.
- This release adds one Publish button per clip. It does not publish all selected projects automatically or introduce scheduling/autoposting.
- The existing AI writer can reject text it cannot verify against a clip. Such clips remain under Needs preparation rather than receiving a transcript copied into their description.
