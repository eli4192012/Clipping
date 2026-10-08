# v5.31 validation · Sequential clipping and automatic exports

Validated on October 7, 2026, on the existing Apple Silicon Mac with Python 3.13.14. The app badge is v5.31. Editorial rules, transcription/model choices and `modes.VERSION` remain unchanged.

## Queue behavior

- Imported projects can be added together from **Video queue**, or individually from project setup. Each entry snapshots its source size/modification time and analysis settings. Duplicate active entries with the same source/settings are skipped.
- One exclusive runner finds clips and exports all selected suggestions before claiming the next video. The runner is separate from Streamlit and the browser. A SQLite transaction claims the next waiting item; a process lock prevents duplicate runners. The existing heavy-job lock serializes queue work with manual analysis/render jobs.
- Pause lets the current video finish and leaves subsequent items waiting. Waiting items can be reordered or removed without touching media. Failures retain completed analysis/exports and let subsequent videos continue; retries reuse saved work. A changed or missing source fails before new analysis rather than processing different media.
- Interrupted active entries resume in order when the app reopens. Paused queues stay paused. Model and FFmpeg children inherit the heavy-job lock, including foreground workers through a thread-local descriptor, preventing recovery from overlapping a surviving child. This does not require keeping a browser tab open.
- Exports use default studio presentation and saved caption corrections; existing manual styles/ranges remain available in their original editor records. The queue and editor share the existing render fingerprint. Export manifests and the finished-clip index make completed videos reopenable and available to Combine clips. No posting text or social publication is generated automatically by the queue.
- The runner starts macOS `caffeinate -i -w` for a temporary idle-sleep assertion. The assertion ends when the runner exits. Closing the lid, choosing Sleep, shutdown or power loss can still interrupt work. Progress combines actual analysis milestones, per-clip export completion and encoded-time updates. Analysis time is explicitly an estimate; export time is additional.

## Automated validation

`python -m unittest discover -s tests -q`: **389 tests passed in 25.916 seconds** in the main pinned environment. First-party Ruff checks and `git diff --check` passed. No dependencies or model weights were downloaded.

New tests cover persistent settings/order, duplicate prevention, waiting-item reorder/removal, failure continuation (including exceptions without a message), pause/resume, interrupted-run recovery, singleton election, waiting behind a foreground lock, source-change protection, analysis-only mode, export checkpoints, queued-project deletion protection, inherited locks after parent-handle closure and foreground-worker descriptor inheritance without global environment mutation.

Streamlit tests exercise multi-project add, automatic export defaults, reorder/remove, start/pause, opening saved results with their original settings, and sidebar navigation without an active project. Native FFmpeg tests export media with audio/captions, reopen manifests without rendering, preserve a successful export when another fails, retry only the missing export, complete empty selections and process two saved fixture analyses sequentially through the real export pipeline. The shared render-key test confirms compatibility with the previous editor fingerprint.

The full suite retains existing local AI boundary/source checks, real caption/video joins, combined-video exports, worker timeouts and diagnostics checks. Hosted checks run the same suite and fresh pinned install on Apple Silicon; status is shown on the pull request.

## Live app trial

Used the live v5.31 app to add these two existing projects with automatic exports enabled, then clicked **Start queue**:

| Order | Saved project | Selected clips | Available exported clips |
| --- | --- | --- | --- |
| 1 | DC Lou Anarumo is happy with the growth he’s seen from multiple position groups | 7 | 7 |
| 2 | Jonathan Taylor's patience pays off for six! | 1 | 1 |

The UI showed **Exporting clip 4 of 7** and one video waiting. Navigating to My projects did not stop processing. Both entries finished without errors; the first entry's finish timestamp preceded the second entry's start timestamp. The queue then disabled itself and the runner and its caffeinate process exited. Total queue time was **22.544 seconds**, with **saved analysis reused for both projects, four existing exports reused and four new clips rendered**. This is a cache/export trial, not a first-run AI-speed benchmark.

Probed all eight media files: each contains audio and 720×1280 video starting at zero. Their durations are consistent with the selected timelines: approximately 62.34, 23.63, 24.42, 28.17, 29.41, 37.62, 25.30 and 14.00 seconds. The local queue/results remained available after restarting Streamlit; there were no waiting jobs left. Queue history and its runtime media are ignored by Git.

This release adds orchestration; it does not claim new editorial-quality or audience gains. Sports clips retain the existing manual-review limitations. The unattended trial reused existing transcripts/analyses, so it does not benchmark transcription or model inference. Controlled tests verify interruption/failure recovery; no real source or existing export was deliberately interrupted or removed during the live trial.

## Preservation

Compared size and modification time against **2,367 existing data/export/model files**. **2,361 remained unchanged; none were removed.** Only project activity, saved-run and finished-clip registries for the two processed projects changed (six metadata files). All prior videos, transcripts, analyses, manual edits, exports and model files remained unchanged. Twenty-nine local runtime files were added, including the queue database, render manifests/packages and the four new clips with captions/timeline/framing files. No publishing or account changes occurred.
