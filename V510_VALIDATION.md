# v5.10 validation

- 129 existing regression tests passed.
- Generated three JPEG thumbnails from an existing exported clip in 0.52 seconds on this Mac. This is one sample, not a promise for every video.
- Verified maximum image dimension of 1280 pixels, cache reuse without reopening the decoder, thumbnail selection persistence after reopening, and the JPG download control.
- Social accounts/history, draft persistence and publishing confirmation smoke tests passed.
- New thumbnails use frames from the finished render, including its chosen framing and any burned-in text. Recommendations compare image sharpness and brightness; they do not predict views or understand visual meaning.
- Thumbnail upload to YouTube or Instagram is not automated. Existing posting drafts and previously generated text files remain saved.
