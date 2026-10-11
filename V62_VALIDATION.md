# v6.2 validation · October 10, 2026

The live Google token-renewal endpoint returned HTTP 400 with `invalid_grant` for the saved Indy Audible connection. This is an expired or revoked authorization, before a video upload starts. No provider message, credential, authorization URL or token was copied into the error or logs.

## Verified behavior

- The app displays v6.2 and **Indy Audible · Reconnect needed**, with a specific explanation in Accounts. Publishing provides an Accounts shortcut for the flagged account.
- Existing Google app settings are reused. **Connect YouTube → Sign in with Google** opened Google's account chooser. Multiple accounts are available, so the channel owner must select the Google account for Indy Audible, complete sign-in, then return and press **Finish connecting YouTube**. The connection has not yet been restored or verified with Google.
- An authentication failure before upload preserves an editable Draft and saves the safe explanation. Two live Draft records now contain this reconnect message. The agent did not publish or schedule a clip during validation.
- Known Google and YouTube error codes map to controlled messages. Unknown or malformed responses retain a generic status message; raw provider text and secrets are excluded. Uncertain upload attempts keep their receipts and require checking rather than automatic reposting.
- A mocked same-channel reconnect replaces its credentials and removes the warning while preserving other accounts. No permissions or OAuth scopes were added.

## Checks

- `.venv/bin/python -m unittest discover -s tests -q`: **539 tests passed in 37.140 seconds**. Includes error privacy, OAuth recovery, draft preservation, uncertain upload handling, Accounts and Publishing navigation tests. Results are in `work/v62-validation/full-tests.log`.
- Python syntax compilation of changed app/publishing modules and tests passed; `git diff --check` passed.
- All **611** protected source videos, transcripts, exports and model files retain their original sizes and nanosecond modification times.
- All **23** baseline posting records remain saved. One new Draft appeared during the live session, bringing the total to 24; an existing Draft's update timestamp changed. Original posting content, schedules and receipts were retained. No saved record was removed or reset.
- Existing source analysis-cache version and model weights are unchanged. No dependencies were installed.
- Live Accounts proof: `work/v62-validation/reconnect-accounts.jpg`. Google sign-in and the Accounts page were left open for the channel owner.

Google explains authorization and testing-mode refresh-token expiration in its [OAuth documentation](https://developers.google.com/identity/protocols/oauth2). Testing-mode expiration is one possible cause; the live response does not identify why this particular permission expired or was revoked.
