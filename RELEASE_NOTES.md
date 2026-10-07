# v5.30 · Clips that keep a complete idea

- Changes Balanced selection from “the shortest explanation” to the subject, useful explanation and conclusion. Uses your preferred duration as a target while allowing genuinely brief complete ideas. Keeps the question when needed and retains the one-question interview limit.
- Keeps whole sentences and completes speech split across transcript pauses. Restores explanation removed by aggressive internal cuts. Balanced internal deletions are limited to clear acknowledgements, literal repetition and discussion references; Fast remains an optional shorter edit.
- Improves interview source boundaries: keeps named setup, separates actual questions from lowercase continuations, excludes moderator transitions and counts a detected confirmation even when Whisper omitted its question mark.
- Adds final-speech evidence for the subject, explanation and conclusion, plus an explicit check that any kept question is answered. Rejects incomplete endings, unnamed-person openings, reporter-only setups and unverified edits in both processing modes. Current structural guards also run on cached edits. One bounded repair can fix a rejected plan or invalid evidence references; every final check still has to pass. Original moments remain available in the selection report.
- Adds **Find fuller clips with updated AI** to older results. Reuses the transcript, saves a separate analysis and leaves prior clips, manual edits and exports available. New editor/review/timing cache identities reflect the changed work without changing transcription caches or `modes.VERSION`.
- All processing stays local with the installed AI editor. Full regression tests and saved-video validation are documented in [validation](V530_VALIDATION.md). Longer kept speech and more detailed checking can increase processing and rendering time; fewer clips may pass.

# v5.29 · Reliable installs, exports and diagnostics

- Fixes the pinned install list: Keychain support, scene detection and higher-quality MLX transcription now include all required packages. Uses the working local versions and checks direct constraints plus native imports in a clean environment.
- Shows actual encoding progress for individual clips as well as combined videos. A wall-clock watchdog works even when FFmpeg stops producing output; failures stop and reap the process and remove the new partial video. Earlier exports remain available. Caption paths with spaces, apostrophes and punctuation are escaped consistently.
- Keeps private, rotating local diagnostics in `work/logs/app.log`. Failed jobs and UI actions record exception types and call locations; worker traceback locations survive temporary-folder cleanup. Account/provider messages and transcripts are excluded from general logs. FFmpeg diagnostics are bounded and redact URLs and token fields.
- Adds GitHub Actions on Apple Silicon: a fresh pinned install, dependency/import checks, scoped first-party lint and the regression suite, including real video/audio/caption exports. Vendored code, model weights and personal media are excluded from the checks' source requirements.
- Validates analysis controls without rewriting saved settings; shares the existing timing key between estimate reads and writes and tolerates damaged timing history. Binds loop callbacks explicitly and removes an unused import. All 51 saved settings/run combinations checked retain their original analysis paths; the analysis-cache VERSION remains unchanged.
- Updates the README for the public repository and development branch. All transcription, inference and editing stay local. **348 tests passed** on this Mac; see [validation](V529_VALIDATION.md). This release improves reliability and diagnostics; editorial quality and model-speed changes remain separate work.

# v5.28 · Local speech, visual and sound curation

- Adds **Use speech, visuals & sound to choose clips** in project settings. Reuses speech editing, then combines local sound classification and sampled-frame observations before final moment selection. Choose 1–6 moments for heavier visual review, default 3.
- Uses Google's local YAMNet for speech/music/reaction sounds, the installed Qwen3-VL 4B for three retained-source frames per selected moment, and a cached motion/camera-change scan. Interview, Podcast, Sports, Music and Gaming presets apply different supporting weights. Emotion inference and analytics training remain deferred.
- Makes only small priority adjustments. Existing source checks, complete endings and the one-question interview limit take precedence. Missing models, failed responses and detected visual contradictions remain unavailable or uncertain; motion cannot approve a completed sports play.
- Shows **Speech, visuals & sound evidence**, with actual source frames/timestamps, sound windows, weights, failures and downloadable JSON. **Advanced → Review this moment with speech, visuals & sound** reviews an existing final cut on demand without changing its edits, captions, posting text or export.
- Installs the small sound model in a separate pinned TensorFlow environment using `setup_sound.py`; sound setup is completed on this Mac. Inference stays local and serial, reuses transcripts, and caches source and cut evidence independently. The main MLX dependencies and analysis-cache VERSION stay unchanged.
- **330 tests passed**, plus real trials across four moments in three saved videos, cache reopening without workers, and live app evidence checks. The first small-model attempt was unreliable; final curation uses 4B. The observed priority change does not establish better clips, audience gains or parity with a commercial service. See [validation](V528_VALIDATION.md).

# v5.27 · Before-and-after comparisons

- Adds **Before & after** in the sidebar and **Edit → Compare before and after** for a saved moment. Play real pairs, inspect opening/posting text and final thoughts, download reports and save your own preference and notes.
- Uses the same source, transcript, fixed discovery cut and rendering profile for both sides. Reviews a copy in opening → ending → final-cut opening check → posting order. Existing project edits, publishing drafts, transcripts and exports are kept.
- Reuses local transcription, model decisions and renders. Stage times distinguish fresh work from cache reads. Failed steps are shown; no suggestion is automatically applied or published. Earlier runs and failures stay available.
- Compares four saved moments and exposes mixed results, including local self-checks accepting inaccurate headline wording. Shorter duration or a model's approval is not counted as proof of better quality. See [validation](V527_VALIDATION.md).
- Fixes a false two-question rejection when one unfinished comma-ended question continues across a short pause. Completed questions, voice changes and explicit multiple questions remain separate. The analysis-cache version is unchanged.

# v5.26 · AI ending review

- Adds **Edit → Improve the ending with AI**. Identify the main point, choose a complete source-sentence ending and check the proposed payoff, removed speech, qualifications and opening promise locally. The reviewer can keep an already suitable ending.
- Offers an editor choice for this review without changing the project's model setting. Reuses existing timed transcription and limited ending observations from the local example library; no new model download or cloud inference is needed.
- Trims only the tail of the current timeline. Earlier speech and internal source gaps are preserved. Timing guards reject cut-off words, unanswered endings, two questions in an interview and directly dependent closing cautions; a source check cannot override these guards.
- Shows the ending, exact main-point/payoff quotes, removed speech and duration before explicit **Apply this ending**. Generation is on demand and cached, with one bounded retry. Failed generation leaves saved cuts intact. Sports and silent clips retain manual controls.
- Stores ending selections separately from discovery, manual boundaries and styles. Applying creates a new export; Restore reuses the earlier export. Existing sources, transcripts, caption corrections, analyses, posting text and exports are retained. No automatic publication or analysis-cache version change. See [validation](V526_VALIDATION.md).

# v5.25 · Repair rejected posting text

- Gives the posting writer the rejected draft and source-check reason during its one bounded retry. It repairs unsupported wording against the final clip instead of starting again from an error alone.
- Directs the writer and checker to preserve the terms linking conditions to outcomes, including the golden-signature London Eye prize. Corrected text still needs to pass the existing source, title, hashtag, closing and fresh-description checks.
- Matches question hooks to the clip: rewards/reveals can use What, Why requires a stated reason, and How-to requires an actual method. Event descriptions do not have to use commentary phrasing.
- Removes duplicate title alternatives before checking the remaining hooks; repeated ideas no longer cancel an otherwise valid posting package.
- Shows a concise explanation and retry/manual-edit guidance when generation fails. Existing manual copy, checked caches, source media, transcripts and exports remain saved. Loaded older posting controls refresh without restarting the app.
- Uses the installed local model and existing transcript. No new downloads, transcription, video rendering, cloud inference or automatic publication. New writer cache keys avoid reusing older drafts. See [validation](V525_VALIDATION.md).

# v5.24 · AI opening text

- Adds **Look → Improve the opening with AI**. Generate a short first-screen hook from the final kept transcript and its first three seconds, then explicitly apply it to preview a new export.
- Tries several hooks, checks the selected wording in a separate local pass, and shows exact supporting subject/payoff quotes. Guards reject placeholders, unsupported acronyms/absolute claims and copied opening questions. Failed generation preserves the previous opening.
- Uses saved opening/headline presentation lessons from unexcluded **Good pattern** examples. Other clips' facts, titles, transcripts and analytics are not passed as evidence; the full-record review flags are independent of this limited presentation use.
- Reuses transcription and caches checked suggestions by final cut, model, opening timing and lessons. Generation is on demand, with one bounded retry. Applying changes the text shown for the first three seconds; speech boundaries, internal cuts and social posting copy retain their existing behavior.
- Keeps manual styling authoritative and retains earlier exports. Sports and silent clips use manual opening text. No new model download or account is needed. The model checks its own suggestion, so wording still requires your review; no retention improvement is established. See [validation](V524_VALIDATION.md).

# v5.23 · Local example library

- Adds **Example library** in the sidebar. Browse supplied clips, actual posted titles, opening text, saved transcripts and sampled frames, with notes on what works and what to avoid copying.
- Keeps good patterns, mixed examples and patterns to avoid separately labeled. Editable notes and review status save locally. Analytics show views, engaged views, stayed-to-watch and average-viewed percentages with their export period; unconfirmed clip-to-YouTube matches remain visibly marked.
- Seeds this Mac's library with the seven supplied clips and existing review material, reusing their transcripts without transcription or AI inference. Add more video examples, supply a transcript if available, search/filter the library and download its JSON. Adding the same clip preserves its previous notes.
- Stores the library under data/example-library/, outside Git. Original imported clips remain referenced at their existing paths; sampled frames and transcripts are copied into the library. Uploaded new examples get their own local media copy. Missing originals leave notes and transcripts available.
- This is step 1 only: the reference library does not change clip selection, cuts, opening text, social titles, analysis caches or model weights. See [validation](V523_VALIDATION.md).

# v5.22 · Hook titles and fresh descriptions

- Opening **Social media** now writes missing YouTube posting text automatically once. It uses the selected local editor and the final clip's transcript; viewing Edit or Look does not run this writing task.
- Proposes different hooks around the clip's question, contrast and takeaway. A separate source check chooses a supported title and discards unsupported suggestions. **More title ideas** allows choosing another checked hook when available; hashtags remain inside each title.
- Descriptions explain the point in fresh words. Copied transcript passages and unsupported absolute claims are rejected instead of becoming the description. Legacy quoted defaults are replaced, preserving separately edited titles and other platform packages; saved manual copy stays as written.
- New writer caches avoid reusing earlier weak AI copy without clearing existing caches or media. Failed automatic generation can be retried explicitly and does not loop on reruns. No generation publishes a video. Requires Streamlit 1.64 or newer, already present in the pinned local runtime. See [validation](V522_VALIDATION.md).

# v5.21 · Refresh older posting controls

- Fixes the Social media tab failing with "post_form() takes 2 positional arguments but 3 were given" when an already-running server retains the previous posting form.
- Refreshes that older module before opening the clip's controls. Current controls are reused normally; saved posting text and video exports are retained. See [validation](V521_VALIDATION.md).

# v5.20 · AI posting titles with inline hashtags

- Renames the clip's Post tab to **Social media** and adds **Generate title & description with AI** to its YouTube posting package. The selected local 4B editor writes the headline and a short final-clip summary, then independently checks them against the final transcript.
- Hashtags are part of the title, within YouTube's 100-character limit. The description summarizes the clip without a separate hashtag block. Existing separate hashtags display inline in titles or captions; separate hashtag input fields are removed.
- Keeps writing on demand, with model/final-clip caches and an explicit **Generate fresh text** option. Failed generation preserves saved text. No transcription, video rerender, cloud AI or social-account connection is needed to generate copy.
- Retains editable posting fields and existing reviewed publishing drafts. **Use current posting text in this draft** explicitly copies updated text into an editable draft; saving/reviewing and publishing remain separate user actions.
- Speechless clips use manual posting text. Model summaries and source checks can be wrong; review the wording before posting. Sports vision, source videos, caption timing, opening overlays and combined videos keep their existing behavior.

# v5.19 · Qwen3.5 local AI editor option

- Installs Qwen3.5-4B in 4-bit form locally, with a pinned model revision and an editor-only setup command. No account or paid API is required. Models are never downloaded during processing.
- Adds **AI editor** in Advanced settings. Qwen3.5 is available as an experimental option for topic discovery and Shorts planning/checking in either processing mode. Qwen3 4B remains recommended after the initial saved-video comparisons; a newer model is not automatically a better editor.
- Separates model-specific analysis, topic and edit caches while reusing saved speech. Structured edit decisions identify their model. Existing videos, transcripts, exports and prior results are preserved.
- Keeps the 3 GiB MLX limit and serial model workers, adds small prefill batches and a bounded prompt context without silently truncating source text.
- Retains the existing source-fidelity checks. Invalid or rejected cuts remain unverified original drafts or are excluded; the new model cannot bypass those checks. Sports vision, visual packaging and combined-video ordering keep their existing behavior.
- See V519_VALIDATION.md for real offline inference results, measured limits and automated checks.

# v5.18 · Combine clips into longer videos

- Adds Combine clips in the sidebar and collection, plus Add to combined video in the clip editor. Select finished clips from multiple projects, search/filter them, change their order and remove items without deleting their original files.
- Saves named combinations locally for later editing. Uses the exact finished clip versions, retaining their baked captions, opening text and framing. New individual edits can be added as new versions.
- Exports one wide 16:9 MP4 by default (1280 × 720), with vertical output available. Clips fit without new cropping; unused space can use a blurred or dark background. Existing cropped areas cannot be restored by joining exports.
- Normalizes differing frame sizes/rates and audio formats one clip at a time. Silent clips receive silence; speech is not synthesized or analyzed. Available SRT captions shift onto the combined timeline, with an embedded subtitle track, chapter markers and a downloadable timestamp list.
- Caches prepared clips and completed combinations. Reordering reuses prepared clips; an unchanged export skips encoding. Prior exports remain saved. Preview/browser download are on request, and Finder can reveal the saved file directly.
- Shows when a saved result is outdated after combination changes. Progress uses completed preparation and actual FFmpeg output times; remaining time is an estimate.
- No new dependencies, model inference, transcription, discovery or analysis-cache version change.

See V518_VALIDATION.md for mixed-format regressions, the real 82-second export, preservation checks and performance measurements.

---

# v5.17 · Clearer framing and final-clip packaging

- Organizes clip review into Edit, Look, Post and Advanced. Keeps the v5.16 Shorts Editor, manual boundaries, supported alternate versions and original comparison.
- Adds cached sampling across kept footage for automatic speech crops, stable two-person split screen and optional speaker switching. Active Speaker requires user-confirmed anonymous labels and visible positions, holds shots for at least three seconds and ignores short acknowledgements. Uncertain scenes fall back; crop warnings remain visible. Automatic Sports keeps the full picture.
- Adds Off / Subtle / Dynamic visual pacing. Subtle is the default for new speech looks; movement needs a useful final-transcript beat and safe sampled face margins. The real kicker example received one restrained 3.5% punch-in; the shorter running-back example received none.
- Emphasizes a few final hook/payoff caption phrases with larger bold treatment or an optional Gentle pop. Caption timing and manual corrections remain intact. New hook suggestions use extractive kept speech, preserve negation/qualifications and can be edited or hidden.
- Adds separate editable YouTube Shorts, TikTok and Instagram Reels copy, with copy controls and final-edit caches. Specific names/tags must occur in the final transcript. Manual posting text and existing social drafts are retained; no automatic publication occurs.
- Extends the existing thumbnail feature with eight sampled frames, three ranked/separated choices and editable cover text. New automatic exports can supply clean source frames without duplicate captions. Generation happens on request; blink/expression assessment is still limited. Downloads do not set a platform thumbnail.
- Adds timestamped B-roll suggestions only, eight explained editorial assessments and a descriptive local Creator Profile from human ratings. Unknown criteria remain unscored. No virality probabilities, preference training, stock downloads, cloud AI or paid API was added.
- Preserves saved legacy looks until Apply style. Separate packaging caches leave analysis-cache versions and existing transcription/model behavior unchanged. Same-edit reruns reuse metadata, sampling and export caches; only the chosen variant renders.

See V517_VALIDATION.md for measured before/after exports and limitations. V517_IMPLEMENTATION_REPORT.md documents inspected reference code, adopted/rejected ideas, changed files and the recommended next update.

---

# v5.16 · A separate Shorts Editor

- Adds **Edit speech into tighter Shorts**, enabled for new speech analyses. Moment discovery supplies source neighborhoods; a separate editor chooses the actual opening, explanation, internal cuts and payoff. Answer-only openings are allowed when context and meaning checks pass. Sports action keeps its existing pipeline.
- Saves inspectable decisions: hook/context/payoff ranges, removed phrases and gaps, cut reasons, final transcript, output duration, source context checks, meaning checks and supported variants. Invalid model plans may use a clearly identified text-based quote proposal, which still requires independent local review with grounded evidence. Failed edits retain the original moment for manual review; Higher quality recommendations continue to require passed checks.
- Exports multiple chronological source ranges using one timeline for video, audio, SRT and burned captions. Caption groups stop at joins. No synthesized or reordered speech. Minimum edited duration is five seconds; the preferred minimum never causes padding.
- Generates concise opening/posting titles from the final kept speech and posting descriptions as grounded transcript excerpts. No outside facts, live trends or automatic hashtags are added.
- Shows a saved **Edit version** selector and original-moment comparison. Fast and Full Context are offered only when the local review indicates a meaningful alternative; generation and rendering happen on request. Alternatives must differ by more than two seconds and pass their own checks. Small edits do not automatically get Fast variants.
- Reuses existing transcripts and caches successful edit decisions, including the selected variant. Only the chosen version renders when opened. All Shorts editing uses the installed 4B local editor in either processing mode; the smaller editor failed grounded-review checks during validation. This can add processing time. No new model or service was installed.
- Keeps existing evidence-based ranking and omits unverifiable criterion ratings. The expanded 100-point rubric, reordering, visual pacing and analytics personalization remain later work.
- Manual start/end changes explicitly export a continuous source range and clear automatic approval for that cut. Restore suggested boundaries returns to the edited timeline. Existing sources, transcripts, runs, captions, styles, Used markers and exports are retained.

See V516_VALIDATION.md for the two real-video comparisons, runtime checks and limits. Run Find my clips again to apply the new editor, or request a Shorts edit when reviewing an older clip.

---

# v5.15 · Faster reviews and visible progress

- Topic workers now send live progress back to the app for transcript windows and individual clip reviews instead of leaving the bar at 62%.
- Local reviews request shorter reasons and evidence, with a 400-token response budget instead of 650. Completeness, fidelity and audience checks remain.
- Completed proposal windows are cached individually, so a retry can reuse partial topic work. Existing completed analyses and reviews remain valid.
- Interview proposals with known missing context skip expensive AI review and remain rejected.
- Initial time estimates scale with estimated review workload; in-stage estimates use recent review durations. Estimates remain approximate.
- Subprocess output is stored in temporary files while status is polled; timeouts terminate the worker and preserve completed review caches.

---

# v5.14 · One question per interview clip

- Interview selection never merges a follow-up exchange into the preceding clip.
- Each selected clip must contain exactly one detected reporter question and its complete answer. Multiple questions before one answer are skipped; fragmented transcription of a single question can stay together.
- Context-dependent follow-ups may be rejected rather than made longer by attaching another exchange.
- Complete short answers are not padded to a preferred duration. Answers over the maximum are skipped rather than cut in half.
- Final structural checks reject combined exchanges even when the AI approves them. New analysis/review cache versions ensure the rule applies on rerun, while existing transcripts and exports remain saved.

---

# v5.13 · Complete interview exchanges

- Keeps multipart reporter questions with their answers, including subject introductions and declarative setup.
- Stops the preceding answer before the next topic; ignores rhetorical filler such as “You know what I mean?” as a new question.
- Avoids bridging transcript gaps longer than six seconds, where an unheard question could be missing. Ambiguous context is rejected rather than filled into the requested clip target.
- Adds a deterministic interview-boundary veto after AI review, including Balanced mode. A positive model score cannot override a failed boundary check.
- Uses conservative topic-only interview headings instead of inferring a speaker’s identity or role. Older interview clips opened in the editor get safe default headings; explicit custom headings are retained.
- Invalidates clip-selection and review caches while preserving reusable transcripts, old runs, source videos and exports. Run Find my clips again to generate updated cuts; previously downloaded MP4s are unchanged.

---

# v5.12 · Content categories

- Adds every category from your reference, with a maximum of two selections. Let AI detect is an exclusive automatic choice.
- Selected categories guide local topic proposals and exact-cut reviews, combining format and subject guidance. Interview pairs preserve question-and-answer structure.
- Automatic routing adds a category suggestion from sampled or saved speech and title cues. These are estimates; you can override them.
- Category changes invalidate selection and review caches while sharing existing speech transcripts. Saved runs retain their selected categories.
- American football retains its dedicated visual play pipeline when selected alone or with Sports. Other categories use category-guided transcript review; they are not newly trained visual sport, music, movie or gameplay recognizers.

---

# v5.11 · A clearer project setup

- Restyles Shape your clips to match your reference: separate processing-quality and automatic-detection cards, with the source cover and project details on the right.
- Adds connected progress steps with a completed-step checkmark and a highlighted current step.
- Groups the remaining clipping controls under Clip preferences.
- Local jobs use a dedicated progress card with actual milestone percentages, elapsed time and an explicitly estimated time remaining.
- Existing settings, saved projects and clipping behavior are preserved. No decorative Stop button is added without working cancellation.

---

# v5.10 · Clip thumbnails

- Replaces the automatic title-and-description panel with three downloadable thumbnail options from each finished clip.
- Recommends a frame using sharpness and brightness, with a saved choice per render. Preserves the video’s portrait or landscape framing.
- Cached JPEGs avoid repeat decoding. No new AI model, API, or background full-video scan.
- Removes the separate AI headline suggestion. Topic labels, file names, manual opening text, and required social publishing fields remain available.
- New topic reviews no longer request posting descriptions. Existing saved text and social drafts are preserved.
- Thumbnails download separately; automatic social cover upload is not part of this change.

---

# v5.9 · A brighter local studio

- New ice-blue and violet theme, gradient logo, illustrated workspace banner, and clean summary cards inspired by your reference.
- Project cards show a cover extracted from their own source video, with duration when available. Small previews are cached locally and refreshed when the source changes.
- A simpler Open action takes you to saved clips, or project setup when no runs exist. Multiple saved runs and project settings remain available behind expandable controls.
- Search, account connections, publishing history, deletion confirmation, and the clickable release badge are preserved.
- Responsive layouts and keyboard focus outlines remain available. No processing models or clipping rules changed.

---

# v5.8 · Less repeated processing

- Saves reviewed candidate moments separately from the final clip list. Changing source coverage can reuse completed analysis and only redo selection.
- Podcast topic proposals are saved; cached proposal/review results can return without loading model weights.
- Removes a redundant final overlapping podcast prompt when the preceding window already covers the end. Every transcript sentence remains covered.
- Visual scene settings share the same speech transcript. Enabling word alignment or speakers can reuse raw speech instead of transcribing again.
- Automatic video-type detection loads one speech model for all three samples instead of loading it three times.
- Preserves older transcript paths, saved analyses, quality rules and model choices. CPU/thread and memory limits remain unchanged; TransNet remains outside normal processing.

The largest gains are on reruns and settings changes after work has been cached. First-time transcription and local AI review can still take minutes; no whole-video speed multiplier is claimed.

---

# v5.7 · Precise cuts and boundary review

- New timeline selection plus millisecond start/end fields in every clip editor.
- Flags boundaries inside timed words or transcript sentences, unanswered ending questions, and missing speech evidence.
- Offers a small outward repair for clipped words; edits are never silently changed.
- Optional opening/ending frame previews and previous/next-frame controls use actual decoded timestamps, including variable-frame-rate video.
- Frame stepping is preview-only until Apply, avoiding a new render for every click. Context playback and nearby transcript help check the complete thought or play.
- Restore suggested boundaries remains available. Saved edits, exports and project data are preserved.
- Benchmarked TransNet V2 separately on six preserved problem clips: 18 transitions vs 14 for the current detector, with four additional transitions visually checked. Detection was 8.6× slower on this sample, so normal clipping keeps the existing detector.

The new controls are in Precise timeline & boundary checks. TransNet does not run during ordinary clipping. A shot transition is not proof that a play or sentence is complete. See the benchmark and validation reports for measured results and limitations.

---

# v5.6 · Topic-based download names

- Downloaded videos now use the clip's posting title instead of timestamps and a random ID.
- Subtitle downloads use the same title, with an .srt extension.
- Edit the saved posting title to change the download name. Names are cleaned for filesystem compatibility.
- Existing exports, project references and publishing drafts retain their internal paths; no reanalysis or rendering is required to rename a download.

---

# v5.5 · Automatic framing for every video type

- Crop-first automatic portrait framing is now the default for new vertical clips in Interview, Podcast and Sports modes, including exports made without an explicit layout.
- Renamed the layout to Portrait · automatic. Previously saved automatic interview layouts still work.
- Keeps native 9:16 framing; tries a safe clear crop before blurred video backgrounds. Uncertain action and group footage retain the wider view.
- Explicit manual layouts remain saved. Select Portrait · automatic to change an existing manually styled clip.

Framing samples faces; it does not track the ball or prove that all important action fits a crop. Review sports clips before publishing.

---

# v5.4 · Clear portrait crops first

- Automatic interview framing tries a close crop, a wider crop and the widest available 9:16 crop before adding blur.
- Uses all sampled face positions to place a stable crop without jitter; keeps safety margins and an exact portrait ratio.
- Existing 9:16 footage retains its composition without extra zoom or added blur.
- Multiple people, uncertain detection or subjects that cannot fit still use a sharp foreground over blurred video.
- Manual layout choices remain available. New renders use the updated framing; saved analysis and previous exports are preserved.

Framing samples faces; it cannot guarantee preservation of every gesture, prop, caption or brief scene change. Preview before posting.

---

# v5.3 · Delete saved projects

- Each project on My projects now has a Delete project section with a confirmation checkbox.
- Moves the project folder, including its imported source, transcripts, analyses and edits, to macOS Trash.
- Keeps exported clips, external originals such as Downloads, posting history and already published posts. Associated publishing drafts are disabled.
- Blocks deletion while a processing or publishing job is using the app; validates that the target is a managed project folder.

---

# v5.2 · Clear openings and complete payoffs

- New local editorial review considers opening appeal, standalone clarity, useful content and payoff. Each assessment includes a quote from the actual clip.
- Completeness remains the first priority. Among reviewed candidates, the app favors useful answers and resolved stories over empty hooks; clips rated weak on both value and payoff are excluded.
- Podcast discovery now explicitly seeks complete, worthwhile topics without sacrificing necessary context. Interview question-and-answer grouping is preserved.
- Sports selection favors sampled setup/action/aftermath evidence over commentary alone, while retaining a manual-review warning.
- Clip cards and the editor explain selection. Basic checks and visual cues are clearly distinguished from semantic review; none predicts views.
- Reuses existing transcription and performs editorial review within the existing local model call. No new model, AI API, or extra full-video scan.
- New analysis uses a separate cache; previous runs, exports and Used markers remain available. Run analysis again to apply this release to an existing project.

These are our editing criteria, not YouTube's ranking formula. No live trends, channel analytics, guaranteed retention or virality are claimed.

---

# v5.1 · From finished clip to social post

- Accounts screen with Google browser login and Instagram login through Facebook Login for Business; secrets stored in macOS Keychain.
- Saved, per-account publishing drafts use the actual finished export and existing title/description. Optional hashtags are entered manually.
- Review the exact video, account, text, visibility and audience before explicitly publishing.
- YouTube resumable uploads and Instagram direct local-file Reel uploads. No AI model is loaded for posting.
- Publishing history preserves drafts, upload receipts, processing states, errors and published links. Status checks do not create posts.
- One upload at a time, duplicate-attempt warnings, conservative recovery after uncertain responses, and automatic Used marking only after platform confirmation.
- YouTube starts private by default and shows the actual privacy returned by YouTube.

Developer account setup is required before login works. Instagram requires a linked professional account and currently uses a manually pasted OAuth return URL. Scheduling and custom covers are not included. Live login/upload validation requires your configured developer apps; see the validation report.

---

# v4.0 · A cleaner local studio

- New deep-teal and mint theme, custom frame-and-play logo, clearer type, softer cards, and consistent controls.
- Projects are the home screen, with project/run counts and search. The sidebar keeps My projects and New project easy to find.
- Setup is organized around the main choices, with detailed model and duration controls under Advanced settings.
- Clip collection includes search, All / Unused / Used filters, and counts for total, unused, and used clips.
- Workflow indicators appear inside projects rather than cluttering the library and import screens.
- Responsive spacing and visible keyboard-focus styles; native controls retain their labels.

All clipping logic, saved projects, exports, captions, posting copy and Used markers are preserved. Nothing is reanalyzed by the visual update.
