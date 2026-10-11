# v5.24 validation — opening text

## Scope

Implemented step 2 as an on-demand opening-text writer in **Look → Improve the opening with AI**. It reads the final kept transcript and the speech timed within the first three seconds, proposes short hooks, and checks a selected hook in a separate pass with the installed local editor. Applying it changes the existing text overlay from the first frame through three seconds. It does not move spoken starts, endings or internal source ranges.

The writer uses up to three unexcluded Good pattern records' saved opening/headline presentation observations. This is independent of full-record review flags. Other examples' titles, transcripts, names and analytics are not supplied as factual evidence. No model training, view prediction, discovery/ranking changes, new weights, retranscription or analysis-cache version change was added.

Opening suggestions have their own versioned cache keyed by final package fingerprint/text, first-speech timing, selected model identity and presentation lessons. Only a checked result is stored. Generation alone retains the current preview/style; Apply preserves other styling fields, including legacy styles. Failed fresh generation keeps the previous result. Manual editing and restoring the extractive hook clear AI provenance. Source changes warn when a previously applied opening needs another review. Sports and silent clips retain manual text.

## Verification

- **268 tests passed in 14.682 seconds**, including 15 new tests covering evidence boundaries, unsupported claims/acronyms/placeholders, meaningful source words, literal subject context, exact checked-option identity, strict boolean verdicts, invalid option filtering, bounded retry, empty speech, library lesson filtering, cache invalidation, cache reuse, failed-fresh preservation, full-editor Apply behavior, unchanged ranges/posting text, legacy manual styles, manual overrides, sports/silent handling and older loaded controls.
- The actual running app displayed v5.24. Its selected Qwen3.5 4B editor generated **“Why winning with turnovers shows true identity”** for the turnover/resilience clip. The source panel displayed literal subject/payoff words and a notice that the model checks its own draft. The final generation took approximately **26 seconds** in that live run; this is a small-sample measurement, not a whole-video estimate.
- Apply changed the previous 66-character quote, “Games are tough sometimes and you've got to find ways to win them,” to the new 46-character, seven-word opening. The actual preview rendered in approximately **7 seconds**. It loaded at readyState 4, **720 × 1280**, with duration **28.418005 seconds**, and showed the applied wording in the opening field.
- The ASS title event begins at **0.00** and ends at **3.00 seconds**. The rendered first frame was inspected for readable wrapping and placement. Old/new exports have identical duration, dimensions, audio packet bytes and timestamps, SRT bytes, and all ASS content outside the title event. Source boundaries, final speech, caption timing and saved social text were retained.
- The actual checked cache reopened with the worker patched to fail if invoked, in **0.007292 seconds**, confirming no model process was started.
- Of **1,478 existing inventoried files**, none were removed. Source videos, transcripts, existing exports, model files and the example library retained sizes/mtimes. All seven supplied originals retained their SHA-256 hashes. Only two existing finished-clip indexes were rewritten during review/validation. New opening caches, the explicitly applied style and its new export were added locally. The reviewed project's analysis, variants, diagnostics and posting package remained unchanged.

## Limits

Small-model trials produced weak wording, unsupported comparisons and malformed responses, sometimes approved by their own checker. These trials led to stricter lexical/schema guards and simpler prompts. Such guards are not an independent factual verifier: a supported topic word or exact quote does not prove that a paraphrase preserves meaning. The smaller editor's writing quality remains uneven; no reliable preference between models or overall quality improvement was established.

The UI therefore presents a suggestion for explicit review and Apply. Read the evidence, listen to the clip, and edit weak wording. Existing automatic transcripts may themselves contain mistakes; this feature reuses them without certifying their accuracy. No retention, virality or Opus-equivalence claim is made. Spoken opening selection, ending improvements and a comparison feature remain separate work.

Personal references, model outputs, preserved media and validation artifacts stay outside Git. Logs, inventories, the render/audio/subtitle comparison, the live UI screenshot and the inspected first frame are under work/v524-validation/ on this Mac.
