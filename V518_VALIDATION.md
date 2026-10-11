# v5.18 validation

All **201 tests passed**, including all 190 prior tests and 11 new tests. The final suite completed in 6.780 seconds on the existing Apple Silicon Mac. Syntax and whitespace checks are recorded alongside the final release checks.

## Media and workflow coverage

Real FFmpeg tests combine wide and vertical footage with different source frame rates (25 and 24 fps), 44.1 kHz mono audio and a silent clip. Output has a common canvas, approximately 30 fps video and 48 kHz stereo audio. Decoded color frames establish clip order; visible edge markers establish that fitting retains both edges of the portrait picture. The 440 Hz tone is retained and the silent section remains silent. Available captions appear in the external SRT and embedded subtitle track at shifted times. Embedded chapter titles match clip order.

Additional checks cover vertical output, dark padding, missing subtitles, missing clips and malformed captions rejected before encoding, subtitle offsets exceeding one hour, caption-end clamping, original input size/mtime preservation, old render/ASS discovery, indexed clips, saved order and invalid draft paths. An unchanged combination cannot call the encoder; reordered combinations cannot normalize existing parts again.

Streamlit AppTest checks cover the default wide shape, adding clips from multiple projects, moving/removing clips, naming and saved settings, disabled export with one clip, saved result reopening without inference, sidebar navigation without an active project and the editor's exact finished-version registration/Add action. UI rendering is mocked; real media behavior is tested separately.

## Real saved-clip export

Four existing local portrait exports were joined: the checked running-back explanation, the checked kicker discussion and two saved football clips. This is a technical export sample, not a newly reviewed editorial story. Their existing burned captions, opening text and framing were retained and fitted into a wide canvas. Representative decoded frames were inspected. The football clip already had its own full-picture portrait treatment; the combiner preserves that rather than reconstructing its original wide source.

| Measurement | Result |
|---|---:|
| Selected clips | 4 |
| Sum of original export durations | 82.196 s |
| Combined duration | 82.266 s |
| Output canvas | 1280 × 720 |
| Decoded video frames | 2,468 |
| Embedded chapter count | 4 |
| Audio and embedded subtitles | Present |
| Video timestamps | Strictly increasing |
| Fresh export | 17.138 s |
| Unchanged cached export | 0.0017 s |
| Reordered export, reusing prepared clips | 1.424 s |

Duration increases slightly because each input is fitted to complete output frames, retaining its last image/silence where needed. No input speech is synthesized or reordered inside a clip. The assembly order is user-controlled. The final subtitle file and chapter offsets use measured prepared-part durations, rather than the source's discovery timestamps.

These are single-machine samples, not time guarantees for longer recordings. Initial library discovery found all 132 existing clip exports readable in 0.90 seconds. Small metadata records are cached. The exporter limits FFmpeg threads, prepares one clip at a time and uses temporary lossless PCM audio, then encodes AAC once across the final join. Prepared video can be copied into reordered combinations without another video encode. This uses extra temporary disk space and one video re-encode on first preparation; it is not a bit-for-bit media join.

Local artifacts are under work/v518-validation/, excluded from Git. The sample is exports/combined-1d43ea4a9f7ecacb8fa8b526.mp4; reordered sample is exports/combined-2f6cdb40a4bd93356aa3bc06.mp4. Their SRTs, chapter lists and assembly manifests are stored beside them. No social publication occurred.

## Preservation and limits

Saved combinations are new files under data/assemblies/. Finished-clip indices are additional per-project records; existing analysis structures are unchanged. Render/metadata caches use new work/assembly-* paths. Existing source videos, transcripts, model files and individual exports are retained. The analysis-cache VERSION is unchanged; the release badge is v5.18.

A before/after size-and-mtime inventory checked 1,213 preexisting files under data, exports and models; all retained their recorded attributes. A clean checkout containing only Git-included files opened the v5.18 library and empty combination builder, with wide output selected and export disabled until two clips are added. That startup check prohibited socket.create_connection and had no project media or downloaded models. Syntax compilation and git diff whitespace checks also passed. The export does not reassess story coherence or recover areas already cropped out of a clip. Direct cuts can sound abrupt; human listening and editorial ordering remain necessary. No multi-hour benchmark, disk-exhaustion recovery test, audio loudness matching, crossfades, automatic narration or social publication was performed. Preview/browser downloads remain on request to avoid automatically loading long videos when reopening a saved combination.
