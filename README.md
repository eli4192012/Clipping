# Clipping

A local video clipping studio for this Apple Silicon Mac. No paid AI APIs or accounts.

## Set up from GitHub

This app requires an Apple Silicon Mac. The current development environment uses Python 3.13.14. Install Python 3.13 and put Node.js on your PATH if you want YouTube imports. Then run:

```sh
git clone https://github.com/eli4192012/Clipping.git
cd Clipping
python3.13 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python download_models.py
./Start\ Clipping.command
```

The private repository requires access to the GitHub account. `requirements.lock.txt` records the installed dependency versions; `requirements.txt` lists the direct dependency constraints. Model setup downloads files from Hugging Face and the pinned OpenCV YuNet face detector and needs internet access and several GB of free space. Transcription, model inference and editing then run locally. Alignment and speaker detection have separate optional setup commands described below.

The repository contains the app, tests and documentation. Your videos, saved project transcripts, exports, downloaded models, virtual environments, worker artifacts and credentials stay on this Mac and are excluded from Git. Small regression fixtures in `tests/fixtures/` are included for the tests. Validation reports refer to local media and work files that are not included in a clone. GitHub is a code backup; back up your local projects and exports separately.

Run the test suite after installing the dependencies:

```sh
.venv/bin/python -m unittest discover -s tests -q
```

## Open

Double-click **Start Clipping.command**. The app opens at http://127.0.0.1:8501.
If the page opens before the server is ready, refresh it after a few seconds.
Keep the Terminal window open. Press Control-C there to stop the app.

1. Paste a YouTube link or upload a video, then continue.
2. Choose Interview, Podcast, or Sports. Optional controls are under **Fine-tune the details**.
3. Click **Find my clips**. A percentage bar, elapsed time, and estimated remaining time track processing. Estimates can be exceeded; the app says when work is taking longer.
4. On the completion summary, click **Open my clips**.
5. Choose **Review clip** to render that one standalone clip. Adjust its boundaries if needed, then save the video or subtitles.

The top-right release button is **v5.17**; click it for changes and validation results. Each subsequent shipped user-requested update increments the minor number; the major number stays 5 unless requested otherwise. Release numbering lives in `version.json`, separate from analysis-cache versions.

Saved videos can be reopened from the start screen. Settings and previous results are kept locally. Initial processing estimates use video length and selected review options; later estimates use this video's previous measured processing time. Percentages represent processing milestones, not a promise of constant speed.

## Local models

Balanced uses Whisper base locally on the CPU; Higher quality uses the local Whisper large-v3-turbo model. The Shorts Editor uses Qwen3 4B 4-bit through MLX in either mode. The older continuous-clip workflow can use Qwen3 1.7B in Balanced. Models are downloaded once; subsequent processing uses their local files. No transcript or media is sent to a model service. Streamlit telemetry is disabled and the server binds only to localhost.

If models are missing, double-click **Download Models.command** while connected to the internet. Allow several GB of disk space for dependencies, models, source videos, and exports. English editorial review is recommended. Whisper can detect other languages, but this app's selection rules are English-oriented.

## Current Shorts workflow

Leave **Edit speech into tighter Shorts** enabled to find moments, then choose their real hook, useful explanation and ending. The editor reuses the transcript and can remove selected internal phrases. Its checked decision is saved separately from the original video and transcript. Open a clip to render only that selected edit.

**Edit version** compares the checked edit with the original moment. Supported Fast and Full Context versions can be generated on request. Small ideas do not get artificial extra versions. **Shorts editing decisions** shows what was kept or removed, why, the final transcript, and local checks; download the JSON for debugging. Failed edits remain original drafts for manual review or appear in the selection report.

Caption timing follows the edited timeline. Opening and posting text comes from the final kept speech. Applying manual start/end boundaries exports one continuous source range; restoring suggested boundaries restores the internal cuts. Saved older clips can request a local Shorts edit without rerunning transcription.

These are experimental editing estimates, not predictions of views. The local model can make wrong decisions; listen to joins and compare the original. The larger local editor adds processing time. See V516_VALIDATION.md for measured examples; no whole-video speed guarantee is made. Cold opens, richer scoring and analytics learning remain later work.

## v5.17: finishing the Short

Open a clip to find **Edit / Look / Post / Advanced** tabs. Edit keeps the existing Shorts versions, original comparison and manual boundaries. All packaging uses the selected final timeline, including caption corrections.

- **Look:** Portrait · automatic now samples kept footage across the clip. Speech clips default to Subtle visual pacing: a small progressive punch-in at a useful speech beat, then a wider ending, only when sampled face margins permit it. Off removes this movement; Dynamic permits up to two stronger changes. Some clips correctly receive no zoom. Manual layouts and crop sliders remain available. Automatic Sports framing keeps the full picture and disables speaker switching and pacing.
- **Conversations:** Automatic can put two stable visible speakers in split screen. Active Speaker requires existing anonymous transcript labels and your confirmation of each person's left/right source position. It holds a shot for at least three seconds and ignores brief acknowledgements. Missing labels, unconfirmed positions or unstable scenes use split screen or the full picture. Face sampling does not understand slides, balls or objects; review the visible crop warning and choose full picture when those matter.
- **Captions and hooks:** A few phrases from the final hook/payoff can receive larger bold emphasis or a Gentle pop. Word timing still follows the edited timeline; caption corrections remain supported. Suggested opening text quotes strong kept speech and preserves qualifications. Edit it, use the suggested hook, or leave the field blank to hide it. If a truthful short phrase cannot be established, no hook is invented.
- **Post:** Separate editable YouTube Shorts, TikTok and Instagram Reels packages have native code-block copy buttons. Names and hashtags must occur in the final text; excluded source context cannot silently add a team, league or location. Saved manual copy reopens for the same edit. Hashtags are suggestions, not reach predictions.
- **Covers:** Click Prepare cover options on request. Eight frames are ranked by sharpness, exposure and available face cues; three separated options can receive editable hook text. New automatic exports provide clean source frames without duplicate burned captions. Blinks, expression and identities still need your judgment. Covers download separately; the app does not automatically set a YouTube Shorts cover.
- **Advanced:** Inspect eight editorial assessments with grounded evidence where available; unknown criteria remain unscored. B-roll suggestions give final-output timestamps, a subject, a reason and a suitable source type. Nothing is downloaded or inserted. Saved source ranges and decisions remain available for debugging.

**My review patterns** in the project library summarizes your local ratings. It does not train a model or change ranking. Older reviews remain readable; missing new details are not guessed. Fewer than five highly rated cuts are explicitly treated as insufficient evidence for stable preferences.

Existing saved looks retain their previous rendering until you apply a new style. Sources, transcripts, prior analyses, reviews and exports stay local. Packaging, face samples, posting copy and covers have separate caches; reopening an unchanged edit reuses them. No extra transcription or large-model pass was added. Optional cover generation adds work only when requested. See [validation](V517_VALIDATION.md) for measured time and media checks and [the implementation report](V517_IMPLEMENTATION_REPORT.md) for the repository comparison and remaining limits.

## Historical v1 foundation

- Saves uploads and transcripts locally, with cached transcripts for repeated analysis.
- Builds continuous sentence ranges, checks for context dependence and unfinished endings with a local model, and compares nearby context for misleading cuts.
- Shows unverified candidates separately; model approval is not a guarantee.
- Exports original framing or a padded portrait frame, optional MP4 subtitle tracks, and separate SRT captions.

## Limits

This is not a validated substitute for an editor. Local models and English-oriented rules can miss useful moments or remove necessary context. Long recordings can take substantial time. No live trend research, proven retention scores, YouTube keyword search is included. Active-speaker crops require confirmed positions; they are not verified identity or lip-sync tracking. Captions can be burned in and corrected locally. Portrait output supports automatic or manual crops and full-picture blur. Shorts editing omits source ranges without synthesizing or reordering speech; review its meaning and timing before publishing.

Uploaded copies and transcripts stay under `data/`; exports stay under `exports/`. To remove a video's stored data, stop the app and delete its corresponding folder under `data/`. No automatic deletion occurs.

## Reinstall dependencies

On an Apple Silicon Mac with Python 3.13:

```sh
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python download_models.py
.venv/bin/python -m streamlit run app.py
```

## Components

- faster-whisper: https://github.com/SYSTRAN/faster-whisper (MIT)
- Whisper models: https://github.com/openai/whisper (MIT)
- MLX LM: https://github.com/ml-explore/mlx-lm (MIT)
- Qwen3: https://huggingface.co/Qwen/Qwen3-1.7B (Apache 2.0); quantized distribution: https://huggingface.co/mlx-community/Qwen3-1.7B-4bit
- Streamlit: https://github.com/streamlit/streamlit (Apache 2.0)
- OpenCV YuNet face detection: https://github.com/opencv/opencv_zoo/tree/47534e27c9851bb1128ccc0102f1145e27f23f98/models/face_detection_yunet (MIT; model and license downloaded during explicit setup)
- imageio-ffmpeg: https://github.com/imageio/imageio-ffmpeg (BSD-2-Clause). Its bundled FFmpeg binary has its own LGPL/GPL terms depending on build options: https://ffmpeg.org/legal.html

These dependencies retain their own licenses. Before redistributing a packaged app, include the corresponding notices and comply with the bundled FFmpeg build's terms.

## YouTube links

Select **YouTube link**, paste a watch or Shorts URL, click **Find video**, then **Import & continue**. Imports are limited to 720p and 4 GB and are cached in `data/youtube-VIDEO_ID/`. After import, click **Find my clips** as usual.

Direct-link imports use yt-dlp and the installed Node.js runtime; they do not use YouTube search quotas or require an API key. Internet is needed for lookup and download. Use videos you own or are permitted to download and edit. Private, restricted, live, upcoming, and blocked videos may not import; upload a local copy instead. No browser cookies or account credentials are accessed. A YouTube Data API key would support a future keyword-search feature, not provide media download access.

Dependency: https://github.com/yt-dlp/yt-dlp (Unlicense; optional dependencies have their own licenses). YouTube changes can require upgrading yt-dlp with `.venv/bin/pip install --upgrade "yt-dlp[default]"`.

## Clipping modes

With the Shorts Editor enabled, Interview and Podcast discovery supply broader source neighborhoods, then the editor can shorten them below the preferred duration and omit unnecessary questions. The continuous-clip workflow below remains available by switching that editor off. Sports keeps its existing visual pipeline.

- **Interview** defaults to a preferred 20–65 seconds. With the Shorts Editor off, it favors one question and its complete answer. With the editor on, a checked standalone answer can start directly and be shorter.
- **Podcast** defaults to 30–80 seconds. Favors story setup and a conclusion or payoff, with a story-specific local review.
- **Sports** defaults to 10–35 seconds. Samples video twice per second and uses visual transitions, low-motion runs, activity, and commentary cues. It does not use punctuation as the visual endpoint. Sports suggestions are always marked for manual review: motion and cuts do not prove that a play has finished. Camera movement, replays, and graphics can confuse these signals. It is not a trained sports action model.

All modes apply a final non-overlap filter and source-coverage budget. Current UI defaults permit up to 100% of the source for speech and 35% for sports; these are ceilings, not targets. Edited coverage and overlaps count only kept source ranges. There is no clip-count maximum; an optional minimum target never forces weak or duplicate clips into results. Fewer or zero clips are valid. Clips are not shortened solely to fit the coverage budget. Manually changing source boundaries can introduce overlaps. The selected clip renders when opened for review.

Choose a mode and click **Find my clips** again. Mode/version-specific caches prevent the previous overlapping suggestions from appearing as new results. Transcripts remain reusable. Sports can process silent videos; captions are omitted when no words fall inside the exported range.

## Extracted previews

Clips render as standalone MP4 files only when opened from the collection. Their players start at 0:00 and contain only the selected segment. **Save video** downloads that exact clip. Start/end fields use original-video timestamps. Adjusting either boundary or portrait framing regenerates the clip; unchanged renders are reused. Extracted files are also saved in `exports/`. Surrounding source footage is available in the editor's context expander.

## Sports and editing upgrades — September 27

Sports drafts add two seconds of setup and aftermath where available, look up to eight seconds ahead for sustained lower motion, and can finish nearby commentary. A shot change alone is not considered a settled ending. These remain heuristics, not complete-play recognition. Length settings are targets; context may extend them, but the non-overlap and total-footage limits still apply afterward.

Use **Apply boundaries** to render an edited range once. Changes are stored locally for that analysis. **Restore suggested boundaries** returns to the automatic range. Expand **Watch surrounding context in the original video** to inspect the lead-in and ending; the main clip preview remains a standalone MP4 starting at zero. Manually introduced overlaps show a warning.

Refresh and click **Find my clips** to generate the upgraded sports results. Existing exports are retained.

## Experimental local football vision review

Sports mode now has **Review football video frames locally**, enabled by default. It uses Qwen3-VL-2B-Instruct (4-bit, Apache 2.0) with MLX-VLM. The model is installed in `models/sports-vision`; Download Models.command can reinstall it. No API key is needed, and inference runs with Hugging Face offline mode enabled.

The pipeline first locates event words in commentary, groups nearby mentions, then reviews timestamped video frames around selected candidates. Individual frame descriptions supply setup/action/closeup hints. An ordered sequence can suggest boundaries; ambiguous sequences produce clearly marked context drafts. It does not prove a touchdown occurred or reliably distinguish a replay. It currently targets American football. For other sports or silent footage, turn visual review off to use motion-based drafts.

**Event windows to inspect** defaults to two, adjustable to six. When there are more candidates, review is spread across the video; it does not inspect every play or guarantee the best moments. Each window can take several minutes on an 8 GB Mac. Reviews are cached; the vision process exits after each window to release memory. A timeout or invalid output becomes an uncertain draft, never a passed review.

Visual windows sample 16 frames at two-second intervals, from roughly 12 seconds before the event mention to 18 seconds afterward. Fast action and heavily delayed commentary can be missed. The length minimum is enforced; the maximum may expand by up to 16 seconds for context. Final non-overlap and total-footage limits still apply.

The app warns when likely football footage is processed in a speech mode. Football transcript-only reviews cannot receive a passed visual-play assessment. Model inference and clip export work locally; high-quality complete-play recognition remains experimental.

Components: https://github.com/Blaizzy/mlx-vlm and https://huggingface.co/mlx-community/Qwen3-VL-2B-Instruct-4bit .

## Interview structure upgrade

Interview mode now groups subject introduction → question → answer and excludes the setup of the next detected question, including declarative setup sentences. It flags unresolved pronouns in the opening. A complete exchange can be shorter than the requested minimum; an overlong answer is skipped rather than cut to meet the maximum. With local AI review enabled, a separate ending-selection pass can shorten an exchange at a sentence boundary before the completeness review. Invalid model output retains the transcript-grouped boundary and is noted. Final overlap and footage limits still apply.

Football interviews remain appropriate for Interview mode. A football-related word alone no longer fails every speech review or forces Sports mode. Speech review labels describe transcript completeness only, never whether an on-field play is visible.

The segmentation infers interviewer turns from language, punctuation, named subjects, and transition cues; it is not verified speaker diarization. Unusual phrasing and transcript errors can still confuse it. Original dialogue and subtitles are not silently rewritten. Refresh and run **Find my clips** again to use the new analysis version; previous exports remain intact.

## v2.1 quality choices

Choose **Higher quality** for MLX Whisper large-v3-turbo, Qwen3-4B transcript review, and Qwen3-VL-4B sports review. **Balanced** retains the original smaller models. Both use local files and separate analysis caches. Sports can use PySceneDetect and now samples 24 frames from up to 24 seconds before commentary through 22 seconds after it. The footage limits still apply.

Model workers run separately and serialize large-model tasks to limit memory pressure. An expensive stage can hold at its current milestone while the elapsed clock continues. Larger models are not a guarantee of better boundaries.

Optional WhisperX alignment and pyannote Community-1 run in `.venv-speech` because their dependencies differ from the main app. **Setup Alignment.command** installs that environment and the English alignment model. **Setup Speakers.command** uses a hidden token prompt after you accept the model conditions on Hugging Face; the token is not saved. Unsupported languages must leave alignment off. Speaker labels are estimates, not verified identities.

See RELEASE_NOTES.md and V2_VALIDATION.md for the release report and measured checks. React/FastAPI migration is deferred; this release improves local processing within the existing interface.

## v2.2 controlled interview comparison

Open a saved video, choose **Interview**, and click **Compare the same moment**. Enter a source timestamp inside a question or answer. The selected processing quality supplies one shared transcript. Balanced and Higher quality independently review that same exchange; they cannot choose different topics. Both previews are standalone exported MP4s, with source bounds and durations displayed. Saved comparisons can be reopened from the comparison screen.

In an individual clip or comparison, expand **Rate this cut** to save 1–5 ratings for opening, ending, context, and pacing, plus notes. Scores are stored under the project's `reviews/` folder and can be downloaded. They describe your judgment and do not automatically train or rank clips.

The new interview rules remove generic previous-answer lead-ins, respect available speaker boundaries, protect referenced subjects, and require transition evidence before shortening an answer. Up to 0.5 seconds of post-answer room can be added when the transcript shows a gap; it stops before the next transcribed word. Transcript mistakes can still affect boundaries. Existing videos and results remain saved; rerun analysis for the new rules.

## v2.3 sports discovery

Sports mode now proposes multiple kinds of commentary events and supplements them with coarse visual activity across the source. Cue timing uses available word timestamps. Nearby mentions within 12 seconds are grouped; this is a heuristic, not verified play identity. Proposals are ranked with some preference for covering different parts of the video. Six windows are reviewed by default for this upgrade; choose 1–12 in the settings details. More windows can take substantially longer on this Mac. The separate 1–5 clip limit, strict non-overlap, and 35% footage budget remain.

The completion screen includes a downloadable sports diagnostics report. “Found” means proposed windows; “review attempts” includes unsuccessful visual runs; “clips kept” means final drafts. Neither motion nor a keyword proves a complete or important play. See V23_VALIDATION.md for measured results.


## v3.3 workflow

Use Interview for press conferences, Podcast for stories/discussion, and Sports for action. Higher quality speech selections must pass a local completeness check. In Fine-tune, maximum source coverage defaults to 100% for speech; this permits distinct topics without requiring the app to use every second. No overlap is allowed. Complete topics can be shorter than the preferred duration; the maximum still applies.

Open a finished clip and expand Layout, captions & title. Choose original, full-picture portrait, fixed speaker crop, or two-speaker stacked crops. Set the crop sliders, edit or clear the opening title, and apply. Captions highlight words locally; check transcription of names. Full picture is safest for action and changing camera shots. Fixed crops do not track faces. Settings are saved per clip. Click v3.3 for release notes and validation.

## v3.4 polish

Existing clips can use the new controls without reanalysis. In **Check names & edit captions**, supply known names if useful, review possible spelling hints, edit the Caption column, and save. Restore originals to undo edits. Corrections are saved beside the transcript and shared by clips using it; the original transcript and timing stay untouched.

In **Layout, captions & title**, use **Suggest a clearer title locally** or type your own. Optional quiet-edge trimming is off by default, requires quiet audio and word-timing agreement, and trims at most 0.3 seconds per edge. It does not remove internal pauses. Newly analyzed clips receive the revised headline pass automatically.

## v3.5 automatic portrait interviews

Enable Vertical video in Interview mode. New clip layouts default to Automatic interview. For existing clips, choose **Portrait · automatic interview** under Layout, captions & title, then Apply style. Stable single-person footage is cropped closer; modest movement can use a closer foreground over blur; uncertain or group footage keeps its full picture. Full-picture portrait has a moving blurred-video background, not black padding. Original landscape output is unchanged.

The small local YuNet detector model is from https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet and is saved under models/face-framing with its MIT license. If unavailable, automatic framing falls back to full-picture blur. This is sampled face detection with a fixed crop, not active-speaker tracking. User-selected manual layouts are preserved.

## v3.6 video-type detection

Automatic type selection is enabled on the settings page. Detection reuses a saved transcript or transcribes up to 60 seconds locally, then combines speech/title cues with sampled faces. It chooses Interview, Podcast, or Sports and displays a reason and confidence label. Turn off **Choose the video type automatically** to override. Podcast is the general speech fallback for unclear content; Sports remains best suited to football. Detection is cached against the source file and title, with no changes to the original video or transcript.

## v3.7 clip count and speed

There is no clip-count maximum. Set an optional minimum target if useful; the completion page reports whether it was reached. All suitable clips are selected within coverage, duration, overlap, and search constraints. A minimum never forces weak or duplicate clips into the collection.

Completed analyses and individual topic reviews are cached. Changing just the minimum target is inexpensive. New titles are produced with the completeness review, avoiding a separate model call per topic; use Suggest a clearer title locally when wanted. First-time long-video transcription and sports frame inspection still take time.

## v3.8 saved projects

Open **My projects** in the sidebar to search videos, select an earlier analysis run, reopen saved clips, or continue changing settings. New runs retain their exact settings. Settings changes autosave; clip edits, caption corrections, styles and exports remain saved in their existing locations. Older runs are discovered automatically using their saved metadata. Project files are local, not a cloud backup, and processing interrupted by server shutdown must be resumed by running analysis again (completed caches are reused).

## v3.9 responsiveness

Balanced is the recommended default for an 8 GB Mac. Heavy jobs queue one at a time; encoding/filtering and Balanced transcription use two threads. Workers run at lower priority when permitted. MLX cache is limited to 128 MB, with a 3 GB allocation ceiling (not a total-process memory cap). Large jobs may fail and require Balanced or a shorter source. Restart the server after updating; already-running workers retain old limits.
