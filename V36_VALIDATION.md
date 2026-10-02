# v3.6 validation

- 68 tests pass, including sports interviews versus gameplay, podcast discussions with questions, explicit press conferences, and low-confidence unknown footage. Existing boundaries and export tests remain passing.
- The real Colts press conference is detected as Interview using its saved transcript and sampled faces.
- Streamlit automatic mode selection and switching to manual mode passed without exceptions. Interview defaults showed 20–65 seconds and 100% maximum coverage.

This is evidence-based routing among the three existing modes, not universal genre recognition. Confidence labels are heuristic, and automatic detection can miss mixed-format sections.

The saved football-game source was detected as Sports. An uncached 24-second discussion clip with an explicit podcast title exercised the sample-transcription path and selected Podcast without errors.
