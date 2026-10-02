# v3.5 validation

- 63 regression tests pass, including single-person crop safety, group/action/movement fallbacks, and absence of a black-padding filter in blurred portrait layouts. The protected interview boundary tests remain passing.
- Real portrait test exports decoded successfully at 720×1280. Sampled frames of a tight speaker crop and a full-picture blurred background were visually inspected. Upper and lower regions contain image content rather than generated black padding.
- The full 29-second Nico interview produced 16 single-face detections across 16 samples. It selected a wider person-focused foreground over blurred video because a tighter fixed crop would risk cutting off movement.

Limitations: sampled frames can miss brief movement or camera cuts. Face detection is not speaker identification. Fixed crops do not track a moving subject. Already-black regions inside a source remain part of the source image. No broader accuracy or retention claim is made.

The full 29.06-second Nico export was rendered with the person-focused blur layout, titles, captions and audio; the preview was inspected and video decoding passed. Streamlit editor, automatic-layout application, and v3.5 report checks passed without exceptions. The server was restarted successfully.
