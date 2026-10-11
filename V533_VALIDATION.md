# v5.33 validation: local posting-style examples

## Scope and imported data

The supplied five-page **All Videos And Shorts Oct 7 2026.pdf** supplies 63 Indy Audible title/description pairs, with hashtags in the titles. All five pages were rendered and visually inspected. Text objects were decoded directly because ordinary extraction corrupted parts of the descriptions. Ten rasterized titles were transcribed from the rendered pages; decorative emoji in those image titles are omitted from the searchable text. Rows continuing across page breaks were joined. Every row ID from 1 through 63 has a nonempty title and description.

The unmodified PDF, extracted corpus, active profile and import audit stay under ignored `data/posting-style/` on this Mac. No private examples or original PDF are committed. The importer archives each distinct corpus before activating its profile, including excluded entries. Repeated imports preserve the archive; even changes to excluded entries produce a separate archive and fingerprint.

56 examples are eligible for generation. Two copied-speech descriptions, two generic descriptions, one conflicting year and two conflicting win/tie outcomes are excluded. Generic trending tags and obvious mistyped tag variants are not suggested. This filtering does not prove every remaining example is accurate or effective.

This is **example-based personalization at generation time**, not model-weight fine-tuning. The PDF has neither paired finished-clip transcripts nor view/retention metrics, so it cannot establish successful title patterns or support performance-based training.

## Runtime behavior

- The posting writer retrieves up to three related examples using weighted content-word overlap. Weak matches and unrelated topics receive no examples. Retrieval is local and does not load another model.
- The writer receives historical examples as style data. Its independent source-check prompt receives only the finished clip transcript and generated copy. The examples are not factual evidence for a new clip.
- The writer can generate direct headlines, supported contrasts and useful questions, with natural short descriptions rather than mandatory questions and rigid one-sentence templates.
- Hashtag suggestions use current transcript entities and supported topic phrases. Titles retain inline tags and the 100-character limit. Descriptions have no separate tag list.
- Evidence IDs attach exact source phrases. Deterministic checks reject invalid IDs, copied speech, unsupported explicit numbers and several observed unstated-benefit claims. A known wrong-actor signature/trip error is rejected. Individual invalid title alternatives can be discarded while retaining a supported alternative.
- A failed attempt gets one bounded repair. Failed generation does not replace saved copy. Profile fingerprints separate posting caches without invalidating transcription or analysis.
- The Social media screen displays the channel, saved-post count and number of relevant examples. Saved manual fields and reviewed publishing drafts retain their existing protections. Importing examples and generating text do not publish videos.

## Automated checks

- **413 tests passed locally** on Python 3.13.14, including real video-export regressions. The final follow-up changes to archive provenance and caption grammar also passed the 10 posting-style tests and 12 posting-UI tests.
- Ruff and `git diff --check` passed. No new app runtime dependency or model download was needed.
- New tests cover preservation of all imported pairs, exclusions, changed excluded-entry archives, bounded relevance, absent/corrupt profiles, transcript-supported tags, historical data being absent from source checks, source vetoes, exact evidence IDs, observed factual failures, independent title filtering, profile cache invalidation and UI provenance.
- Existing opening-hook tests exposed a shared stopword dependency during development; it was restored and the full suite passed afterward.

## Real local model trials

The previous writer and personalized writer were compared on three saved finished transcripts using the installed **Qwen3 4B** model. Trials use temporary validation output and do not overwrite project posting text. The final personalized run accepted two drafts and rejected one:

| Case | Final result | Practical assessment |
| --- | --- | --- |
| Signature reward | Accepted, about 20 seconds | The description preserves the recipient, condition and London Eye reward. The chosen title is still awkward and can suggest the wrong object is won. Model approval is not proof of title accuracy. |
| Turnover discussion | Rejected after repair, about 35 seconds | The draft added an unstated survival benefit. The new deterministic guard blocks it instead of saving it. A usable personalized draft was not obtained in this trial. |
| Colts/Washington matchup | Accepted, about 27 seconds | The description explains the mismatch and missing personnel more fully than the previous short draft. The title can still overstate a prospective matchup as an observed struggle. Human review remains necessary. |

Earlier trials also exposed invented confidence/sharpness claims and inaccurate reconstructed quotes. Those failures informed additional guards and exact phrase IDs. The result is a connected style reference and stronger rejection of observed errors, **not consistent automatic posting quality**. These three cases do not establish audience gains, broad factual reliability or an end-to-end speed improvement. Conservative checks may also reject valid paraphrases.

## Live app and preservation

The app at `http://127.0.0.1:8501/` displays **v5.33** and the Indy Audible reference under **Social media**. A clip with previously saved manual posting text was opened to confirm the reference caption without generating replacement text or publishing. The old title and description remained present. A screenshot is saved locally in `work/v533-validation/indy-audible-style.png`.

Against the prior 2,367-file source/transcript/export/model inventory, 2,361 files remain unchanged, none are missing, and only the same six project/run/finished-clip metadata paths already documented in v5.31 differ. No additional inventoried path changed during this validation. The existing manual posting file also remains unchanged. Analysis-cache `modes.VERSION` remains 10; only the user-visible release advances to v5.33.

Raw extraction, corpus audits, private trial outputs and detailed logs remain in ignored local validation/storage directories. GitHub contains the implementation, synthetic test fixtures and this validation summary; other clones need their own local example import.
