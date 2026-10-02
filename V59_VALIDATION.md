# v5.9 validation

- 129 regression tests passed.
- AppTest verified project search, opening saved clips, returning to the library, and the v5.9 release dialog.
- Accounts/history navigation and saved publishing draft confirmation checks passed.
- All three existing projects generated JPEG covers from their own local source videos. Cached reads were verified without reopening the video decoder; missing sources have a placeholder.
- Dashboard and project cards inspected in the browser. No clipping, model, or export behavior changed.
- A representative source frame is used for each cover; it is not necessarily the original YouTube thumbnail. Initial cover generation requires a short local decode; subsequent views reuse the small JPEG.
