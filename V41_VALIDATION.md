# v5.1 validation

- 94 automated unit/regression tests passed, including 15 publishing tests. They cover title/caption limits, required audience, changed exports, stale review protection, persisted drafts, native upload serialization, resumable YouTube offsets and lost receipts, Instagram upload/publish order, uncertain outcomes, retry history and Used markers.
- Streamlit AppTest passed for real app navigation to Accounts and Publishing history, a temporary per-clip draft composer, audience validation, saved draft reload and the explicit confirmation gate. Tests used temporary accounts/data and made no real posts.
- Native macOS Keychain write/read/delete passed using a temporary non-credential test item, which was removed.
- Existing transcription, clipping and export test coverage still passes. This update does not change model selection or clipping logic.

## Not yet verified with a live account

No Google/Meta developer credentials were supplied, so end-to-end browser authorization and real platform uploads have not been tested. Upload protocol tests use mocked platform responses. Platform review, account eligibility, permissions, quota and media validation remain external requirements. No video was published during implementation.

Instagram setup requires an HTTPS callback page under your control; this release uses a manual OAuth return URL. Processing checks are manual, scheduling and custom covers are not included. Closing the app during an upload may require recovery from Publishing history. An uncertain Instagram publication is deliberately not retried automatically.
