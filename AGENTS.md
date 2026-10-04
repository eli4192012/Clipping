# Clipping project rules

- User-visible version is stored in version.json and displayed in the top-right corner of the app.
- Current release is v5.24. For each subsequent user-requested change that ships, increment minor by one (v5.25, v5.26, etc.). Do not increment for intermediate edits/tests within the same release.
- Keep major at 5 unless the user explicitly requests another major version. Do not change the analysis-cache VERSION merely to update the UI badge.
- Keep all transcription, model inference, and editing local. Preserve existing source videos, transcripts, and exports.
- Progress percentages must reflect actual pipeline milestones. Time remaining is an estimate, never a promise.
