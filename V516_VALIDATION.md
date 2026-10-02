# v5.16 validation

168 tests passed, including all 152 prior tests and new checks for source-ID validation, chronological cuts, caption retiming, source-coverage accounting, cache reuse, rejected model output, unanswered questions, artificial variants and grounded review evidence.

Real FFmpeg tests encoded colored video segments with different audio tones. The exported frames and decoded tones changed together at the expected joins. Removed dialogue did not appear in SRT; embedded subtitles and burned captions rendered. Silent input and the complex full-picture portrait layout also passed. These checks establish media/timeline behavior, not subjective editorial quality.

Streamlit AppTest checks passed for conditional variant controls, on-demand generation, persisted selection, original-moment comparison, full editor range export, final posting text and restoring the suggested edited timeline. Inference and export were mocked in these UI tests; real inference and real export were checked separately below.

## Real saved-video comparisons

One shared saved Higher quality transcript was used for each original source neighborhood and its new edit. No retranscription, source changes or replacement exports were performed.

| Moment | Source neighborhood | Edited timeline | Encoded output |
|---|---:|---:|---:|
| Running-back cutting explanation | 50.08 s | 8.16 s | 8.185 s |
| Colts kicker / London discussion | 61.82 s | 12.46 s | 12.471 s |

Running-back comparison: [original](/Users/elilong/Desktop/Clipping/exports/clip-487.6-537.7-77712f.mp4) · [edited](/Users/elilong/Desktop/Clipping/exports/clip-edit-ad7303bd4eee.mp4).

Kicker comparison: [original](/Users/elilong/Desktop/Clipping/exports/clip-902.3-964.1-57dd56.mp4) · [edited](/Users/elilong/Desktop/Clipping/exports/clip-edit-31059d45befe.mp4).

The first edit keeps the complete statement about not cutting, speed, power and momentum. The second keeps the secret-weapon statement, identifies Spencer in the saved transcript, and ends on the bubble-wrap line. It removes later first-class seating and player praise. The existing transcript spells the surname “Schrader”; transcription/caption corrections remain the user's editable layer.

Both final edits passed the independent 4B local source check, with at least two criterion quotes verified against the exact final transcript. Unsupported criterion quotes were omitted from scoring. Both used the text-based quote proposal after structurally invalid model plans; this basis and the rejected proposal are inspectable in the decision/attempt files. This is a functioning fallback plus local model review, not evidence that model-only edit planning is reliable.

Fresh model work in the recorded successful samples took roughly 44–50 seconds per moment excluding about 5–6 seconds of model loading. The complete running-back worker took 53.8 seconds. Reopening the already cached kicker decision took 0.55 seconds in the worker; this does not represent fresh inference speed. Real before/after portrait renders were generated for both moments and their first-frame caption/title layout was inspected.

The smaller 1.7B model sometimes returned literal rating-template text instead of real quotes. Shorts editing therefore uses the already installed 4B editor for both processing modes. Balanced still uses its existing lighter transcription backend. No dependencies, model downloads or remote AI services were added.

Artifacts are under work/v516-comparison/: results.json, renders.json, the two request/edit JSON files and decisions/ (including rejected attempts). Comparison videos and subtitle files are new files under exports/; exact paths are in renders.json. Existing exports were preserved.

Cache reuse was also checked directly with model loading prohibited: both decisions reopened in under 0.01 seconds in-process. Nine source videos and nine original transcript files retained modification times from before this update. The v5.16 badge, default Shorts toggle and opt-out persistence passed UI checks.

## Limits

No full 34-minute reanalysis, blind human preference study, published retention test or broader genre benchmark was performed. Local approval can still be wrong. Fast/Full Context behavior was exercised with UI and structural tests; these two final short examples do not establish real-model variant quality across longer stories. No three-version batch is generated automatically. The 100-point ranking expansion, reordering, visual pacing and analytics personalization are deferred.

New analysis paths and separate decision caches apply the editor without changing modes.VERSION for the UI badge. Source videos, transcripts, prior runs, caption corrections and saved exports are retained. Progress follows completed discovery/edit/check/save milestones and time remaining is explicitly an estimate.
