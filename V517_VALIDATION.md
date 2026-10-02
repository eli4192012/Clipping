# v5.17 validation

Validated on the existing Apple Silicon Mac with Python 3.13.14 and the locked dependencies. All **190 tests passed** in the final run (18.874 seconds), including all 168 previous tests and 22 new tests. Syntax compilation and git diff whitespace checks also passed.

## Test coverage

The 22 added tests cover final-transcript-only metadata, preserving negation and qualifications across adjoining editorial roles, sparse caption emphasis, edit/correction cache invalidation, grounded evidence and unknown criteria, descriptive review deduplication, safe scene fallback, stale speaker confirmations, acknowledgement filtering, minimum camera hold, Sports behavior and semantic-only zooms.

Real FFmpeg tests use timed colored source regions and audio. They check active-camera colors at expected times, split-screen output, progressive zoom encoding, unchanged duration, embedded/burned captions, caption-free cover extraction and cover-cache reuse. UI tests exercise four tabs, the release badge, selected-range exports, cached reopen, original-moment selection, disabled hooks/pacing, persisted custom posting text, legacy manual looks and collection assessments without rendering or inference. UI exports and background jobs are mocked; these tests do not wait behind a live local analysis job. Real media exports are tested separately.

## Existing editorial cuts versus original discovered moments

This release reuses the two saved v5.16 checked decisions and transcripts. It does not claim that new effects improved editorial meaning or selected a better cut.

| Measurement | Running-back cutting explanation | Kicker / London discussion |
|---|---:|---:|
| Original discovered neighborhood | 50.08 s | 61.82 s |
| Final kept speech | 8.16 s | 12.46 s |
| Encoded v5.17 output | 8.185 s | 12.471 s |
| Time to selected strong phrase, original → final | 25.18 → 0.88 s | 38.10 → 2.68 s |
| Opening setup omitted by existing editor | 24.30 s | 35.42 s |
| Ending omitted by existing editor | 17.62 s | 13.30 s |
| Actual internal gaps removed | 0 | 1 |
| Kept ranges versus v5.16 | Identical | Identical |
| SRT contents/timing versus v5.16 | Identical | Identical |
| Decoded audio correlation versus v5.16 | 1.0 | 1.0 |

The strong phrases measured are “not cut at all” and “secret weapon.” Adjacent hook/context/payoff ranges do not count as internal cuts when they retain contiguous source time. The running-back statement keeps the conditional claim plus speed, power and momentum. The kicker edit keeps the secret-weapon explanation, the transcript's Spencer reference and bubble-wrap payoff. Team/location context removed by the editor is not imported into posting tags.

Both cuts retain their saved independent local text checks from v5.16. No new inference, human listening assessment or blind preference evaluation was performed. Audio equality establishes that packaging did not alter the prior audio; it does not prove the original internal join sounds natural. The UI still asks the creator to listen to joins and inspect context. Correcting caption text does not inherit automatic text approval.

## Visual checks on real saved footage

The two speech exports were decoded and inspected before/after at 1.2 and 5 seconds. The new sampler found stable face crops across the retained footage, giving a larger subject and clearer caption presentation than the prior sample's wide shot on blur. The running-back clip received no gratuitous movement. The kicker received one 3.5% progressive punch-in around the kept “golden right foot” phrase at output 6.06 seconds and returned wider at the end.

Three cover choices were generated from each export. Inspected final covers have one hook overlay, using clean source frames rather than stacking a new hook onto burned video captions. The installed OpenCV build lacks the optional legacy eye detector. Blinking, flattering expressions and subject recognition were therefore not established; selection remains manual.

A separate real two-person source window at 35–49 seconds rendered a 14-second split-screen export. Two stable faces appeared in 10 of 11 samples; decoded output showed both heads within their panels. Existing transcript labels were absent, so the app chose split screen without guessing active-speaker identity. This manually chosen window validates framing only; it is not an editorially approved Short. Verified-position active switching was validated with synthetic footage, not a real labelled conversation.

## Measured processing impact

Single local timing samples, with the same source and kept cuts; numbers are not whole-video forecasts. The v5.16 render baseline was taken before source edits. Cover preparation is a separate optional action.

| Stage | Running-back clip | Kicker clip |
|---|---:|---:|
| v5.16 export | 2.152 s | 2.145 s |
| New final package, fresh | 0.002 s | 0.003 s |
| New face sampling, fresh | 0.822 s | 0.761 s |
| v5.17 export | 1.499 s | 1.966 s |
| v5.17 package + sampling + export | 2.322 s | 2.729 s |
| Difference from export baseline | +0.170 s | +0.584 s |
| Old three-frame thumbnails | 0.290 s | 0.367 s |
| New optional eight-frame sampling + three clean covers | 2.070 s | 1.946 s |
| Cached package | 0.0007 s | 0.0017 s |
| Cached scene samples | 0.0002 s | 0.0002 s |
| Cached covers | 0.0001 s | 0.0001 s |

The new face detector is the small existing local YuNet model, not another large language model. No source retranscription, candidate rediscovery or additional MLX pass was required. Sampling is bounded to 24 kept-timeline frames and cached independently of cosmetic choices. Render-only timings vary with framing, machine load and warm caches; this is not evidence of a general rendering speedup. No full 34-minute job benchmark was rerun.

## Preservation and startup

A before/after inventory checked size and modification time for 968 existing files under data, exports and models. Existing source media, transcripts, analysis results, reviews, exported media and model files retained those recorded attributes. While the app remained open, one existing variant cache and two project/settings records changed. Those current records were retained; no rollback or bulk migration was performed. This inventory is a metadata check, not a cryptographic content audit.

Saved legacy manual looks remain identical in UI/export regression tests; new effects require Apply style. Previous thumbnail caches and renders remain on disk. New caches use separate versioned paths. The UI badge is v5.17; the analysis-cache VERSION was not bumped for this release. Model setup explicitly downloads pinned YuNet files only when missing. Inference and editing never trigger that setup download.

A separate checkout copy containing only Git-included files opened the empty Streamlit library, v5.17 badge and local profile successfully without models or project media. The startup check prohibited socket.create_connection. This validates startup rather than full clipping without the required downloaded models.

## Local artifacts and limits

Detailed measurements, scripts and inspected frames are in work/v517-validation/ (excluded from Git). Baseline exports and newly rendered comparison media remain under exports/. Local artifacts are available on this Mac; they are not bundled into a fresh clone.

- Running-back baseline: exports/clip-edit-019c0d99920c.mp4; new: exports/clip-edit-bb6cc4c1dc43.mp4.
- Kicker baseline: exports/clip-edit-faedf09c499b.mp4; new: exports/clip-edit-73db2ea83388.mp4.
- Two-person framing check: exports/clip-edit-9d6c9bbe13f4.mp4.

No broad genre benchmark, human audio-join review, lip-sync/identity verification, reliable blink/expression detection, automatic B-roll insertion, social thumbnail upload, retention study or analytics learning was performed. Face sampling can miss movement between frames and cannot protect every object or slide. Manual full-picture framing remains the safe review option when that content matters.
