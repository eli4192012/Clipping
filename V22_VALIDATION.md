## v2.2 checks

- 38 regression tests pass, including previous-answer fragments, speaker changes, required subject context, protected answer endings, silence padding, and rejecting timestamps outside a matching exchange.
- On the reported Balanced transcript, the final-drive question now begins at 115.10 seconds instead of including the 110.80–114.68-second fragments. The grouped answer still ends at 153.44 seconds before optional silence padding.
- Both local reviewers completed the same-exchange comparison at target 120s using the shared Balanced transcript. Both returned 115.10–153.76s, including 0.32s of safe trailing room. Their equal boundaries are a valid comparison result; neither passed the transcript completeness check on this imperfect transcript.
- Both actual comparison MP4 exports decoded successfully. UI checks passed for two previews, score and note saving, persistence after rerun, review history, version dialog, target entry, and back navigation.
- Live browser confirmed v2.2. No broad improvement in retention or model accuracy is claimed.
