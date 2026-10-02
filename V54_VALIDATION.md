# v5.4 validation

- 110 regression tests passed. Added checks for native portrait preservation, safe crops despite subject movement, source-edge headroom, and blur fallback when movement cannot fit.
- Rendered and decoded two real three-second clips at 720×1280: the supplied Alec injury reference (native portrait) and a saved landscape interview (automatic speaker crop). Both produced 72 frames; inspected output frames show a clear original background and no added black padding or blur.
- New export cache identifier ensures opening a clip renders updated framing instead of reusing an old export. Existing files are retained.

Limitations: Detection uses sampled faces, not full scene understanding. It can miss a brief movement or meaningful object outside the crop. Group scenes and uncertain detections retain blur; manual layouts remain available. Existing blur or black bars already baked into a source are not removed automatically.
