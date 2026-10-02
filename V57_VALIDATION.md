# v5.7 validation

- 122 regression tests passed, including eight new tests for clipped-word detection, sentence warnings, question endings, safe outward proposals, invalid bounds, actual timestamp stepping and bad timing limits.
- Streamlit tests passed for word warnings, explicit repair, millisecond fields, real decoded frame previews and preview-only frame stepping with explicit Apply.
- A real source export using 1.201s–2.207s decoded successfully with the expected duration within audio/video packet rounding. Frame stepping uses decoded timestamps rather than a fixed FPS assumption.
- TransNet benchmark completed on six preserved problem exports. Runtime, detections, model provenance and measured process memory are documented in TRANSNET_BENCHMARK.md. Four additional shot transitions were visually inspected. No new large runtime or multiple AI models were installed.

Limitations: Word and sentence checks depend on transcription timing; they do not prove semantic or visual completeness. Millisecond input precision exceeds the temporal resolution of many source videos. Output encoding rounds to available media frames/audio packets. Frame previews show source footage, not final crop/captions. No exhaustive ground-truth shot annotations, live retention study or full-game benchmark was performed.
