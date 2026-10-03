# v5.20 validation

## Posting workflow

The clip's Social media tab can generate a YouTube title containing hashtags and a short description using the selected local 4B editor. Writing uses only the selected edit's final transcript, including caption corrections. It does not retranscribe the source, inspect unseen footage or rerender the clip. A connected social account is not required.

The full title must fit 100 characters, including hashtags. Generated tags must occur literally in the final speech, and the description has no separate hashtag block. The writer supplies supporting transcript quotes and a separate model call checks the proposed text. Invalid output gets one correction attempt; failure preserves saved posting text. A deterministic check also rejects added uncertainty when the source contains none. These checks reduce errors but do not establish factual truth or guarantee faithful summaries.

Writing runs on demand. A model/final-transcript cache reuses checked results; Generate fresh text explicitly requests new inference. The two fields remain editable. Legacy tags appear inline without rewriting their saved file until an explicit save. Existing reviewed publishing drafts keep their wording until Use current posting text in this draft is clicked and the draft is saved. Generating text never publishes a video.

## Real local inference

The production social-copy subprocess was tested with the final code and an existing kept transcript about Spencer Schrader's kicking and a London trip. Fresh generation, source checking and saving took 22.446 seconds. Reusing the same checked result took 0.000607 seconds. Its title was:

> First Downs Needed for Schrader's Golden Foot #SpencerSchrader #London #Golden

The description attributed the secret-weapon and protection remarks to the speaker, rather than claiming the remarks were verified facts. This is a working integration example, not a claim that this is an ideal title or that its writing will increase views.

Additional direct worker checks used existing running-back and kicker transcripts with network socket connections prohibited and Hugging Face/Transformers offline mode enabled. Qwen3 4B and Qwen3.5 4B both produced accepted inline-tag titles and descriptions. Running-back checks took 15.110 and 16.893 seconds respectively, with peak MLX allocation of 2.422 and 2.587 GiB. These earlier checks preceded the final speaker-attribution prompt adjustment; the production timing above measures the final code. A kicker draft that added "maybe" and "unclear" was rejected; its single correction attempt passed in 29.959 seconds overall.

Inference retains the existing serial worker lock, bounded prompts and 3 GiB MLX allocation limit. The allocation limit does not describe total system memory. Timing varies with the transcript, model and other applications. Qwen3 remains the recommended default; the existing experimental Qwen3.5 choice is honored.

## Regression and preservation

225 tests passed in 19.883 seconds, including all prior tests and fourteen new checks. New coverage exercises title limits without truncating words or tags, unsupported/duplicate tags, literal evidence, source-check rejection and repair, added uncertainty, model/final-clip cache identity, fresh regeneration, failure preservation, speechless clips and legacy inline display.

Streamlit integration tests verify the Social media tab, AI generation filling editable fields, saved copy reopening without inference, removal of separate hashtag inputs, publishing-composer defaults and draft updates requiring explicit action. Generation leaves the clip's export count unchanged. Failed fresh generation retains manual text. No publishing API was called by these tests.

Python compilation and git diff checks passed. The badge is v5.20; its report includes this file. The analysis-cache VERSION was not changed to update the badge.

All 1,341 inventoried pre-existing files under data/, exports/ and models/ retained their sizes and modification times, with no new files in those directories during validation. Benchmark text, measurements and inventories live under work/v520-validation/, excluded from Git. No model download or dependency installation was needed.

## Limits

No live account authorization or social-platform upload was performed. This release does not change Google's verification requirements. No human title-preference study, virality/retention measurement or broad genre evaluation was performed. A model can still summarize poorly or approve inaccurate wording; review titles and descriptions before posting. Silent or visual-only clips require manual posting text.
