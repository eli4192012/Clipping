# v5.27 · Before-and-after comparisons

The requested fourth step now has a playable comparison collection in **Before & after** and an **Edit → Compare before and after** action for saved clips. The actual results are mixed. Two previously accepted edits remain useful comparison examples; the fresh local trials did not establish a reliable improvement in cut quality. They exposed an interview-counting bug, incorrect headline relationships and awkward titles despite passing model self-checks.

## Comparison method

The four fresh trials reused existing source videos, timed transcripts and saved discovery moments. Both sides were rendered with the same full-picture portrait layout, highlighted captions, no camera pacing and no extra emphasis. Only the opening text and permitted suffix trim could change. The baseline reconstructed each saved cut and its earlier opening; it did not rerun an old app binary, transcription or discovery. Baseline titles were the saved topic titles, with no fabricated historical posting descriptions.

The final workflow followed opening → ending → final-cut opening check when shortened → posting text. Installed Qwen3 4B ran offline in the existing serial worker. Opening and ending checks retained their bounded repair attempts. Three ending reviews failed their retained exact-quote requirement and kept the prior speech; one reviewer explicitly kept an appropriate ending. Every generated posting title includes its hashtags. New drafts remain inside the comparison's private cache, separate from active project copy.

| Saved moment | Before | Fresh After | Result observed from transcript and exports | Measured trial time |
|---|---:|---:|---|---:|
| Pub prize | 62.36s | 62.36s | Ending review failed. Opening incorrectly linked a bold signature to the London Eye prize, while the reward statement said golden signature. | 188s |
| Turnovers and resilience | 28.42s | 28.42s | Shorter resilience opening; failed ending review retained the caution and final payoff. Title remains abstract and needs review. | 128s |
| Winning ugly | 30.44s | 30.44s | Reviewer kept the essential warning about future turnover deficits. The new posting title repeats “win” and is awkward. | 102s |
| Preparation rhythm | 49.42s | 49.42s | Question counting was corrected to one. The model still failed the quote check and retained the next-topic setup. “At 14 years” can imply age instead of career year 14. | 139s |

The four final trials took **556.83 seconds total**. Reported times include fresh local writing/checking and both renders. Transcription and discovery were reused, and development tests sometimes competed for CPU resources; these measurements are not a controlled model-speed benchmark or a whole-video estimate. Earlier ending-first trials and a question-fix retest remain accessible through **Show earlier comparison runs** rather than replacing their failures with successful results.

Two actual previously accepted export pairs were imported without rendering or inference:

- The accepted pub ending from v5.26: **62.36s → 8.98s**, stopping at the prize statement. Its literal opening still needs work. Its saved active project selection was preserved.
- The accepted turnover opening from v5.24: both **28.418005s**, with the earlier long speech quote replaced by **Why winning with turnovers shows true identity**. The spoken timeline, final caution and existing exports were retained.

These saved pairs retain their original packaging and are labeled separately from the fresh trials, which use one controlled rendering profile. The default collection has **six pairs across four source moments**, with eleven saved reports when development runs are included. No winner or audience-performance score was invented.

## Interview guard correction

One real question began “What is an aspect of your game, whether it's how you prepare,” and continued after a 0.861-second pause with “how you study, how you practice…?” The old ending guard counted both transcript groups as questions and rejected every ending. A narrow continuation rule now keeps that unfinished question together.

The exception requires unfinished comma/semicolon punctuation, a lowercase continuation, a source-time gap of at most 1.5 seconds and no measured voice change. Completed questions, independent capitalized questions, numbered multiple questions, distinct voices and long source gaps remain separate. Removing an internal gap does not make two distant source questions count as one. The fix applies to the ending guard and comparison counts; historical discovery results and analysis-cache versions are unchanged. Existing applied ending selections still reopen. Compatibility markers refresh older loaded controls and question-count code.

## App, storage and tests

Saved comparisons show the actual videos, opening text, posting titles/descriptions, last thoughts, source ranges, local checker reports, failures and measured stage times. User preferences and notes are saved separately from reports. Viewing a pair runs no model or renderer. Changed or missing source/transcript/media marks a pair unavailable while retaining its notes. A comparison works on a copy and does not apply edits, generate publishing drafts, publish or train the AI. Sports retains manual cuts and text.

The clip action respects the current wide/portrait preference using a shared full-picture layout, includes current caption corrections on both sides, and uses a matching saved posting draft for the baseline where available. An already applied AI opening reconstructs the baseline from the literal transcript hook; an earlier unsaved manual opening cannot be recovered. If a final-cut opening recheck fails, the new overlay is empty. Unverified new posting copy is empty rather than borrowed from an older cut.

**309 tests passed** in the full suite. Seventeen new tests cover controlled pairs, preserved project/copy/source state, strict same-moment prefixes, unchanged speech after failed reviews, source/media/subtitle changes, separate user ratings, cache reuse without worker/render calls, source changes during a job, malformed reports, ordering/rechecking, projectless navigation, persistence, missing-media controls, per-clip handoff and the paused-question regression. Completed questions, changed voices and omitted long gaps remain protected. Real campaign exports passed duration and subtitle-text/timestamp validation.

The running app displayed **v5.27** and all six default options. Both accepted opening previews loaded at readyState 4, **720 × 1280**, and **28.418005s**. The fresh pub pair loaded both 62.36-second videos and displayed its source-accuracy warning and failed ending review. A local validation note was saved with the preference left **Not rated**; no human preference was assigned. A saved comparison reopened with the worker and renderer patched to fail if called, in **0.003811s**.

The preservation inventory covered **1,653 existing files** under data, exports and models. None were removed or changed in size/mtime, including **857 protected source, transcript, model, export, posting-copy, applied-edit/style and example-library files**. The seven supplied original MP4s also retained their SHA-256 hashes. Only new comparison reports, caches, review notes and exports were added. Personal comparisons, outputs, analytics and media stay outside Git under data/before-after/ and exports/. Local logs and proof screenshots are under work/v527-validation/.

## Interpretation

The comparison establishes app behavior and makes real strengths and weaknesses inspectable. It does not establish retention improvement, reliable factual checking or parity with another clipping service. The small model can transplant a real word into the wrong relationship, or choose a weak main point under a misleading opening. Exact supporting quotes and a self-check are insufficient to certify a paraphrase. Automatic transcripts can also be wrong; no word-by-word audio correction or human listening assessment was performed here. Read the flagged drafts, listen to the actual cuts and record your preference before using them.
