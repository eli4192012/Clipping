# v5.25 · Posting-text corrections

The reported failure rejected a description linking a **bold signature** to a London Eye trip. The final clip also contains the correct **golden signature** condition earlier. A word merely occurring somewhere in the transcript is insufficient support for attaching it to a different outcome.

## Change

The writer retains its one bounded retry, but the repair now receives the actual rejected draft, the checker report, its reason and the final transcript. A shorter repair prompt asks for small factual corrections while preserving the actor, condition and outcome. The repaired draft passes the same format, source, approved-title, closing and fresh-description checks before saving. Duplicate title alternatives are removed before checking the remaining hooks. A single supported title is sufficient; alternatives are optional.

Initial writing now matches the question to the speech: What can preview a reveal or reward, Why needs a stated reason, and How-to requires a method. Event descriptions do not need the commentary phrasing used for arguments. These are model instructions, not deterministic proof of factual correctness.

Posting-form errors extract a concise explanation from a worker exception and show fresh-generation/manual-edit guidance. Saved text is retained. The form and writer compatibility markers refresh older modules in an already-running server. UI release is v5.25; posting writer is social-copy-4. Analysis-cache versions are untouched.

## Automated checks

`.venv/bin/python -m unittest discover -s tests -q`: **273 tests passed in 39.633 seconds**.

Five new regressions cover a draft with both golden/bold terms receiving its actual rejection and another check, repeated unsupported text still failing after the bounded retry, duplicate alternatives being checked once after deduplication, concise error extraction without a traceback/path/JSON dump, and failed generation preserving a saved manual title/description byte-for-byte. Existing checks cover cache reuse, old writer keys, closing qualifications, unapproved titles, manual-field precedence, loaded-module refresh and separate publishing drafts.

## Real local model and running app

The final normal worker used this Mac's installed experimental Qwen3.5 4B and the existing London pub clip's finished transcript. It completed writing, checking, one repair and checking again in approximately **64 seconds**, saved the checked cache and then reused it. A further cache read with the worker patched to fail if invoked also succeeded. No transcription, model download or cloud inference was performed.

The resulting title was **Who gets the golden signature? #LondonEye #GoldenSignature** (58 characters). The description was a short question about the golden signature and London Eye outing; it did not reproduce the whole transcript. Two distinct title choices remained. The live app displayed this result in Social media, including the hashtags inside the title and an editable description. The existing preview remained available. Generation did not publish anything. The local screenshot is `work/v525-validation/social-ui.png`; private caches, transcripts, media and model outputs are excluded from Git.

A before/after inventory of **1,513 existing files** under data, exports and models found no removals or size/mtime changes. Only this clip's new checked posting cache and posting-package file were added. No new export was created.

## Limits

This verifies recovery and normal app/cache behavior on the reported source; it does not establish reliable hooks, accurate factual self-checks or improved audience performance. During development, the same small model accepted an unsupported named-person title and made awkward repairs. A subsequent attempt generated duplicate alternatives, which motivated deduplication. The final question hook still needs human review: a clip that states a prize condition may not show the actual recipient, and an identity-seeking headline can imply a reveal the clip does not deliver. The model's source check does not settle that distinction.

Errors can still occur after the bounded repair. They remain failures rather than unchecked copy or a transcript fallback. Review or edit the wording before publishing. Original videos, transcripts, model files, exports, manual copy and existing publishing drafts are preserved; only the checked posting cache and posting-package selection are saved for this source.
