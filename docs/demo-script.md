# Boot Order Atlas — actual local demo narration

A **151.6-second edited CLI walkthrough** was rendered locally on 2026-11-09. It uses actual Linux-host command outputs and selected fields from generated reports, displayed as original text cards. English generic synthetic narration and 28 burned-in caption blocks accompany the walkthrough. This is edited evidence, with the displayed commands retained; it is not an uninterrupted terminal screen recording.

The MP4 is H.264/AAC, 1920×1080 at 5 fps, **6,129,190 bytes**. SHA-256: `038c9f53408f4dd1766c82b199012b3b76bf393dd335dd4b03705b24fc524b1c`. [Machine-readable local-media record](local-demo-20261109.json). It was [published publicly on YouTube](https://youtu.be/K55o50_Tus4) on 2026-11-10. Anonymous playback has not been independently verified, and no official submission receipt is recorded here.

## Recorded sequence

| Time | Actual content |
| --- | --- |
| 00:00.0–00:16.8 | Review startup assumptions before the first boot |
| 00:16.8–00:36.2 | Source plus an explicit contract |
| 00:36.2–00:53.0 | Earlier launch does not prove readiness |
| 00:53.0–01:12.2 | Compare the changed events and assumptions |
| 01:12.2–01:29.0 | A cycle in declarations, not a measured deadlock |
| 01:29.0–01:50.6 | Unknown syntax stays visible |
| 01:50.6–02:12.6 | Reproducible host outputs |
| 02:12.6–02:31.6 | Runnable source. Explicit limits. |

## English narration

**1. Review startup assumptions before the first boot**

This is Boot Order Atlas, a working Python command line tool for reviewing QNX eight startup scripts on a Linux host. This edited walkthrough uses actual command outputs. It does not show QNX or emulator execution.

**2. Source plus an explicit contract**

The input is an inline QNX startup script plus a separate resource contract. These workshop programs are fictional examples. The operator declares each service's expected paths and foreground return behavior. The tool never guesses a driver's resources.

**3. Earlier launch does not prove readiness**

In the first version, the panel starts after its producers, but before matching path waits. The actual analysis reports two unguarded dependencies and links each one to its source line. Launching a producer does not prove readiness.

**4. Compare the changed events and assumptions**

The revised version adds two waitfor commands before the panel. The comparison shows the added events and warnings that are no longer reported. Each dependency is now conditional on a stat check. The report still does not prove the wait succeeded or the service stayed healthy.

**5. A cycle in declarations, not a measured deadlock**

This second input declares a circular dependency. Atlas reports that the before launch assumptions conflict and also identifies a producer that has not started. This is a contract finding, not a measured operating system deadlock.

**6. Unknown syntax stays visible**

Coverage boundaries remain visible. An external waitfor is not silently treated as the internal command. Unsupported arguments, an explicit shell and an external startup file require review. Unknown syntax is not declared invalid QNX syntax, and source commands are never executed.

**7. Reproducible host outputs**

The host smoke check regenerates the comparison and verifies its artifacts. Identical inputs produce identical JSON and a single offline HTML report. Source and contract fingerprints make the assumptions auditable. The repository includes focused regression tests for the supported boundaries.

**8. Runnable source. Explicit limits.**

The public repository contains the runnable tool, fixtures, documentation and an M I T license. This local video is an edited command line walkthrough. No QNX SDK build, hardware validation or official competition submission is claimed.

## Actual commands captured

All ran from the repository root. The fixture services are fictional; these commands analyze text and do not execute them. Full local capture stdout/stderr is retained with the media. Selected JSON fields in the video are formatted for readability, with source line references preserved.

```sh
python3 -m boot_order_atlas analyze examples/serial-before.build --contract examples/serial-contract.json --json output/video-before.json --html output/video-before.html
python3 -m boot_order_atlas compare examples/serial-before.build examples/serial-after.build --contract examples/serial-contract.json --json output/video-comparison.json --html output/video-comparison.html
python3 -m boot_order_atlas analyze examples/cycle.build --contract examples/cycle-contract.json --json output/video-cycle.json
python3 -m boot_order_atlas analyze examples/boundaries.build --contract examples/empty-contract.json --json output/video-boundaries.json
python3 scripts/check.py
git rev-parse HEAD
```

## Validation and next step

`ffprobe` confirmed the duration, codecs and dimensions. A single-thread video/audio decode completed without error; eight actual decoded scene frames were inspected, including the detailed comparison frame. Caption offsets use real decoded PCM sample counts plus frame-aligned padding. The original narration is generic `en-US-AriaNeural`, synthesized through the Microsoft Edge online service using `edge-tts 7.3.1`; it is not a local model or an imitation of an identified person. No paid API was used.

The media documents actual host-tool functionality. It establishes no QNX SDK build, emulator run, hardware validation, successful boot, runtime readiness or organizer acceptance. Code correctness remains bounded by the tool’s documented review model. An extra attempt to capture the complete test suite hit a 60-second harness limit and is not presented as a pass; the video instead shows the successful artifact smoke check. Earlier committed local test evidence is separate.

The [official rules](https://qnx.devpost.com/rules) require a public YouTube demonstration shorter than three minutes. The prepared video was [published publicly](https://youtu.be/K55o50_Tus4) on 2026-11-10, and its URL can be added to the final entry. Rendering the local file on November 9 did not perform an upload, new account action or official submission. The later publication does not confirm QNX event registration or final submission. On November 10, official registration was confirmed by "Thanks for registering!" and My hackathon projects showing 0. Project creation is in progress; no new project creation or final submission is confirmed.
