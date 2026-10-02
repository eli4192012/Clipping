# v5.3 validation

- 106 regression tests passed, including four project-deletion tests using temporary projects.
- Verified moving project files, preserving external originals, disabling associated drafts, rejecting outside/symlink targets, blocking deletion during processing, and rolling back draft changes if the move fails.
- Existing Streamlit Accounts, history, draft reload and explicit publishing confirmation checks passed.
- No real user project was deleted during testing. macOS Trash permissions can still prevent moving a project; in that case the app reports the failure.
