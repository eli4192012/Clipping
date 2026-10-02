# v5.12 validation

- 135 unit/regression tests passed, including category validation, automatic exclusivity, rejecting a third choice, combined routing, distinct guidance and category cache keys.
- Prompt tests verified cooking-specific instructions reach both proposal generation and exact-cut review.
- Streamlit setup smoke test verified all 29 choices (28 categories plus automatic), saved two-category settings and Interview routing.
- Transcript cache paths are unchanged by category selection; final selection paths include category identity.
- No full-video category quality benchmark was run. New categories guide the existing local text model; they do not add trained visual recognition for basketball, soccer, music, gaming or movie scenes. Automatic category suggestions use sampled speech and title cues and can be wrong.
