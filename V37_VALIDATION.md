# v3.7 validation

- 71 tests pass. New checks verify more than five suitable clips can be selected, failed drafts are not used to fill a minimum, and cached analysis skips transcription/model work.
- Settings UI checks verify the maximum selector is gone, the optional minimum is off by default, and enabling it exposes the numeric target without exceptions.
- Existing Nico boundary regression remains passing.

Speed changes eliminate redundant work rather than guarantee a fixed processing time. New videos still require local transcription/review, and sports search remains expensive. Minimum targets report shortfalls rather than weakening quality gates.

Real Higher quality interview run returned 7 suitable clips, exceeding the old five-clip cap. Repeating with a minimum target of 10 reused completed analysis in 0.0000 seconds (backend call only, not full UI time). Target shortfalls remain explicit. Server restart and health check passed.
