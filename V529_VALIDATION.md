# v5.29 validation

## Scope

Implements the confirmed reliability fixes from the external review: complete main dependency lock, safe export deadlines and real encoding progress, private error diagnostics, automatic regression checks, compatible analysis/timing cleanup and accurate setup documentation. No model caching/GPU change, editorial rewrite, cache filename migration or automatic publication is included.

## Local verification

- Python 3.13.14 on Apple Silicon; clean main environment installed from the regenerated lock, without installing TensorFlow into the main environment. All 99 installed packages satisfy their requirements. Direct pins and all 11 core imports pass without model downloads or Keychain access.
- Full suite: **348 tests passed in 29.612 seconds** in the existing environment and **348 passed in 35.085 seconds** in the clean environment. This is regression-test timing, not a video-analysis performance claim. Scoped Ruff syntax/name checks and `git diff --check` pass.
- Real FFmpeg exports verify continuous and multi-range clips, original audio frequencies/frame order, omitted speech, caption offsets, burned captions and portrait/silent media. ASS paths include spaces, apostrophes, commas, colons and brackets. Combined-video regression tests cover mixed formats, silent segments, chapters, subtitle offsets, unchanged-cache reuse and reordered assemblies.
- Real subprocess tests cover a silent hang, ignored SIGTERM, 2 MB stderr output, split/invalid progress lines, callback failure, error-tail redaction and child-process reaping. Injected export failures verify new partial MP4 removal while a previous export remains intact.
- Logging tests verify restricted file/directory permissions, rotation limits, exception-call locations without sensitive exception messages, worker-stack retention after temporary-folder cleanup and fallback behavior when logs cannot be written.
- Compared the previous and current `analysis_path` implementation for **51 saved settings/run combinations**: zero changed paths and zero invalid combinations. Cached analyses are reused without transcription; timing keys match the old implementation and damaged timing files fall back to estimates. Unknown saved settings fields remain intact.

## Automation and limits

GitHub Actions uses a standard `macos-15` Apple Silicon runner, Python 3.13 and pinned official actions. It installs the main lock in a fresh virtual environment, checks dependencies/imports, lints first-party code and runs all tests. Optional sound/alignment model downloads and real publishing are outside CI. Logs and personal media are not uploaded as artifacts.

The watchdog limit is `max(180, output_seconds * 12 + 60)` seconds. It is deliberately longer than the UI estimate and does not imply constant processing speed. Progress uses encoded output time and reaches completion only after the export succeeds. General logs keep types/locations rather than raw messages because provider/model exceptions can contain private data. Installed PyAV/OpenCV imports produce existing duplicate-class warnings on macOS; import and rendering checks succeed despite those warnings.

Evidence files are retained locally under `work/v529-validation/` and excluded from Git. The refreshed live app displays v5.29, reopens an existing seven-clip collection without analysis and loads a saved 12.71-second preview at 0:00 with video/subtitle download controls; the browser reports loaded media with no playback error. Screenshot proof remains local at `work/v529-validation/live-preview.png`.

Preservation audit: all **2,274 existing files** under `data/`, `exports/` and `models/` retain their original size and modification time; none were removed or modified by the fixes or validation. No publishing action was performed. GitHub check results are visible on the draft pull request after the branch is pushed.
