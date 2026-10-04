# v5.26 · Reviewed AI endings

The ending editor identifies the selected clip's main point and chooses a complete sentence ending before trailing material or another topic. **Edit → Improve the ending with AI** provides a local editor choice, the suggested last sentence, exact main-point/payoff quotes, the speech removed and the duration. A suggestion changes no boundary until **Apply this ending**. **Restore prior ending** removes that selection and reopens the earlier export.

## Source and persistence checks

Only sentence endpoints supported by the original saved timed transcript are offered. An endpoint reconstructs a prefix of the existing source ranges; it cannot change the opening, reorder speech, restore omitted internal gaps or synthesize words. Timing and interview guards reject cut-off words, unanswered questions and more than one detected question. Directly dependent closing qualifications are excluded before inference. A second local check evaluates meaning, standalone context, payoff, qualification retention, the opening promise and relevance of the last sentence. Both the main-point quote and payoff quote must match retained speech; the payoff must come from the final kept sentence.

The model receives this clip's selected transcript, offered endings, limited nearby context and a few presentation observations from the local example library. Example facts, media, transcripts and analytics are not passed to it. The existing local worker reuses transcription, runs offline, queues heavy work and makes at most one repair attempt. No model download, cloud inference or publishing is added. Cached suggestions and applied selections are separate. Failed reviews preserve earlier selections and caches. Changing the review editor does not change project settings. Changing opening text refreshes the review cache and warns about an earlier applied review while retaining the accepted speech cut.

Selections are stored per analysis and variant in a separate `.endings.json` file. Manual boundary changes clear that variant's ending selection. Discovery results, transcripts, caption corrections, styles, posting copy and earlier exports remain saved. The final rendered transcript, duration, payoff range and editing reasons are updated for the accepted ending. The UI version is v5.26; the analysis-cache version is unchanged. Completed jobs now show elapsed completion time instead of a remaining-time estimate.

## Automated validation

`.venv/bin/python -m unittest discover -s tests -q`: **292 tests passed** in the final run.

Nineteen new regressions cover safe prefix trims, exact retained quotes, invalid IDs and checker results, two-question rejection, dependent cautions, preserving internal gaps, keeping an already suitable ending, bounded failure, caching, explicit Apply, restoration without inference, source/manual-copy preservation, changed opening text, per-review model choice, silent/sports controls, manual boundary reset and refreshing older loaded controls. Updated decision metadata is also checked after applying an ending.

## Real local inference and running app

The existing London pub clip lasted **62.36 seconds**. The installed recommended Qwen3 4B editor selected the sentence describing the golden-signature London Eye prize, ending at **8.98 seconds**, before subsequent greetings and other topics. A direct offline model run completed in approximately **32 seconds**; the normal running-app worker completed in approximately **44 seconds**. Both produced the same endpoint and passed the six source checks. Generation created a checked cache without a new London export or applied selection.

In the running app, Apply rendered a standalone **8.98-second, 720 × 1280 MP4** in approximately four seconds. Restore reopened the original **62.36-second** preview. Reapplying reused the shorter saved render without another model call. The generated final package ends with the prize statement, and every subtitle timestamp is within the shorter video's duration. The first **8.3 seconds** of decoded mono audio at 16 kHz were sample-identical to the corresponding original export. A frame at 8.85 seconds decoded successfully and was visually inspected. These checks establish prefix preservation and playback, not a human listening assessment.

The experimental Qwen3.5 4B attempt on the same source failed the strengthened ending review and was not applied. A separate real Qwen3 interview test also failed after the bounded retry because its main-point quote did not meet the retained exact-quote requirement; that saved interview and its existing ending were unchanged. These failures are reported rather than converted into unchecked edits. They demonstrate why explicit review and a keep-current/manual fallback are necessary; they do not establish a general model ranking.

The before/after inventory covered **1,598 existing files** under data, exports and models. No file was removed. All **817 existing protected files** (source videos, transcripts, model files, exports and posting-copy files) retained their sizes and mtimes. For the ending test, only the London project's finished-clip index changed; new ending caches/selections, a final package, a render manifest and export files were added. The inventory also recorded sports-project outputs and a project-metadata update outside this ending test. Those were retained and are not evidence for ending quality. Private model outputs, media, inventories and screenshots are excluded from Git; the local proof is `work/v526-validation/ending-ui.png`.

## Limits

This is an on-demand suffix review of a selected clip, not a new automatic discovery pass or a broader comparison campaign. It cannot repair a poor opening or remove material inside the retained prefix. Speech boundary quality depends on the saved transcript; caption corrections cannot create new source endpoints. Sports and clips without complete timed speech use manual controls. The local model checks its own proposal, and sentence completion is not proof that an idea is complete. Listen to the proposed ending and joins before sharing. This release does not prove improved retention or views.
