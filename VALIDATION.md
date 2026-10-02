# First-version validation

Tested on this Apple Silicon Mac, September 26, 2026:

- Python compilation and Streamlit initial rendering passed.
- A generated 29-second spoken sample produced 91 timestamped words and nine sentences using the locally downloaded Whisper model.
- Qwen3 1.7B ran locally through MLX, returned valid structured editorial feedback, and selected the sample's full story.
- Both original-frame and 720×1280 portrait exports decoded successfully. Their duration matched the requested 17.4-second cut within 0.2 seconds; audio and subtitle streams were present.
- Streamlit's testing harness exercised the app with a supplied upload, cached transcription, basic clip selection, and export without exceptions.
- The live local page rendered in the in-app browser.

This verifies functionality on a synthetic sample, not editorial accuracy across real-world content. Long videos, noisy recordings, multiple speakers, and non-English editorial quality have not been validated. Test assets are in `work/`.

YouTube update: URL validation and stale-preview checks passed. Live lookup and download of the public 19-second video "Me at the zoo" succeeded, including separate audio/video merging. The cached import reached the Find my clips interface in the Streamlit test harness. An unavailable test URL returned a handled error.

Mode update: five regression tests pass for distinct speech policies, question/answer boundaries, strict non-overlap, total-footage limits, silent sports selection, and refusing to return a whole short video. All three modes completed their UI paths under the Streamlit harness. The saved 131.6-second source produced two non-overlapping sports drafts at approximately 69.1–88.6s and 114.1–131.6s, totaling 37 seconds. Export without captions passed. This does not validate complete-play recognition; sports boundaries remain heuristic and require visual review.

September 27 upgrades: all eight regression tests pass, including delayed motion settling, commentary completion, rejecting a cut as evidence of settling, and reapplying overlap limits after extending boundaries. Streamlit tests against the saved football source passed standalone rendering, context preview, saving an edited endpoint, and restoring the suggestion. Local server health is OK. Complete-play accuracy has not been established by these checks.

Local vision upgrade: downloaded and ran Qwen3-VL-2B-Instruct-4bit offline on the 8 GB Mac. Direct storyboard-to-timestamp selection was unreliable, so final inference describes individual frames and applies constrained sequence rules. On the supplied touchdown example, model outputs yielded an uncertain draft at 181.5–194.26 seconds, including the setup and original play (manually inspected at these source times), unlike the former 188.92-second start. The model misclassified some action frames and did not establish a full ordered sequence; this is not proof of reliable play detection. Only this real event has been evaluated end to end; other-play accuracy remains unvalidated. Sixteen regression tests cover event grouping, malformed output, missing frames, boundary ordering, mode warnings, and the existing clipping limits.

The integrated live export exceeded the Streamlit harness's 120-second wait under load, but completed as a valid 12.779-second MP4; its video stream decoded successfully. The server health endpoint passed after restart. This upgrade should be treated as an experimental local visual assistant, not validated production-quality sports segmentation.

Interview structure upgrade: 23 regression tests passed, including subject introductions, declarative next-question setup, unresolved pronouns, short complete answers, rejecting overlong answers, semantic ending bounds, and sports-interview routing. On the reported Colts interview, automatic grouping selected 143.54–168.86 seconds for Buckner and 169.70–197.58 seconds for the adjacent offensive-line exchange. The actual local model preserved both endings; it approved the Buckner transcript and left the other draft unapproved. The Buckner MP4 exported with the expected 25.32-second duration. UI tests reused those actual reviewed results and the completed export to verify mode routing, displayed bounds, and download controls. New analysis cache version 6 avoids reuse of the prior bad clip. These tests do not establish accuracy across all interview styles.

UI release v1.1: 25 regression tests passed. Streamlit AppTest exercised settings → processing → completion → collection → editor → collection using saved reviewed analysis and an existing export. No video render occurs on the completion or collection screens. Version badge and download/editor controls were present with no UI exceptions. A separate real basic-analysis smoke test on the 29-second local sample saved results and reported monotonic progress ending at 100%. Live browser inspection confirmed the redesigned start page. ETA tests verify that overruns remain labeled as still working instead of showing a false zero-second promise. This release changes the workflow and presentation, not clip-selection accuracy.

Version 2.1: see V2_VALIDATION.md for actual model, alignment, scene, UI, export, and broken-pipe import checks. 31 regression tests pass. Speaker detection awaits the user-controlled gated download; sports vision remains uncertain.

v2.2: 38 regression tests passed, actual two-model same-exchange comparison and both exports completed, and review-score persistence passed. See V22_VALIDATION.md.
