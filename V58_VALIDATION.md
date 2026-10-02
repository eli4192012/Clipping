# v5.8 validation

- 129 regression tests passed, including seven new speed/reuse tests.
- Verified one speech-model load for three detection samples; no model-weight loading when all podcast proposals/reviews are cached; separate caches when transcript or quality changes; and one review-worker call across two coverage selections.
- Verified alignment reuses raw speech, legacy scene-specific transcript paths remain accessible, and redundant final podcast prompts are omitted without losing sentence coverage.
- In the tested 60-sentence case, proposal calls fall from two to one; 100 sentences require two rather than three. These are call counts, not measured end-to-end speed multipliers.
- Existing Streamlit navigation, publishing draft persistence and explicit confirmation smoke checks pass.

No new full-video cold-processing timing benchmark was run. Integration tests use controlled inference responses; existing completed projects are preserved. The same local models and quality reviews remain in use. Persistent reuse reduces repeated work rather than promising a fixed processing duration.
