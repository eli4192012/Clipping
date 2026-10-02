## Local checks — September 27, 2026

- 31 regression tests pass, including separate caches for model choices, word-to-speaker assignment, and conservative scene-boundary handling.
- The v2.1 button opens the report in the live browser. Settings, the completion screen, and the clip collection passed Streamlit UI tests.
- Whisper Turbo transcribed the synthetic sample locally (91 words).
- On the saved 25.32-second Buckner interview, Balanced took 4.6 seconds and Higher quality took 18.6 seconds. Both produced 104 words; Turbo separated “against Kansas City” from the following tackle statistics more cleanly. This is one sample, not a measured general accuracy improvement.
- The 4B text reviewer kept the established 143.54–168.86-second Buckner exchange and approved its transcript. It did not demonstrate better boundaries than the previous reviewer on this example.
- PySceneDetect found 137 shot boundaries in the saved full interview. Finding cuts is not proof of complete sports plays.
- Full higher-quality integration passed on a 100-second interview excerpt: approximately 94 seconds for analysis, one non-overlapping suggestion, and an MP4 export that decoded successfully.
- The 4B sports model ran locally on 24 frames from the reported touchdown. It missed the pre-snap setup, so this remains an uncertain draft, not an approved complete play. A regression check prevents an earlier play from being substituted for the event.
- A fresh YouTube download succeeded with stdout and stderr deliberately connected to closed pipes, verifying the broken-pipe import fix.
- WhisperX English alignment passed offline on the saved interview: 104 words retained, about 31.7 seconds.
- The uncertain sports draft spans 179.5–195.5 seconds on the test source and includes the event timestamp. This does not establish reliable complete-play recognition.
- Speaker detection is integrated but disabled and unvalidated until its gated model is downloaded.
- Both Python environments pass dependency checks. The local server health endpoint responds successfully.
