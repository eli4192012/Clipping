# v3.8 validation

- 75 tests pass. Added checks cover per-run settings snapshots, missing-source retention, corrupt-record handling, and distinguishing result files from sidecars.
- The library discovers 12 existing projects, including older analysis formats.
- Streamlit library rendering and opening a saved run were tested without triggering analysis.
- Original media, results, captions, edits, and exports were not moved or deleted.

Settings reconstruction for legacy runs is limited to the metadata those versions saved. Local files must be backed up separately; saving projects does not make processing survive a server shutdown.
