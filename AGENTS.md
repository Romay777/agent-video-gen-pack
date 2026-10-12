# Agent Video Gen Pack

A toolkit for making videos with [Remotion](https://www.remotion.dev) (React → MP4). You run the whole job yourself from a person's request.

This file is a reference, and the building blocks below (voice-over, timings, cutting, composition) are independent: use the ones the request needs, in whatever order and combination fits it. Every part is optional, subtitles included: a video can have a voice-over and no subtitles, footage with only a title, motion graphics with no speech at all. What the video contains and how it looks is your call and the person's.

## Two example routes

Two common kinds of request and one way through each. They are examples to orient you; any other route built from the same blocks is equally valid.

| The request | One way to do it |
| --- | --- |
| A video from an idea or text (motion graphics with a voice-over) | Write the narration per scene → [voice-over](#voice-over) → [timings](#timings-speech--word-times) → [composition](#composition) |
| Footage that already has speech, to cut into clips with overlays | [Timings](#timings-speech--word-times) of the whole source → pick moments → [cut](#cutting-existing-footage) → timings of each clip → [composition](#composition) |

`docs/workflows/` holds these two routes written out end to end, with checks and troubleshooting: [narrated-video.md](docs/workflows/narrated-video.md), [clip-existing-video.md](docs/workflows/clip-existing-video.md). Read one when your task resembles it and you want to see how the pieces connect or why something failed; skip, reorder or replace its steps freely.

## Where things live and run

- **`videos/<name>/`** — one Remotion project per video (git-ignored). Media the composition plays goes in its `public/`: `public/voiceover/scene-01.{mp3,json}`, `public/clips/clip-01.{mp4,json}`, plus images, logos and music.
- **`videos/<name>/NOTES.md`** — the video's memory, written by you and kept current: what was asked, size and fps, the exact voice settings (`--voice`, `--model`, the `-i` text), where the source footage and scene texts are, decisions made with the person. Read it first when returning to a video: a re-take needs the same voice and instruction as the other scenes.
- **`work/<name>/`** — inputs and intermediates (git-ignored): scene texts, picks, a link to the source footage. Source footage is read in place or symlinked here, and stays unmodified.
- **`out/`** — standalone results (git-ignored); a project renders to its own `out/`.
- `uv run scripts/…` runs from the repo root; `npx remotion …` and `npx tsc` run inside the project folder.
- Material the video needs and nobody supplied (a logo, music, product shots): ask the person for it.

## Remotion project

Needed when something is drawn or assembled: graphics, overlays, subtitles, several clips in one video. A plain cut of footage is ffmpeg alone.

```bash
mkdir -p videos && (cd videos && npx create-video@latest --yes --blank --no-tailwind my-video)
(cd videos/my-video && npx remotion add @remotion/media)        # <Audio>, <Video>; add @remotion/captions for subtitles
```

`create-video` refuses a folder that already has files, and the scripts create missing output folders, so scaffold the project before generating media into it.

How to write compositions is the job of the `remotion-best-practices` skill: load it before writing Remotion code. It is third-party; [where this repo differs from it](#differences-from-the-remotion-skill) is listed below.

## Voice-over

```bash
uv run scripts/tts.py --file work/demo/scene-01.txt -o videos/my-video/public/voiceover/scene-01.mp3 --voice Zephyr -i "<how the voice should sound>"
```

- OpenRouter TTS, model `google/gemini-3.8-flash-tts`. Needs `OPENROUTER_API_KEY` in `.env`; when it is missing, ask the person for it.
- `--voice`: default `Zephyr` (female); e.g. `Kore`, `Leda` (female), `Puck`, `Charon` (male). All 30 with gender: skill `voiceover-tts`.
- `-i` sets how the voice speaks (mood, pace, persona), written as full sentences. A different instruction changes the voice's character, so scenes of one video usually share one; record it in `NOTES.md`.
- The script prints the take's `duration`. Speech runs at roughly 150 words per minute, and the real length is known only after generating: for a fixed total length, write to that budget, add up the durations, then adjust the text.
- The model reads text literally: spell numbers, units and acronyms the way they should sound. The language follows the text.
- Splitting the narration into one text file and one mp3 per scene lets a single line be re-taken and gives each scene its own length; one file for the whole narration works too.
- A re-take replaces the file only when it succeeds. Copy the old take aside first if the person may want it back.
- Details, errors: [docs/openrouter-tts.md](docs/openrouter-tts.md).

## Timings (speech → word times)

```bash
uv run scripts/transcribe.py videos/my-video/public/voiceover/scene-01.mp3 -o videos/my-video/public/voiceover/scene-01.json
```

- Local Parakeet TDT 0.6B v3; takes audio or video. This is the only transcription path in this repo.
- What it is for: subtitles, syncing visuals to words, choosing cut points by what is said, and checking a generated voice-over. You cannot hear the audio, so comparing `text` with the script is the one check that the voice said what was written; words with `confidence` below ~0.7 deserve a look.
- When a video needs none of that, skip it. Duration alone: `ffprobe -v error -show_entries format=duration -of csv=p=0 <file>`.
- The JSON has `duration`, `text`, `words` and `tokens` (`{text, start, end, confidence}`, seconds), `sentences`, and `captions` (Remotion `Caption[]`).
- Times are relative to the transcribed file. After a re-take or re-cut, transcribe that file again, and update anything copied from the old JSON (inline captions, hand-written durations).
- Word **starts** are measured (±0.08 s); `end` is derived (next start, capped at 0.4 s), so sync and cut on starts.
- Footage without speech gives `error: no speech recognized` and no JSON; a file without an audio track fails earlier.
- The first run downloads ~2.4 GB, and a long source takes about a tenth of its length: run those in the background.
- Format, limits, languages: [docs/timestamps.md](docs/timestamps.md).

## Cutting existing footage

```bash
# a clip for a Remotion project: constant frame rate at the composition's fps
ffmpeg -nostdin -y -loglevel error -ss 75.05 -to 98.6 -i talk.mp4 -map 0:v:0 -map "0:a:0?" -vf fps=30 \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart videos/my-video/public/clips/clip-01.mp4
# a standalone file: the same without -vf fps=30 (keeps the source frame rate), written to out/
```

- Run ffmpeg yourself. `-ss`/`-to` are source times, in seconds or `HH:MM:SS.ms`. Always re-encode like this: a `-c copy` cut lands on a keyframe, seconds off.
- Look before cutting: `ffprobe -v error -show_entries format=duration:stream=codec_type,width,height,r_frame_rate,avg_frame_rate -of json <file>`. `avg_frame_rate` differing from `r_frame_rate` means variable frame rate (phones, screen recorders), which drifts in Remotion until re-encoded with `-vf fps=…`.
- Choosing moments by what is said: transcribe the whole source and read its `sentences` (e.g. `jq -r '.sentences[] | "\(.start)\t\(.text)"' source.json`).
- Choosing moments by what is shown (no speech, screen recordings): a contact sheet and scene-change times, recipes in [docs/ffmpeg.md](docs/ffmpeg.md#recipes); read the image.
- Boundaries that follow speech, as a starting point: `start` = first word − 0.15 s; `end` = the earlier of the next sentence's first word and the last word's `end` + 0.3 s.
- To verify a speech cut, transcribe the clip: its `text` should open and close on the intended words.
- Flags explained, pauses, frame grabs, loudness: [docs/ffmpeg.md](docs/ffmpeg.md).

## Composition

- **Timings are relative to their media file**, so a `<Series.Sequence>` holding one `<Audio>`/`<Video>` (from `@remotion/media`, file via `staticFile()`) and everything synced to it needs no offsets.
- **Length from media**: a video clip is `Math.floor(duration * fps)` frames (stays inside the file); a voice-over line is `Math.ceil((duration + pause) * fps)` with whatever pause you want after it (the example uses 0.6 s). `duration` comes from the timings JSON, `tts.py`'s output or `ffprobe`.
- **Length fixed in advance** (a 20-second ad): set `durationInFrames` yourself and fit the content to it. One voice-over across many clips is an `<Audio>` at composition level, outside the clip sequences.
- **Footage audio**: `<Video>` plays its own sound; `volume` lowers it (under music or a voice-over), `muted` silences it.
- **Subtitles**, when the video has them: ready elements at https://www.remotion.dev/elements/captions — `basic-captions` (a few words at a time, plain white on a grey box), `word-highlight-captions` (highlights the word being spoken), `popping-word-captions`, `rounded-captions`, `moving-pill-captions`. Copy an element's source from `<its url>.md` into `src/`; each takes the JSON's `captions` array. In a component of your own, keep a word active until the next word's start rather than its own `end`.
- **Sync to speech**: frame = `Math.round(word.start * fps)`.
- **Size** is set on the composition, e.g. 1920×1080 horizontal or 1080×1920 vertical. Two ways to fit horizontal footage into a vertical frame: `objectFit="cover"` crops the sides (a still shows what is lost); `objectFit="contain"` over a blurred, muted copy of the same video keeps the whole picture.
- **Several output videos are several compositions**, one per video, rendered to separate files. Clips go back to back in one composition when they form a single video.
- Type-checked references: [docs/examples/Narrated.tsx](docs/examples/Narrated.tsx) + [Root.tsx](docs/examples/Root.tsx) (voice-over scenes sized from their JSON), [docs/examples/Clips.tsx](docs/examples/Clips.tsx) (footage with captions, a title, a progress bar).

## Preview and render

Run `npx remotion studio` in the background and let the person look. Render to `out/` only when they ask for the file. Before handing over: `npx tsc` passes, and a still (`npx remotion still <Id> out/check.png --frame=<n>`) shows what you intended. After a render, `ffprobe -v error -show_entries stream=codec_type -of csv=p=0 <file>` should list `video` and, when there is sound, `audio`.

## Differences from the Remotion skill

`remotion-best-practices` is written for a generic Remotion project that a person edits in Studio. Where it disagrees with this file, this file wins:

| Topic | The skill says | Here |
| --- | --- | --- |
| Transcription | `remotion-captions/transcribe-captions.md`: Whisper WebGPU via `@remotion/whisper-webgpu` | `scripts/transcribe.py` (Parakeet). Its `captions` output is already the `Caption[]` the skill expects |
| Voice-over | `remotion-markup/voiceover.md`: ElevenLabs; duration via `getAudioDuration` | `scripts/tts.py` (OpenRouter), mp3; duration from the timings JSON or `tts.py`'s output |
| Trimming footage | `remotion-markup/ffmpeg.md`: prefer `trimBefore` on the full source | A source longer than a few minutes, or with variable frame rate, is cut with ffmpeg first. `trimBefore`/`durationInFrames` suit short constant-frame-rate files and nudging a cut by a few frames |
| ffmpeg | Not needed, use `npx remotion ffmpeg` | System `ffmpeg`/`ffprobe` are required; the scripts call them |
| Captions data | Always an inline array literal on the captions element | Inline when the person will edit captions in Studio. Imported from the JSON otherwise, which follows a re-take by itself |
| Studio-editable structure | Always: one hand-written JSX node per scene, no `.map()`, inline literals, no `FPS` constant | For videos the person will keep editing in Studio (`Clips.tsx` is written this way). Data-driven markup (`.map()` over the timings JSON, as in `Narrated.tsx`) when lengths should follow re-takes automatically |
| When to open Studio | Right after scaffolding, before writing the composition | Whenever there is something to look at |

## Setup (once per machine)

Requires `uv`, Node.js 18+ (`npx`), and **`ffmpeg` + `ffprobe` on PATH** (check: `ffmpeg -version`). When ffmpeg is missing, ask the person to install it: `brew install ffmpeg` / `sudo apt install ffmpeg` / `winget install Gyan.FFmpeg`. `jq` is optional, for reading timings.

```bash
cp .env.example .env               # then put OPENROUTER_API_KEY into .env (voice-over only)
uv run scripts/download_model.py   # optional: pre-fetch the speech model instead of on the first transcribe
```

## Skills and conventions

- **Skills** (`.agents/skills/`, symlinked into `.claude/skills/`): `remotion-best-practices` is third-party and holds everything about Remotion in subfolders (`remotion-markup/`, `remotion-captions/`, `remotion-create/`, `remotion-studio/`, `remotion-render/`, …), each with a `REFERENCE.md`. This repo's own `voiceover-tts`, `speech-timestamps` and `video-clipping` add detail to the sections above.
- **ffmpeg cuts and measures; Remotion draws.** Captions, titles and effects go in the composition: common ffmpeg builds lack the `subtitles`/`drawtext` filters.
- **Secrets.** `OPENROUTER_API_KEY` lives in `.env` or the environment only: keep it out of output, logs and every other file.
- **Languages.** Parakeet v3 auto-detects 25 European languages; other languages give unusable timings, so tell the person.
