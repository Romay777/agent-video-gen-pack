# Workflow: clips from an existing video (cut → timings → overlays in Remotion)

From "here is a recording, cut it" (shorts, highlights, an ad, a trimmed version) to clips with subtitles and effects on top. The speech is already in the footage, so there is no script and no TTS.

> This is one worked example of a route through the toolkit. Your task may need fewer steps, other steps or a different order: subtitles, titles and effects in particular are there only if the video calls for them.

```
source video → transcribe whole source → pick moments → cut clips (ffmpeg) → timings per clip → Remotion overlays → Studio preview → render (on request)
```

ffmpeg does the cutting and measuring; Remotion draws everything that goes on top. Install and recipes: [../ffmpeg.md](../ffmpeg.md). A plain cut with nothing on top is step 1 plus the ffmpeg command of step 4, with no Remotion project at all.

## 1. Take in the source

- Check `ffmpeg -version && ffprobe -version` first; without them stop and ask the person to install ffmpeg.
- The person supplies the file. Copy or symlink it to `work/<video>/source.<ext>` (`work/` is git-ignored) and leave it unmodified.
- Probe it (command in [../ffmpeg.md](../ffmpeg.md#recipes)) and note duration, resolution, frame rate, and that an audio stream exists. Resolution and orientation decide the framing in step 5.

## 2. Transcribe the whole source

For choosing moments by what is said. With timecodes from the person, go straight to step 4.

```bash
uv run scripts/transcribe.py work/talk/source.mp4 -o work/talk/source.json
jq -r '.sentences[] | "\(.start)\t\(.end)\t\(.text)"' work/talk/source.json    # the readable view (any JSON tool works)
```

`transcribe.py` reads video files directly and chunks anything over 20 s on pauses. Expect roughly a tenth of the source's length in processing time on an Apple-silicon CPU, so run a long source in the background. Read the `sentences` listing rather than the whole JSON: `tokens` makes it very large.

## 3. Pick the moments

What makes a good moment depends on the video. For speech that must stand on its own, that is usually a complete thought closing on a finished sentence.

Boundaries that follow speech come from **measured word starts**:

- `start` = start of the first word − 0.15 s.
- `end` = start of the first word of the *next* sentence. A word's own `end` is derived and capped at 0.4 s, so cutting on it clips the tail of a drawn-out word. When nothing follows, use the last word's `end` + 0.3 s.

This example records the picks in `work/<video>/clips.json` as `[{ "id": "clip-01", "start": 75.05, "end": 98.6, "why": "…" }]`: a list that is easy to show the person and to re-cut from.

## 4. Cut, then time each clip

Create the Remotion project first ([../remotion-setup.md](../remotion-setup.md)) so clips land in its `public/clips/`. Cut each pick with the command from [../ffmpeg.md](../ffmpeg.md#recipes) (it always re-encodes, at the composition's fps). For subtitles or word-synced effects, transcribe the result:

```bash
uv run scripts/transcribe.py my-video/public/clips/clip-01.mp4 -o my-video/public/clips/clip-01.json
```

Transcribing the cut file gives timings relative to that clip's own start, which is what Remotion needs. It also verifies a speech cut: the JSON `text` should start and end on the intended words, with the first word starting within ~0.3 s; otherwise move the boundary and cut again.

Cutting to files (rather than putting the whole source in `public/` and trimming in Remotion) keeps the project small and constant-frame-rate. Fine-tune by a few frames in Remotion afterwards with `trimBefore` / `durationInFrames`.

To drop a pause or a tangent from the middle of a moment, cut the parts on either side as two clips and place them back to back.

## 5. Build the composition

Follow the `remotion-best-practices` skill; its `remotion-markup/video-editing.md` and `remotion-captions/display-captions.md` define the structure. How this example connects the pieces:

1. **One `<Series.Sequence>` per clip**, written out as its own JSX node, holding that clip's `<Video>` (from `@remotion/media`) and every overlay synced to it. Trims go on the sequence, so video and captions move together.
2. **Length comes from the clip**: `durationInFrames = Math.floor(duration * fps)` from the clip's JSON, written as a number on the sequence; the composition's length is the sum. Flooring keeps the last frame inside the file.
   **Several output videos are several compositions**, one per video, each rendered to its own file; clips go back to back in one composition when they form a single video.
3. **The clip's own audio** plays through `<Video>`. `volume` lowers it (under music, say) and `muted` silences it (for a new voice-over).
4. **Captions**, if the video has them: paste the clip JSON's `captions` array inline into `<BasicCaptions captions={[...]}>`; inline is what lets the person edit them in Studio.
5. **Framing** a horizontal source in a vertical composition, two ways: `objectFit="cover"` crops the sides (a still shows what is lost), or the full frame sits over a blurred, muted copy of itself (what the example does).
6. **Sync effects to words** with `Math.round(word.start * fps)`, exactly as in the narrated workflow.

Overlays and where the technique is documented (files in `.agents/skills/remotion-best-practices/remotion-markup/` unless noted):

| Overlay | How |
| --- | --- |
| Subtitles | `<BasicCaptions>`; `../remotion-captions/display-captions.md` |
| Title, lower third, keyword pop-ups | `<Sequence from={wordFrame}>` with `spring()`; `text-highlights.md` |
| Punch-in zoom on a key phrase | `scale` on the `<Video>` wrapper driven by `interpolate()`; `cropping.md` |
| Progress bar | width from `frame / durationInFrames` |
| Transitions between clips | `<TransitionSeries>`; `transitions.md` |
| Color, blur, grain, light leaks | `effects.md`, `light-leaks.md` |
| Sound effects, background music | `sfx.md`, `audio.md` |

A type-checked reference of one video made of two clips, blurred-background vertical framing, captions, a title and a progress bar: [`../examples/Clips.tsx`](../examples/Clips.tsx). It expects `public/clips/clip-01.mp4`, `clip-02.mp4` and `src/basic-captions.tsx`, and was type-checked and rendered to stills against the stock `create-video --blank` template (Remotion 4.0.535).

## 6. Preview, then render

Start Studio in the background and let the person look; render only when they ask for the file. Before handing over:

- `npx tsc` passes.
- A still from the middle of each clip shows what you intended (framing, and captions matching the words if there are any): `npx remotion still Clips out/check.png --frame=<n>`.
- Composition length equals the sum of the clip lengths.
- After a render, `ffprobe -v error -show_entries stream=codec_type -of csv=p=0 out/clips.mp4` lists `video` and `audio`.

## Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `ffmpeg: command not found` | Install it: [../ffmpeg.md](../ffmpeg.md#install-and-check). |
| Clip starts mid-word or ends on a clipped word | Boundary was set from a derived `end`. Re-pick from word starts (step 3) and re-cut. |
| Captions drift from the speech | The clip was re-cut without re-transcribing, or the trim sits on `<Video>` instead of the shared sequence. |
| `No filter named subtitles` / `drawtext` | The ffmpeg build lacks them. Draw text in Remotion. |
| Wrong or missing words in a noisy recording | Compare low-`confidence` words with the audio and correct the inline `captions` text by hand; timings stay. |
| Language is not one of Parakeet's 25 European ones | Timings will be unusable; tell the person. See [../timestamps.md](../timestamps.md). |
