# ffmpeg

`ffmpeg` and `ffprobe` must be on `PATH`. Every workflow needs them: `scripts/transcribe.py` decodes its input with ffmpeg, `scripts/tts.py` reports the result's length with ffprobe when it is there, and [clipping an existing video](workflows/clip-existing-video.md) is done with ffmpeg directly. There is no wrapper script for cutting: run the commands below and adapt them.

## Install and check

| OS | Command |
| --- | --- |
| macOS | `brew install ffmpeg` |
| Debian / Ubuntu | `sudo apt install ffmpeg` |
| Windows | `winget install Gyan.FFmpeg` (then reopen the terminal) |

```bash
ffmpeg -version && ffprobe -version     # both must print a version
```

If it is missing, ask the person to install it (the install may need their password) rather than working around it. `npx remotion ffmpeg` exists inside a Remotion project, but the scripts here call the system binary and Remotion's build carries only the codecs Remotion itself needs.

## Recipes

Look at a file before cutting it: resolution decides the composition size, and `avg_frame_rate` differing from `r_frame_rate` means variable frame rate.

```bash
ffprobe -v error -show_entries format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate -of json source.mp4
```

Cut a clip, `-ss` (start) and `-to` (end) in source time, as seconds or `HH:MM:SS.ms`:

```bash
ffmpeg -nostdin -y -loglevel error -ss 75.05 -to 98.6 -i talk.mp4 \
  -map 0:v:0 -map "0:a:0?" -vf fps=30 \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart \
  videos/my-video/public/clips/clip-01.mp4
```

Each part is there for a reason:

- `-ss`/`-to` **before** `-i`, with a re-encode: the cut lands on the exact frame.
- `-vf fps=30`: constant frame rate at the composition's fps, for a clip that goes into Remotion. For a standalone file leave it out and the source frame rate is kept; for a variable-frame-rate source keep it, set to the source's nominal rate. Add `scale=-2:1080` (after a comma, or as the whole `-vf`) to downscale a 4K or Retina source.
- `libx264` + `yuv420p` + `aac` + `+faststart`: an mp4 that Remotion and browsers play and seek reliably.
- `-map "0:a:0?"`: first audio track, and no error when the source has none.
- `-nostdin`: ffmpeg never waits for keyboard input, which would hang an agent's shell.

Then confirm the result: `ffprobe -v error -show_entries format=duration -of csv=p=0 videos/my-video/public/clips/clip-01.mp4` should print `end − start`.

Find pauses, as candidate cut points or dead air to remove:

```bash
ffmpeg -nostdin -hide_banner -i source.mp4 -vn -af silencedetect=noise=-35dB:d=0.6 -f null - 2>&1 | grep silence_
```

Grab a frame to see what is on screen at a moment (read the PNG to check framing, faces, on-screen text):

```bash
ffmpeg -nostdin -y -loglevel error -ss 80 -i source.mp4 -frames:v 1 work/talk/at-80s.png
```

See a whole video at a glance, for footage without speech: a contact sheet with one frame every 5 s, twelve per image (change `fps=1/5` and `tile=4x3` to the length; frame *n* of the sheet is at *n* × 5 s):

```bash
ffmpeg -nostdin -y -loglevel error -i source.mp4 -vf "fps=1/5,scale=320:-2,tile=4x3" -frames:v 1 -update 1 work/demo/sheet.png
```

List the times where the picture changes sharply (cuts, screen changes); raise or lower `0.3` for fewer or more:

```bash
ffmpeg -nostdin -hide_banner -i source.mp4 -an -vf "select='gt(scene,0.3)',showinfo" -f null - 2>&1 | grep -o "pts_time:[0-9.]*"
```

Even out loudness of a quiet recording (`-ar 48000` matters: `loudnorm` upsamples internally):

```bash
ffmpeg -nostdin -y -loglevel error -i clip.mp4 -c:v copy -af loudnorm=I=-16:TP=-1.5:LRA=11 -ar 48000 -c:a aac -b:a 192k clip-loud.mp4
```

## Gotchas

- **`-c copy` cuts are inexact.** A stream copy can only start on a keyframe: the clip starts seconds early or opens on frozen frames. Re-encode (as the cut recipe does) whenever the cut point matters.
- **Text and effects belong in Remotion, not in ffmpeg filters.** ffmpeg's `subtitles`, `ass` and `drawtext` filters exist only in builds with libass/freetype, and the default Homebrew build has none of them. Use ffmpeg to cut and measure; draw captions, titles and effects in the composition.
- **Variable frame rate** (phones, screen recorders, Zoom) drifts against Remotion's frame-based timing. The cut recipe's output is constant frame rate; a source dropped into `public/` untouched is not.
