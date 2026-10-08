# v5.22 validation

## Actual problem and resulting behavior

The Social media tab previously seeded YouTube fields with a literal opening quote and up to 1,400 characters of the final transcript. Those defaults appeared before an explicit AI button was clicked. This made the app look as if its AI was merely copying speech, even when no AI writing had run.

Opening Social media now generates missing posting copy once with the selected local editor. Other tabs do not start posting inference. Old quoted placeholders are removed from the displayed fields, and legacy quoted descriptions are upgraded while separately edited titles are preserved. Existing manual titles/descriptions remain authoritative. Explicit generation can replace them when requested.

The writer proposes different hook headlines and a brief description in fresh words. A separate check filters unsupported titles and chooses by exact title text, avoiding ambiguous numerical indices. Available alternatives can be selected under More title ideas. The chosen headline also appears above the clip and in its download name. Inline hashtags fit within the complete 100-character title.

Long copied passages, generic title labels, unsupported absolutes and added uncertainty are rejected. A separate closing caution is written in a short paraphrase and checked explicitly; a single-sentence idea does not receive a duplicate closing summary. One correction attempt is allowed. Failures preserve saved files, leave the transcript out of description defaults and require an explicit retry rather than looping on each rerun.

The posting writer cache version is social-copy-3 because the generation/checking format changed. Older writer caches and all analysis/transcription caches remain on disk. User-visible numbering is v5.22; the analysis-cache VERSION was not changed for the badge. Streamlit 1.64 is required for tracking the active tab and is already present in the pinned runtime; no dependencies or models were installed.

## Real inference and live app

Qwen3.5 4B ran against the saved 30-second discussion of learning to win ugly. Direct offline inference with network socket connections prohibited took 34.371 seconds and peaked at 2.617 GiB MLX allocation. The checked title was:

> Why does winning ugly matter for teams early on? #TurnoverBattle #WinUgly

Its description was 116 characters, in two sentences: a brief argument for winning ugly early, followed by the warning against an ongoing 3–0 turnover margin. The final source check accepted all three title ideas and marked the closing qualification preserved.

The same selected Qwen3.5 writer completed automatic generation in the already-running app after opening Social media. The title field, short description, alternative-title control, clip heading and download name displayed the new copy. The resulting cache and posting package were saved locally. No publishing button was pressed, the check did not change an account connection, and this clip reused its existing export.

A production subprocess test with Qwen3 4B used the saved running-back explanation. Fresh generation and saving took 24.848 seconds; checked cache reuse took 0.001309 seconds. It retained one supported title, "Why does no cut mean maximum speed? #Momentum #Speed", and a seven-word description about preserving speed, power and momentum. Its other suggestions were discarded. These are integration examples, not proof of consistently excellent titles or scientifically precise wording.

Several development drafts made unsupported comparisons, copied closing speech or failed the checker. Shorter structured instructions, a separate closing-summary field and title selection by exact text improved these examples. Small models still sometimes reject valid paraphrases or approve overstated wording; the checks do not guarantee fidelity. The source check is a second call to the same local model, not an external fact checker. Timing varies, and the existing 3 GiB MLX allocation limit does not represent total system memory.

## Tests and preservation

240 tests passed in 13.257 seconds, including all previous 227 tests and thirteen new checks. Coverage includes copied/stitched descriptions, unsupported claims, hook selection, invalid choices, filtering title ideas, the closing caution, cache version migration, one-time automatic generation, explicit retries, preserving manual and other-platform text, upgrading legacy quoted descriptions, alternative selection, saved reopen and unchanged clip export count. Compilation and git diff checks passed.

The baseline inventory contained 1,381 existing files. Existing source videos, transcripts, model files and exports retained their sizes and modification times. The live generation updated the current clip's posting file and added its AI cache. The inventory also observed changes in an assembly draft, the social database and another project's metadata, plus new analysis/render/cover/posting files while the app remained in use. Those metadata files are not included in the media-preservation claim. No existing media or model file was replaced or deleted by this release.

Benchmarks, failed-draft evidence, test logs, the live screenshot and preservation inventories are under work/v522-validation/, excluded from Git. No long-video reanalysis was initiated for validation, and no blind title-preference study, virality/retention measurement, broad genre evaluation or live upload was performed. This release improves posting text; it does not change source cuts, opening overlays, Google verification or publication consent.
