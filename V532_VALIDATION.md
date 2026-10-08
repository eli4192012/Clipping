# v5.32 validation · Optional closed-lid queue mode

Validated on October 7, 2026. The queue's clipping/analysis behavior, models, source videos and analysis-cache version remain unchanged. The release badge is v5.32.

## Implementation and sources

The optional queue-start flag uses [Amphetamine](https://apps.apple.com/us/app/amphetamine/id937984704), a free Mac App Store utility advertising closed-display operation and AppleScript support. The user installed version 5.3.2 (9416). Inspected the installed app's scripting dictionary with `sdef`; it documents session start/end, remaining seconds, closed-display enable/query, screen sleep and the first-use closed-display warning. Both the exact start script and status-query script compiled successfully with macOS `osacompile`. Compilation is not an activation or lid-closed hardware test.

The installed `caffeinate` manual distinguishes idle-sleep assertions from system-sleep assertions; the former alone does not establish closed-lid support. Apple's [pmset implementation](https://github.com/apple-oss-distributions/PowerManagement/blob/main/pmset/pmset.m) persists system power-setting writes, so this release uses the separate utility's supported API rather than installing a privileged Clipping sleep override. Clipping only reads `pmset -g batt`. The optional utility's [Power Protect documentation](https://github.com/x74353/Amphetamine-Power-Protect) describes additional setup for power-source changes; Clipping does not install this helper or its sudo configuration.

Each opt-in start elects the existing exclusive queue runner, launches an independent local session watcher, waits for confirmed API activation before claiming a video, and ends its session after finishing/pausing. The watcher also detects owner exit by PID, user ID and start time, rejecting zombies and reused PIDs. It checks the charger and the app's reported closed-display mode. Losing support pauses the remaining queue after the current video; successful media and waiting entries remain saved. Failed initial setup leaves all videos unclaimed.

Sessions allow display sleep and have a 24-hour fallback limit. Existing active sessions are rejected before starting. Amphetamine exposes no session identifier: cleanup checks the finite countdown to avoid ending indefinite, Trigger, expired or differently timed replacement sessions. This is a heuristic, not an ownership guarantee for a manually substituted session with a matching countdown. A dead/stale watcher reports an error; the queue pauses remaining items and the user can end the utility session manually. Clipping does not suppress screen locks, install privileged services, modify sudo permissions or write permanent power settings. Reopening the app automatically resumes normal queues; a new closed-lid start requires explicit opt-in.

## Automated validation

**402 tests passed in 30.516 seconds** in the existing pinned local Python environment. First-party Ruff and `git diff --check` passed. New cases cover normal session cleanup, unplug behavior, denied closed-display activation, avoiding existing/replaced sessions, owner exit, finite countdown bounds, dead/stale monitoring, stable process identity across CPU states, zombies, unsupported platforms, unavailable power checks, failure before claiming a video, pausing remaining work when support is lost, and Streamlit charger gating/opt-in propagation. Native OS mutations and AppleScript execution are mocked in the offline suite; real script syntax is independently compiled against the installed dictionary.

The original queue ordering, automatic exports, failure/retry recovery, native FFmpeg exports, source-change guards and local AI/editorial tests remain covered. No transcription/model dependencies changed or weights were downloaded.

## Live UI and preservation

The live v5.32 queue screen showed the optional closed-lid checkbox. With a saved video waiting and the option selected, the real power-source check displayed the charger instruction and disabled Start queue while the Mac was on battery. The queue remained disabled and no processing/session was started. The temporary waiting entry was removed after validation; the existing completed entries and project were retained. The four focused Streamlit queue tests also passed after the final wording changes.

A second audit against the 2,367-file v5.31 baseline found the same 2,361 unchanged files, no missing files, and exactly the six project/run/finished-clip metadata changes already documented for v5.31. This release introduced no additional changes to those existing files. The live queue test only changed queue database metadata; source videos, transcripts, analyses, existing exports, manual edits and model weights were preserved. Runtime data and screenshots remain ignored by Git.

## Runtime limits

The app is installed and the exact scripts compile. The Mac is currently running on battery with no external display. Amphetamine's one-time closed-display/Automation prompts and a plugged-in physical closed-lid trial still need completion. No actual closed-lid processing success, thermal behavior, battery operation or keep-awake activation is claimed by this validation. Keep the charger connected and use an open, ventilated surface. The user requested closed-lid operation; this release's queue mode supports charger-connected use only.
