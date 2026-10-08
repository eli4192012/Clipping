# v5.17 implementation report

## Findings from both repositories

Clipping already had the important editorial architecture: local Whisper, candidate discovery, a separate Qwen/MLX Shorts Editor, independently checked chronological ranges, shared video/audio/caption timing, cached alternatives, original comparisons, local reviews and optional publishing. It also already had manual/automatic portrait framing and three cached thumbnail choices. Replacing discovery, recreating thumbnails from scratch or importing another cloud analysis stack would duplicate or weaken that work.

The reference was inspected at [commit 4a478dff3dacd293eeb5e28335aa7c81d78b8f50](https://github.com/NaufalRizqullah/opensource-clipping/tree/4a478dff3dacd293eeb5e28335aa7c81d78b8f50), including actual engine, subtitle, camera, metadata, thumbnail and B-roll code. Its MIT license names Muhammad Naufal Rizqullah. This implementation adopts product ideas and uses independent local code; no reference implementation was copied.

## Ideas adopted and choices rejected

| Reference implementation inspected | Useful idea adopted here | Boundary of adoption |
|---|---|---|
| [Camera switching](https://github.com/NaufalRizqullah/opensource-clipping/blob/4a478dff3dacd293eeb5e28335aa7c81d78b8f50/clipping/studio/render_camera_switch.py) and [split screen](https://github.com/NaufalRizqullah/opensource-clipping/blob/4a478dff3dacd293eeb5e28335aa7c81d78b8f50/clipping/studio/render_split_screen.py) | Two-person presentation and held shots | Require confirmed label-to-position mapping; do not assign visible identities from label/face ordering. |
| [Subtitles](https://github.com/NaufalRizqullah/opensource-clipping/blob/4a478dff3dacd293eeb5e28335aa7c81d78b8f50/clipping/studio/subtitles.py) | Meaningful phrase emphasis | Emphasize sparse final-timeline phrases, with optional gentle scale; avoid repeated global keyword animation. |
| [Metadata](https://github.com/NaufalRizqullah/opensource-clipping/blob/4a478dff3dacd293eeb5e28335aa7c81d78b8f50/clipping/metadata.py) | Separate platform packages | Derive text/tags locally from kept speech; preserve manual copies and drafts. |
| [Thumbnail](https://github.com/NaufalRizqullah/opensource-clipping/blob/4a478dff3dacd293eeb5e28335aa7c81d78b8f50/clipping/studio/thumbnail.py) | Short hook on a saved cover | Extend existing ranked-frame choices; avoid one fixed timestamp and remote font dependency. |
| [B-roll](https://github.com/NaufalRizqullah/opensource-clipping/blob/4a478dff3dacd293eeb5e28335aa7c81d78b8f50/clipping/studio/broll.py) | Supplemental visuals at understandable points | Suggest subjects/reasons/source types only; no Pexels dependency, random stock download or automatic NFL footage insertion. |
| [Engine](https://github.com/NaufalRizqullah/opensource-clipping/blob/4a478dff3dacd293eeb5e28335aa7c81d78b8f50/clipping/engine.py) | Explain why a candidate might work | Retain grounded editorial assessments; omit its cloud AI requirements and viral-score framing. |

Glitch intros, constant transitions, aggressive effects, voiceovers, template proliferation and new scheduling infrastructure were rejected because they do not establish better edits and add distraction, processing or dependency costs. A 100-point score was not introduced: existing evidence cannot honestly support every dimension. Missing criteria remain visibly unknown.

## Architecture and files

The source → transcription → discovery → Shorts Editor → final timeline sequence is unchanged. The final timeline and caption-correction layer now feed a cached package containing literal hook text, entities, sparse emphasis, three posting packages, assessments and B-roll suggestions. Cached kept-frame sampling feeds a separate camera plan. The chosen timeline then renders once; optional covers reuse that final framing and source mapping. No new large-model stage exists.

| Files | Responsibility |
|---|---|
| final_package.py | Final-edit fingerprint, extractive hook, entities, emphasis, platform copy, B-roll suggestions and eight assessments. |
| visual_pacing.py | Bounded local face sampling, conservative crops/split/speaker plans and FFmpeg pacing filters. |
| packaging_ui.py | Look, Post and Advanced controls, saved copy and speaker-position confirmation. |
| creator_profile.py | Deduplicated descriptive summaries of existing local human reviews. |
| app.py | Four-tab review integration, final selected edit/corrections, cache reuse and richer review details. |
| engine.py, presentation.py | Shared timeline export with camera plans and sparse ASS emphasis; legacy render path retained. |
| clip_thumbnails.py | Eight sampled frames, three separated choices, optional clean-frame extraction and cover overlays. |
| social_ui.py | Platform-specific defaults for new drafts; preserves existing draft copy. |
| download_models.py | Explicit setup of pinned YuNet model/license when missing; no runtime download. |
| version.json, AGENTS.md, README.md, RELEASE_NOTES.md | v5.17 release and migration/workflow guidance. |
| V517_VALIDATION.md, this report | Evidence, timings, limitations and repository comparison. |
| tests/test_final_package.py, test_visual_pacing.py, test_packaged_export.py, test_packaging_ui.py, test_platform_copy.py | 22 new behavior, cache, UI and real-media regressions. |

## What the creator sees

Edit keeps the suggested/Balanced cut, meaningful on-demand Fast/Full Context alternatives and manual boundaries. Look holds framing, Off/Subtle/Dynamic pacing, captions, phrase emphasis and editable/hidden opening hooks. Post contains separate editable copy controls and on-request covers. Advanced holds source ranges, decisions, quality explanations, transcript context and B-roll suggestions. The library adds a descriptive local review profile.

New speech looks default to Subtle; a useful safe beat is required before any movement occurs. Automatic can show a stable pair without speaker labels. Active Speaker requires user verification of anonymous labels against visible left/right positions, then enforces a three-second hold and rejects small acknowledgements. It does not perform lip-sync or identity recognition. Manual framing remains available; automatic crops explicitly warn about omitted slides/objects/text. Automatic Sports framing keeps the full picture.

Existing saved looks do not silently gain effects. Apply style opts them into this package. Source videos, transcripts, prior runs, ratings, caption corrections and exports retain their locations. Metadata/covers have new independent caches; no bulk cache deletion or analysis-version change was made. Captions and copy track the selected edit; edits/corrections invalidate their fingerprint. Existing social drafts keep their manually saved text.

## Validation and measured benefit

See [V517_VALIDATION.md](V517_VALIDATION.md) for test counts, real measurements and limits. The two saved v5.16 edited speech timelines and SRTs remain identical, and decoded audio correlation is 1.0 before/after packaging. Inspected new exports show closer, stable subject framing. Sparse emphasis highlights the no-cut and secret-weapon/payoff language. The kicker gets one small semantic punch-in; the shorter running-back clip appropriately gets none. Clean covers avoid duplicate burned captions. A real two-person window successfully uses split screen without guessed speaker identity.

This establishes visible presentation improvements on these examples and preserves their prior editing checks. It does not establish higher retention, universally better cuts or human-approved audio joins. The editorial improvement measured against the original neighborhoods came from v5.16 and is preserved here, rather than claimed again as a new v5.17 result.

Fresh package + sampling + export added about 0.17 and 0.58 seconds over the two recorded export baselines. Optional improved covers took about 1.95–2.07 seconds instead of 0.29–0.37 seconds. Cached metadata/sampling/covers reopened in milliseconds or less. No transcription or additional MLX work was added; no full 34-minute processing-speed claim is made.

## Remaining weaknesses and recommended next release

Sparse face sampling can miss moving subjects and cannot understand important non-face content. Real labelled active-speaker conversations still need validation; split screen is the proven real-media fallback here. Eye/blink/expression heuristics are limited on the installed OpenCV build. Extractive English hook/emphasis rules can miss subtler good language and need manual review. Editorial assessments do not invent unknown ratings. Older reviews lack new descriptive fields, and no small rating sample influences automatic choices. B-roll remains suggestions only.

For v5.18, prioritize a repeatable human review set across interviews, podcasts and sports, with listening checks at every removed phrase and comparisons of full-picture/crop/split layouts. Improve join diagnostics and final-cut context checks from those results before adding more effects, a numeric ranking rubric or preference training. Then validate existing local speaker labels against real two-person footage before making active-speaker automation less manual.
