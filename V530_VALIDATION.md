# v5.30 validation · Complete ideas before shorter cuts

Validated on October 7, 2026, on the existing Apple Silicon Mac with Python 3.13.14. This release changes speech selection and editing; `modes.VERSION` remains 10. The app badge is v5.30.

## Selection behavior

Balanced editing now asks for an established subject, useful explanation and conclusion within the preferred duration. Whole selected sentences, unfinished transcript continuations and substantive speech between retained sentences are preserved. Internal removals are restricted to redundant material. Short complete ideas remain allowed with an explicit checked reason; there is no duration padding.

The separate final-cut review must identify supporting statements from the speech actually retained. A reporter question cannot be used as the explanation or conclusion. Any retained question must be answered. Deterministic checks reject unfinished sentences/questions, isolated unnamed-person openings, unexplained comparison endings, reporter-only setups and more than one detected reporter question in Interview mode. Invalid edit decisions remain diagnostic/manual-review moments in both processing modes. A bounded planner repair and bounded evidence-reference correction still require every acceptance check; a failed source/meaning check is never overridden.

## Automated checks

- `python -m unittest discover -s tests -q`: **367 tests passed**, 23.756 seconds, in the main pinned local environment.
- First-party Ruff checks and `git diff --check` passed.
- Added coverage for restoring clauses and explanations, continuation/question boundaries, mixed confirmations with missing punctuation, comparisons, incomplete question openings, source-grounded final evidence, bounded repair, short complete ideas, rejected edits in both processing modes and separate saved-run identities.
- Existing real export, caption, combined-video, worker watchdog, source preservation and local model availability tests remain in the full suite.
- No dependency or model download was required. Hosted checks use the existing fresh Apple Silicon install workflow; their status is available on the pull request.

## Real saved-video trial

Reused the existing 663.93-second interview, **DC Lou Anarumo is happy with the growth he’s seen from multiple position groups**, with its saved timed transcript. Settings remained Interview, preferred 20–65 seconds, Higher quality, installed Qwen3-4B editor, full coverage, vertical framing and existing multimodal curation. No retranscription was performed.

| Result | Prior saved suggestions | Final v5.30 suggestions |
| --- | --- | --- |
| Recommended clips | 7 | 7 |
| Durations, seconds | 7.26, 12.68, 6.00, 10.46, 7.90, 7.00, 6.38 | 62.32, 23.62, 24.42, 28.16, 29.38, 37.58, 25.30 |
| Mean duration | 8.24 seconds | 32.97 seconds |

The same injury topic previously retained 6.38 seconds around “when we get an injury” and a moderator transition. The new 29.38-second timeline keeps the named injury setup, one question, and the answer about evaluating George and rotating by committee. A former seven-second Tillery/reporter fragment is replaced by the 37.58-second explanation of the tackle rotation and tackling payoff. Other accepted cuts keep progress examples, pass-rush roles and cornerback expectations.

All seven final cuts match their remapped timed words, pass the current structural guards, preserve the checked meaning and fit the 65-second maximum. Retained source ranges do not overlap between recommendations. Five source moments were excluded, including an incomplete interviewer opening and cuts lacking verified final evidence; four have explicit editorial failures. Multimodal curation completed without reported failures. Those original moments and earlier analyses remain saved.

This is one interview trial, not proof of higher retention or better audience results. The two recommendation sets are not seven identical topics, so average duration is only a description of the outputs. Local semantic checks can still make mistakes. Podcast behavior has regression coverage; no new full podcast or sports-quality trial is claimed.

## Performance and caching

The first full pass using the final review schema took 612.7 seconds. A final resumable pass took 207.1 seconds after reusing completed editing/visual caches and revisiting failed moments. The shorter time is **not a cold-run speed claim**. Successful individual decisions are reusable; current structural checks also run on cache hits. Changed selection/editor/review identities prevent reuse of earlier aggressive clipping results while retaining old runs and transcript caches.

Reopening the completed final analysis returned in about 0.003 seconds with transcript loading, workers and curation deliberately disabled by the validation harness. More complete retained speech, stricter checks and bounded retries can increase first-run processing and render time. Estimates retain measured workload history, and progress follows actual pipeline milestones.

## Live app and export

The refreshed app displays v5.30 and opens the final seven-clip collection. Opening **All hands on deck** rendered only the chosen Balanced version locally in about five seconds. Native browser playback advanced from zero with no media error. The export contains H.264 video at 720×1280, AAC audio and a subtitle track, all starting at zero. Video duration is 29.383 seconds, audio/container duration 29.412 seconds and subtitles 29.38 seconds, consistent with the planned 29.38-second timeline and codec framing. Video/subtitle download controls are visible.

Older analyses expose **Find fuller clips with updated AI**, which creates a separate result and leaves their existing edits accessible. New suggestions are not silently applied to previous clips. No social publication was performed.

## Preservation

Compared size and modification time against a baseline of **2,274 existing files** under data, exports and models. **2,270 remained unchanged; none were removed.** Four intentional metadata files in the validation project changed: project activity, saved-run registry, measured timing history and finished-clip registry. All prior source videos, transcripts, saved analyses, manual edits, exports and model files remained unchanged. New caches, analyses and one rendered clip with its subtitle/timeline/framing files were added locally; these personal runtime files are ignored by Git.
