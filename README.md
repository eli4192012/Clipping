# Clipping

A local video clipping studio for this Apple Silicon Mac. No paid AI APIs or accounts.

## Set up from GitHub

This app requires an Apple Silicon Mac. The current development environment uses Python 3.13.14. Install Python 3.13 and put Node.js on your PATH if you want YouTube imports. Then run:

```sh
git clone --branch codex/v5.17-visual-packaging https://github.com/eli4192012/Clipping.git
cd Clipping
python3.13 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python download_models.py
./Start\ Clipping.command
```

The repository is public. The setup command selects the development branch in [draft PR #1](https://github.com/eli4192012/Clipping/pull/1), which contains the version described here. `requirements.lock.txt` pins the complete main environment, including MLX Whisper, scene detection and Keychain support; `requirements.txt` lists the direct dependency constraints. Model setup downloads files from Hugging Face and the pinned OpenCV YuNet face detector and needs internet access and several GB of free space. Transcription, model inference and editing then run locally. Alignment and speaker detection have separate optional setup commands described below.

The repository contains the app, tests and documentation. Your videos, saved project transcripts, exports, downloaded models, virtual environments, worker artifacts and credentials stay on this Mac and are excluded from Git. Small regression fixtures in `tests/fixtures/` are included for the tests. Validation reports refer to local media and work files that are not included in a clone. GitHub is a code backup; back up your local projects and exports separately.

Run the test suite after installing the dependencies:

```sh
.venv/bin/python -m unittest discover -s tests -q
```

For development checks, install `requirements-dev.txt`, then run `.venv/bin/ruff check .`, `.venv/bin/python -m pip check` and `.venv/bin/python scripts/check_install.py`. The import check does not download or load model weights. GitHub Actions runs the same checks and regression tests on an Apple Silicon Mac, starting with a fresh environment. Lint checks syntax and undefined names in first-party code; vendored upstream files are excluded.

When direct dependencies change, regenerate the lock on Apple Silicon with Python 3.13 using `.venv/bin/uv pip compile requirements.txt --python .venv/bin/python --no-header --no-annotate --no-emit-index-url --output-file requirements.lock.txt`, then test installation in a fresh environment. The existing lock keeps compatible pins unless explicitly upgraded. The sound and optional speech environments remain separate.

## Open

Double-click **Start Clipping.command**. The app opens at http://127.0.0.1:8501.
If the page opens before the server is ready, refresh it after a few seconds.
Keep the Terminal window open. Press Control-C there to stop the app.

1. Paste a YouTube link or upload a video, then continue.
2. Choose Interview, Podcast, or Sports. Optional controls are under **Fine-tune the details**.
3. Click **Find my clips**. A percentage bar, elapsed time, and estimated remaining time track processing. Estimates can be exceeded; the app says when work is taking longer.
4. On the completion summary, click **Open my clips**.
5. Choose **Review clip** to render that one standalone clip. Adjust its boundaries if needed, then save the video or subtitles.

The top-right release button is **v5.30**; click it for changes and validation results. Each subsequent shipped user-requested update increments the minor number; the major number stays 5 unless requested otherwise. Release numbering lives in `version.json`, separate from analysis-cache versions.

Saved videos can be reopened from the start screen. Settings and previous results are kept locally. Initial processing estimates use video length and selected review options; later estimates use this video's previous measured processing time. Percentages represent processing milestones, not a promise of constant speed.

Individual and combined exports report progress from FFmpeg's encoded output time. A wall-clock watchdog stops a hung export, terminates its process, and removes its new partial video. The limit is the larger of three minutes or twelve times the output duration plus one minute; it is a failure limit, not a processing estimate. Saved source videos, transcripts, earlier exports and analysis caches remain available.

Failed operations keep private diagnostics in `work/logs/app.log`, independent of the launch directory. Logs rotate at 1 MiB with three backups and stay excluded from Git. General and account errors record exception types and call locations without exception messages, locals, transcripts or provider responses; worker failures retain child traceback locations before temporary files are removed. FFmpeg errors keep a bounded diagnostic tail with URLs and token fields removed.

## Complete-idea selection

Enable **Keep complete ideas with AI** in clip preferences. Balanced edits keep the subject, the useful explanation and the conclusion. They favor complete sentences, restore unfinished speech split across transcript pauses, and limit internal deletions to clear acknowledgements, literal repetition or discussion references. The editor keeps the question when the answer needs it, and interview edits may contain at most one detected reporter question. Fast remains an optional shorter version.

The duration slider is a preferred range, not a reason to add unrelated speech. A genuinely brief complete idea can be shorter when the final check explains why no useful explanation is missing. Ideas that cannot fit the maximum are skipped instead of being chopped in half. Unverified edits appear only as original moments in the selection report, in either processing mode.

Earlier analyses stay available. Open an older collection or clip and click **Find fuller clips with updated AI** to create a separate analysis using the saved transcript. New editing and review caches have their own selection version; transcription caches and the global analysis version stay unchanged. Local AI still makes mistakes, especially with missing punctuation or mixed speakers, so review the final speech before posting.

## Local models

Balanced uses Whisper base locally on the CPU; Higher quality uses the local Whisper large-v3-turbo model. Under **Advanced settings · duration, coverage & models → AI editor**, choose **Qwen3 · 4B (recommended)** or **Qwen3.5 · 4B (experimental)**. Both use 4-bit local MLX inference and apply in either processing mode. Qwen3 remains the default: the initial saved-video comparison did not establish more reliable edits with Qwen3.5. Older saved settings retain their original model choice, including Qwen3 1.7B for legacy Balanced continuous clips.

Qwen3.5 is downloaded once to `models/qwen3.5-4b` (about 3.06 GB) from a pinned MLX Community revision. On this Mac the existing dependencies support it; no other AI application or account is required. To install only this editor, run `.venv/bin/python download_models.py --editor-only`; the normal model setup also installs it. Application processing never downloads missing weights. MLX LM loads only its text tower for transcript editing; this update does not change sports frame review or add AI ordering to combined videos.

Changing the AI editor creates separate analysis, topic and edit-decision caches. Existing transcripts are reused, old results stay saved, and repeated work with the same model reopens cached decisions. Inference runs one model process at a time with the existing 3 GiB MLX limit, small prompt-prefill batches and a bounded context; oversized source neighborhoods fail for review instead of silently losing text. No transcript or media is sent to a model service. Streamlit telemetry is disabled and the server binds only to localhost. See [v5.19 validation](V519_VALIDATION.md) for comparison results and limitations.

If models are missing, double-click **Download Models.command** while connected to the internet. Allow several GB of disk space for dependencies, models, source videos, and exports. English editorial review is recommended. Whisper can detect other languages, but this app's selection rules are English-oriented.

## Choose moments using speech, visuals and sound

v5.28 adds a local curation pass after speech editing and before final clip selection. In project settings, enable **Use speech, visuals & sound to choose clips**, choose how many moments to review visually (1–6, default 3), then **Find my clips**. When sound setup is present, the option defaults on for settings without a saved choice. Existing saved analyses reopen as before; **Adjust settings** starts a separately cached analysis using the new option.

The pass reuses your transcript and grounded speech review. Google's local **YAMNet** classifies source-timed sound windows, including speech, music and possible laughter/applause/cheering. The installed **Qwen3-VL 4B** examines three frames across each selected moment's retained source ranges; a cheap scan records motion and camera changes. Interview, Podcast, Sports, Music and Gaming presets weight supporting cues differently. These are transparent editing rules, not a newly trained genre or emotion model. Supporting cues make only small priority adjustments; rejected/incomplete clips and the one-question interview limit stay authoritative.

The first setup needs internet access; subsequent inference runs offline. Install sound separately so TensorFlow does not alter the app's MLX dependencies:

```sh
.venv/bin/python setup_sound.py
```

This uses pinned dependencies in `.venv-audio`, unmodified Apache 2.0 YAMNet source, and checksum-verified official model weights (about 15.3 MB). Dependencies need additional disk space. Sound is already installed on the development Mac. The normal `download_models.py` setup provides the 4B vision model; no additional vision weights were downloaded for this release. Missing models and failed observations stay visibly unavailable.

Open **Speech, visuals & sound evidence** in the collection to inspect reviewed moments. For an older clip, use **Advanced → Review this moment with speech, visuals & sound**. That button reviews the current final cut without applying edits, rendering a new export or changing posting text. Evidence includes source timestamps, actual frames, uncertain observations, available signal weights and downloadable JSON. Viewing evidence runs no model. Cached sound, motion, frame observations and complete reports are reused; different source files, cuts, transcripts, genre or model configuration get separate reports. Stale cut/source evidence is hidden until reviewed again.

This first version reviews only a limited set of existing candidate moments visually. It does not use emotion inference, learn from analytics, certify a completed sports play or predict views. The small saved-video trials show that cues can change priority, but do not establish better clip quality or audience retention. The smaller 2B vision model produced unreliable labels during testing; this pass uses 4B and marks detected contradictions uncertain. Inference still makes mistakes, so inspect frames and listen before posting. See [v5.28 validation](V528_VALIDATION.md) for measured results and preservation checks.

## Combine clips into a longer video

Choose **Combine clips** in the sidebar, or **Add to combined video** while reviewing a finished clip. You can use clips from multiple saved projects.

1. Give the combined video a name. **Wide · 16:9** is the default (1280 × 720); vertical output is also available.
2. Find saved clips by project or title, choose them and click **Add selected clips**. Clips appear in the order you add them.
3. Use **↑ / ↓** to change the order or **Remove** to remove a clip from this combination. Your order and settings save locally; **Saved combinations** reopens them later.
4. Click **Export combined video**. The app joins the finished clips, saves one MP4 and combines available SRT captions with updated timestamps. Clip titles become chapter markers and a downloadable timestamp list.
5. Use **Show video in Finder**, or **Prepare video download → Save combined video**. Preview and browser download load the longer video only when requested.

Clips retain their finished captions, opening text and framing. Vertical clips fit into a wide canvas with a blurred background by default; turn that option off for a dark background. This step does not restore picture areas cropped out of a finished clip. For footage that should fill a wide video, choose Original framing when reviewing that clip before adding its new export. Open **Review clip** once for any suggestion that has not been rendered yet; only finished exports appear in this builder.

Combinations use direct cuts, without new transitions, speech changes or AI analysis. Review the story and joins yourself. Changes to an individual clip produce a new saved version that you can add; an existing combination keeps the version you selected. Changing a combination leaves prior exports intact and visibly marks the last export as outdated until you export again.

All processing stays on this Mac. The exporter prepares one clip at a time, handles differing shapes/frame rates and silent clips, and caches prepared media. An unchanged combination reuses its output; changing order reuses its prepared clips. Sources, transcripts and separate clip exports remain intact. Temporary prepared media lives under work/assembly-renders/ and can take additional disk space. See [v5.18 validation](V518_VALIDATION.md) for measured results and limits.

## Example library

Choose **Example library** in the sidebar to collect clips and published titles for future AI improvements. This Mac's v5.23 library includes the seven supplied examples, their saved transcripts and sampled frames, the actual posted titles and available analytics. A fresh clone starts with an empty library because these personal records are excluded from Git.

Search by title or notes, filter good patterns/mixed examples/patterns to avoid, and choose a clip. **Show clip preview** loads its video on request. Review **What works** and **What to avoid copying** together: a successful post can still contain a weak start, an unsupported title claim or an extra interview question. Analytics retain their export period and engaged-view counts. A possible YouTube match remains unconfirmed until you mark it confirmed; percentages from tiny audiences are not automatic quality scores.

Use **Review and edit example notes** to change its displayed name, actual posted title, opening text, lessons and notes. Mark a record ready for future reference only after reviewing its lessons. **Add an example** saves a supplied video and optional transcript without transcription, rendering or model inference. Adding the same file keeps its earlier notes. **Download example library** saves all reference records as JSON.

The library lives in data/example-library/. The opening writer uses up to three unexcluded **Good pattern** records' saved opening/headline lessons as presentation guidance, including lessons saved before the full record is marked ready. That review flag still concerns the full record, transcript and analytics association; those facts and metrics are not used to write another clip. Selection, speech cuts, social posting copy and model weights retain their existing behavior. The seven original imported videos are referenced at their existing locations; keep those files or restore them if moved. Their library notes, transcripts and sampled frames remain available even when an original is missing. New uploaded examples are copied into the library's assets folder. Back up that folder along with your other local projects.

## Improve the opening

Open a clip and choose **Look → Improve the opening with AI → Generate AI opening**. The installed local editor reads the final kept transcript and the first three seconds, tries several short hooks, and checks a selected hook in a separate pass. The aim is to name the subject immediately and preview its actual takeaway rather than display filler or a generic quote. Read **Why this fits the clip**, then choose **Apply this opening text** to render it. It appears from the first frame for up to three seconds. This step improves opening text; it does not move the spoken opening or ending.

Generating alone keeps the current style and preview. **Generate a fresh opening** requests new inference; reopening the same cut reuses its checked cache without loading a model. Changed cuts, caption corrections, first-speech timing, model or presentation lessons produce a separate cache. Only a successful check is saved; a failed fresh attempt retains the earlier suggestion and style. Your manual opening field remains editable and can be left blank to hide it. Applying an AI opening preserves the other saved styling choices and creates a new export without deleting earlier exports.

Everything uses existing local transcripts and model weights. Sports and silent clips use manual text. Supporting quotes and the second model pass reduce mistakes but do not establish factual reliability: the same model can approve its own mistaken paraphrase. Review meaning, qualifications and promised answers before applying. No virality or retention gain is claimed. See [v5.24 validation](V524_VALIDATION.md).

## Current Shorts workflow

Leave **Edit speech into tighter Shorts** enabled to find moments, then choose their real hook, useful explanation and ending. The editor reuses the transcript and can remove selected internal phrases. Its checked decision is saved separately from the original video and transcript. Open a clip to render only that selected edit.

**Edit version** compares the checked edit with the original moment. Supported Fast and Full Context versions can be generated on request. Small ideas do not get artificial extra versions. **Shorts editing decisions** shows what was kept or removed, why, the final transcript, and local checks; download the JSON for debugging. Failed edits remain original drafts for manual review or appear in the selection report.

Caption timing follows the edited timeline. Opening and posting text comes from the final kept speech. Applying manual start/end boundaries exports one continuous source range; restoring suggested boundaries restores the internal cuts. Saved older clips can request a local Shorts edit without rerunning transcription.

These are experimental editing estimates, not predictions of views. The local model can make wrong decisions; listen to joins and compare the original. The larger local editor adds processing time. See V516_VALIDATION.md for measured examples; no whole-video speed guarantee is made. Cold opens, richer scoring and analytics learning remain later work.

## v5.17: finishing the Short

Open a clip to find **Edit / Look / Social media / Advanced** tabs. Edit keeps the existing Shorts versions, original comparison and manual boundaries. All packaging uses the selected final timeline, including caption corrections.

**Edit → Improve the ending with AI** reviews only this selected clip. Choose a local ending editor, generate a suggestion, inspect the main-point/payoff quotes and removed speech, then explicitly **Apply this ending**. The choice starts with the project editor; changing it here does not change project settings. The reviewer can recommend keeping the current ending. It offers complete source-sentence boundaries, trims only a suffix of the selected speech, preserves earlier internal gaps and rejects cut-off words, unanswered questions, multiple interview questions and directly dependent closing qualifications. It reuses the original saved timed transcript and limited ending observations from the example library; example facts and analytics are not evidence. Sports and silent clips use manual boundaries. It does not extend a cut or pick a different opening.

Applying saves a separate ending override and creates a new final-cut package/export; existing analysis, caption corrections, source media, posting copy and exports stay saved. **Restore prior ending** reopens the earlier cut, while manual boundary edits and **Restore suggested boundaries** clear that cut's ending override. Generation alone does not render or publish. Reopening reuses the checked decision. Editing opening text keeps an applied cut and warns when the old ending review used different text; another review gets a separate cache key. Model checks can reject good cuts or approve poor ones; listen and review before sharing. See [v5.26 validation](V526_VALIDATION.md).

- **Look:** Portrait · automatic now samples kept footage across the clip. Speech clips default to Subtle visual pacing: a small progressive punch-in at a useful speech beat, then a wider ending, only when sampled face margins permit it. Off removes this movement; Dynamic permits up to two stronger changes. Some clips correctly receive no zoom. Manual layouts and crop sliders remain available. Automatic Sports framing keeps the full picture and disables speaker switching and pacing.
- **Conversations:** Automatic can put two stable visible speakers in split screen. Active Speaker requires existing anonymous transcript labels and your confirmation of each person's left/right source position. It holds a shot for at least three seconds and ignores brief acknowledgements. Missing labels, unconfirmed positions or unstable scenes use split screen or the full picture. Face sampling does not understand slides, balls or objects; review the visible crop warning and choose full picture when those matter.
- **Captions and hooks:** A few phrases from the final hook/payoff can receive larger bold emphasis or a Gentle pop. Word timing still follows the edited timeline; caption corrections remain supported. Suggested opening text quotes strong kept speech and preserves qualifications. Edit it, use the suggested hook, or leave the field blank to hide it. If a truthful short phrase cannot be established, no hook is invented.
- **Social media:** Opening this tab generates a hook title and a brief description for the YouTube package using the selected local 4B editor. It proposes different question/contrast/takeaway hooks and a second source check picks the strongest supported title, discarding unsupported ideas. **More title ideas** lets you choose another checked hook when available. Hashtags stay inside the title, within 100 characters. Descriptions use fresh words about this final clip; copied transcript passages are rejected. A silent clip needs manual posting text. AI writing works without a connected social account.
- **Posting corrections:** A rejected draft receives one local repair using its actual wording, the checker's reason and the final transcript. Distinctive terms and their conditions/outcomes must stay tied to the supporting source statement. The corrected draft passes the same checks before it is saved. A remaining failure shows a short explanation and offers fresh generation or manual editing; worker tracebacks stay out of the form. These model checks can still make mistakes. Review the copy before posting. See [v5.25 validation](V525_VALIDATION.md).
- **Saved posting text:** Opening Edit or Look does not start posting inference. Social media generation runs once for missing text and reuses checked copy for the same final transcript, writer version and model. Earlier AI copy is refreshed with the new writer; legacy quoted descriptions are replaced while separately edited titles are preserved. Saved manual text remains authoritative. **Generate title & description with AI** explicitly replaces the fields; **Generate fresh text** requests new inference. Failed automatic generation does not retry on every rerun, overwrite saved files or insert the transcript as a fallback. Nothing is published by generating text. Existing reviewed publishing drafts retain their wording; **Use current posting text in this draft**, then **Save draft & review**, applies new copy to an editable draft. TikTok and Instagram packages remain editable with inline tags. See [v5.22 validation](V522_VALIDATION.md).
- **Covers:** Click Prepare cover options on request. Eight frames are ranked by sharpness, exposure and available face cues; three separated options can receive editable hook text. New automatic exports provide clean source frames without duplicate burned captions. Blinks, expression and identities still need your judgment. Covers download separately; the app does not automatically set a YouTube Shorts cover.
- **Advanced:** Inspect eight editorial assessments with grounded evidence where available; unknown criteria remain unscored. B-roll suggestions give final-output timestamps, a subject, a reason and a suitable source type. Nothing is downloaded or inserted. Saved source ranges and decisions remain available for debugging.

**My review patterns** in the project library summarizes your local ratings. It does not train a model or change ranking. Older reviews remain readable; missing new details are not guessed. Fewer than five highly rated cuts are explicitly treated as insufficient evidence for stable preferences.

Existing saved looks retain their previous rendering until you apply a new style. Sources, transcripts, prior analyses, reviews and exports stay local. Packaging, face samples, posting copy, opening text and covers have separate caches; reopening an unchanged edit reuses them. Rendering reuses transcription. AI opening generation and cover preparation add work only when requested; Social media writing follows the triggers described above. See [visual packaging validation](V517_VALIDATION.md) for its measured time/media checks and [the implementation report](V517_IMPLEMENTATION_REPORT.md) for the repository comparison and remaining limits.

## v5.27: compare before and after

Open **Before & after** in the sidebar to play saved pairs, read their opening text, posting titles/descriptions and last thoughts, inspect source ranges and check measured stage times. Rate the pair and save your notes locally. Earlier runs remain available through **Show earlier comparison runs**. The initial local collection compares four saved moments; it is not included in a fresh GitHub clone.

To create another pair, open a saved clip and choose **Edit → Compare before and after**. The comparison reconstructs the prior selected timeline and opening, then reviews a copy: opening first, ending second, and another opening check if the speech changes. Posting text uses the final transcript. Both sides use the same caption rendering and full-picture layout so camera planning does not confound the comparison. The baseline uses the saved cut, not a rerun of historical discovery software. When an AI opening has already been applied, its literal transcript hook reconstructs the baseline; an earlier manual opening is not recoverable unless separately saved. Caption corrections are shared by both sides.

The comparison runs offline with the recommended installed Qwen3 editor. It reuses transcription and discovery, caches checked decisions and renders, and never applies its suggestions to your active project. Failed ending reviews keep the prior speech. A failed final-cut opening check leaves that overlay empty, and unverified new posting copy is left empty rather than borrowing text for a different cut. Sports comparisons retain the manual cut and text. Source/transcript/media changes mark saved comparisons unavailable while retaining their notes. Viewing a saved pair starts no model or render job.

One unfinished comma-ended question can continue across a short pause when the next clause starts in lowercase and the voice does not change. Completed questions, distinct voices, long pauses and numbered multiple questions remain separate. The comparison exposed this counting bug; the fix does not change the analysis-cache version or existing discovery results. See [comparison validation](V527_VALIDATION.md) for actual results and known model errors. A source self-check can accept incorrect relationships between otherwise real words; the comparison does not certify accuracy or predict views.

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
- Qwen3.5: https://huggingface.co/Qwen/Qwen3.5-4B (Apache 2.0); pinned 4-bit distribution: https://huggingface.co/mlx-community/Qwen3.5-4B-MLX-4bit/tree/32f3e8ecf65426fc3306969496342d504bfa13f3
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
