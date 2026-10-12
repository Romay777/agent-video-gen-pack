---
name: video-clipping
description: Cut clips out of an existing video (talk, podcast, stream, screen recording, raw footage), optionally with subtitles and effects on top in Remotion. Use when given footage to cut into clips, highlights or a trimmed version, or when a clip boundary needs moving.
---

# Clips from an existing video

Needs `ffmpeg` and `ffprobe` on PATH: check with `ffmpeg -version`; if missing, ask the person to install it. The commands are in `AGENTS.md` → "Cutting existing footage" and "Timings". What follows is what tends to matter; take the parts your task needs.

- **A plain cut is ffmpeg alone.** Remotion comes in when something is drawn over the footage or clips are assembled into one video.
- **Probe the source first** (duration, resolution, frame rate, audio present); keep it unmodified in `work/<video>/`.
- **Choosing moments by what is said**: transcribe the whole source once (in the background when it is long) and read its `sentences`. With timecodes from the person this is unnecessary.
- **Boundaries that follow speech** sit on word starts: `start` = first word's start − 0.15 s; `end` = start of the next sentence's first word. A word's `end` is derived, so it is a poor cut point.
- **Verifying a speech cut**: transcribe the clip; its `text` should open and close on the intended words. Re-cutting means re-transcribing, since timings are relative to the clip file.
- **In Remotion**, a clip's `<Video>` and whatever is synced to it (captions, titles, effects) share one `<Series.Sequence>`; each output video is its own composition.

## More

- A full worked example with an overlay table, checks and troubleshooting: `docs/workflows/clip-existing-video.md`
- Working composition: `docs/examples/Clips.tsx`
- ffmpeg flags and recipes (probe, pauses, frame grab): `docs/ffmpeg.md`
