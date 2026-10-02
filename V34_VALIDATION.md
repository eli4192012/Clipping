# v3.4 validation

- 59 automated tests pass. A saved real transcript fixture protects the successful Nico Collins cut at exactly 101.18–130.24 seconds and excludes the next question.
- Regression checks cover uncertain-status headlines, name suggestions that never mutate the original, corrected words retaining timestamps, and audio/word agreement for bounded edge trimming.
- The Streamlit editor, style application, and v3.4 report panel were exercised without exceptions.
- The headline worker ran locally on the Nico Collins clip. Titles remain model-generated suggestions requiring review; wording guards are not a factual guarantee.

Limits: name hints use transcript spelling and user-supplied names, not verified rosters. The app cannot reliably infer a name from spelling alone. Corrections affect captions and subtitle downloads, not the original audio or analysis transcript. Quiet-edge trimming is optional, does not change stored boundaries, and does not remove internal pauses. Broader interview and podcast evaluation is still needed.

Real corrected-caption export: a 3.24-second source range rendered successfully with “replace Nico.” in the subtitle output. Audio/word agreement left the complete Nico clip unchanged at 101.18–130.24. The local server was restarted and its health endpoint passed.

The Nico fixture uses a constrained headline, “Nico Collins Uncertain: The Defensive Plan,” to preserve its uncertainty while naming the subject. Other headlines use the local writing pass and wording checks.
