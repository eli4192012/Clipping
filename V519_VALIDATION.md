# v5.19 validation

## Installed model and local runtime

Qwen3.5-4B was downloaded to `models/qwen3.5-4b` from `mlx-community/Qwen3.5-4B-MLX-4bit`, pinned at `32f3e8ecf65426fc3306969496342d504bfa13f3`. Weights occupy 3,034,300,695 bytes; tokenizer/config files bring the download to about 3.06 GB. The recorded initial download took 247.1 seconds. `download_models.py --editor-only` then verified the files and marked the model ready without reinstalling any existing models.

The existing runtime is MLX LM 0.31.3, MLX 0.32.2 and Transformers 5.17.0 on an Apple A18 Pro Mac with 8 GiB RAM. No dependencies were installed or replaced. Direct requirements now require MLX LM 0.31.3 or newer; the committed dependency lock already includes this version.

Inference uses MLX LM's text-only Qwen3.5 support, which discards unused vision weights. The model's vision capabilities are not connected to sports review in this release. All model work runs locally with thinking disabled, greedy sampling, an 8,192-token prompt ceiling and 256-token prefill batches. The existing 3 GiB MLX allocation limit and serial model-worker lock remain in place. The limit is not a claim that total system memory usage is 3 GiB.

## Real inference comparison

The same two saved source neighborhoods and existing Higher quality transcripts used in the v5.16 comparison were tested afresh with each model. These are transcript editing/checking comparisons; no videos were retranscribed, altered or rendered. Network connections were prohibited during inference by replacing both socket connection entry points with failures, in addition to enabling Hugging Face and Transformers offline mode.

| Saved moment | Editor | Fresh task time | Peak MLX allocation | Result |
|---|---|---:|---:|---|
| Running-back cutting explanation | Qwen3.5 4B | 60.17 s | 2.657 GiB | Final source check rejected the edit; fewer than two checks had grounded evidence. |
| Running-back cutting explanation | Qwen3 4B | 43.38 s | 2.578 GiB | Checked 8.16 s edit saved. |
| Kicker / London discussion | Qwen3.5 4B | 50.64 s | 2.644 GiB | Final source check rejected missing context/meaning. |
| Kicker / London discussion | Qwen3 4B | 40.15 s | 2.534 GiB | Checked 12.46 s edit saved. |

Both models returned structurally invalid planning proposals on these two real examples, so the existing phrase-based fallback was used. Qwen3.5 rejected those final transcripts; Qwen3 accepted them with verified evidence. These results establish compatibility, timing and different approval behavior under the app's current prompts. They do not establish which model has better human editorial judgment or prove that every approved edit is correct. The app retains the rejection and review-evidence requirements instead of weakening them for the new model.

A separate synthetic four-sentence example did produce a valid Qwen3.5 model plan and independent grounded approval: 18.95 s of source became 12.23 s of kept speech, omitting the question. Fresh inference took 28.88 s and peaked at 2.587 GiB MLX allocation. It kept an unnecessary previous-episode reference, so this is a functioning integration check rather than evidence of excellent editing. A subsequent call through the production subprocess worker reused that checked decision in 0.26 s.

Qwen3 4B remains the recommended default when it is installed. Qwen3.5 is selectable as an experimental editor in Advanced settings; explicit saved choices are honored. This initial comparison does not justify automatically replacing the existing editor.

## Regression and preservation checks

211 tests passed in 13.906 seconds: all 201 existing tests plus ten model-selection, cache, offline-loading and UI checks. Checks cover separate model analysis paths, shared transcription paths, per-model topic proposals/checks and edit decisions, cached reopen without loading weights, incomplete-download handling, bounded prompts without text truncation, and preservation of legacy model settings when recovering older runs. Streamlit tests verified the recommended default, switching and saving model choices, and blocking analysis only for a missing selected model. A prior badge test now verifies the release from version.json instead of hardcoding the previous release.

The production `shorts_edit` subprocess cache call passed. Python compilation and `git diff --check` passed. The release badge is v5.19 and its report reads V519_VALIDATION.md. The analysis-cache VERSION was not changed for this release.

All 1,276 inventoried pre-existing files under data/, exports/ and models/ retained their file sizes and modification times. The new model occupies its own directory. Benchmark requests, failed attempts, successful decisions, timing/memory measurements and preservation inventories are under `work/v519-validation/`, excluded from Git along with all media and model weights.

## Limits

No full long-video reanalysis, blind human preference study, genre-wide evaluation, new video render, retention measurement or larger-context memory stress test was performed. Qwen3.5 can still propose poor cuts or reject usable ones, and memory/timing will vary with prompt size and other apps. Existing visual packaging and combined-video order remain unchanged. Downloading a newer model does not itself make the app equivalent to Opus Clip; further editorial improvements need measured validation.
