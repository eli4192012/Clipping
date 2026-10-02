# v3.3 validation

- 53 automated tests pass, including multipart-question/follow-up grouping, declarative next-topic boundaries, strict quality rejection, coverage controls, adjacent non-overlapping topics, and literal caption text with clip-relative timing.
- Real Higher quality run on the 185.53-second Colts press conference: 8 proposals, 5 kept. Nico Collins 101.18–130.24; must-wins 80.84–101.10; Slayton 45.52–80.76; C.J. Allen 16.80–45.44; Mooney 5.44–15.70. Two additional passing discussions were excluded by the five-clip limit; one incomplete-context draft was rejected.
- Compared with the previous results, C.J. Allen is recovered, Slayton includes the explanation and follow-ups, Mooney includes the named question, and the must-win cut no longer contains the Nico introduction.
- Four real 4-second exports decoded successfully: original 1280×720 and all three portrait layouts 720×1280. Burned word highlighting and title placement were inspected in sampled frames. These short export tests test rendering, not conversational completeness.
- Streamlit settings and editor loaded without exceptions; applying a speaker-crop style saved and rendered without exceptions, and the v3.3 release report opened without exceptions. Server health endpoint returned ok.

Limitations: this validates one real interview plus regression fixtures, not universal clipping quality. Transcript errors remain possible. Topic and completeness decisions need human review. The two-speaker layout uses fixed crops of a source showing both people, not speaker tracking. Full-game sports recognition was not revalidated for this release; existing sports processing is preserved. Podcast topic proposals use a local-model window scan; broad podcast quality evaluation is still needed. No retention improvement is claimed.

A full 35.24-second Slayton clip was exported with centered portrait crop, title, highlighted captions, and audio; all video frames decoded successfully.
