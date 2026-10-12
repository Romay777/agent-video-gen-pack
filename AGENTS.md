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

## Remotion project

Needed when something is drawn or assembled: graphics, overlays, subtitles, several clips in one video. A plain cut of footage is ffmpeg alone. When there is a project, create it before generating media, in a subfolder, so files go straight into its `public/`:

```bash
npx create-video@latest --yes --blank --no-tailwind my-video && cd my-video && npm i
npx remotion add @remotion/media @remotion/captions   # captions: only for subtitles
```

How to write compositions is the job of the `remotion-best-practices` skill: load it before writing Remotion code. It is third-party; [where this repo overrides it](#overrides-of-the-remotion-skill) is listed below.

## Voice-over

```bash
uv run scripts/tts.py --file work/<video>/scene-01.txt -o my-video/public/voiceover/scene-01.mp3 -i "Calm, warm, unhurried."
```

- OpenRouter TTS, model `google/gemini-3.8-flash-tts`. Needs `OPENROUTER_API_KEY` in `.env`; when it is missing, ask the person for it.
- Splitting the narration into one text file and one mp3 per scene lets a single line be re-taken and gives each scene its own length; one file for the whole narration works too.
- `--voice`: default `Zephyr`. Female: Zephyr, Kore, Leda, Aoede, Callirrhoe, Autonoe, Despina, Erinome, Laomedeia, Achernar, Gacrux, Pulcherrima, Vindemiatrix, Sulafat. Male: Puck, Charon, Fenrir, Orus, Enceladus, Iapetus, Umbriel, Algieba, Algenib, Rasalgethi, Alnilam, Schedar, Achird, Zubenelgenubi, Sadachbia, Sadaltager.
- `-i` sets how the voice speaks (mood, pace, persona), written as full sentences. A different instruction changes the voice's character, so reusing one instruction keeps a video consistent. The language follows the text.
- The model reads the text literally: spell numbers, units and acronyms the way they should sound. Speech runs at roughly 150 words per minute; the real length is known only after generating (`duration` in the timings JSON, or `ffprobe`).
- Details, errors: [docs/openrouter-tts.md](docs/openrouter-tts.md).

## Timings (speech → word times)

```bash
uv run scripts/transcribe.py my-video/public/voiceover/scene-01.mp3 -o my-video/public/voiceover/scene-01.json
```

- Local Parakeet TDT 0.6B v3; takes audio or video. This is the only transcription path in this repo.
- Needed for subtitles, for syncing visuals to words, and for choosing cut points by what is said. When a video needs none of these, skip it: `ffprobe` gives a file's duration.
- The JSON has `duration`, `text`, `words` and `tokens` (`{text, start, end, confidence}`, seconds), `sentences`, and `captions` (Remotion `Caption[]`).
- Times are relative to the transcribed file. After any re-take or re-cut, transcribe that file again.
- Word **starts** are measured (±0.08 s); `end` is derived (next start, capped at 0.4 s), so sync and cut on starts.
- Compare `text` with what was meant to be said; words with `confidence` below ~0.7 deserve a look.
- The first run downloads ~2.4 GB. A long source takes about a tenth of its length: run it in the background.
- Format, limits, languages: [docs/timestamps.md](docs/timestamps.md).

## Cutting existing footage

```bash
ffmpeg -y -loglevel error -ss 75.05 -to 98.6 -i work/<video>/source.mp4 -map 0:v:0 -map "0:a:0?" -vf fps=30 \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart my-video/public/clips/clip-01.mp4
```

- Run ffmpeg yourself; `-ss`/`-to` are source times, `fps` is the composition's. Always re-encode like this: a `-c copy` cut lands on a keyframe, seconds off.
- The source stays in `work/<video>/`, unmodified (copy or symlink it there). Only the cut clips go into `public/clips/`.
- To pick moments by what is said, transcribe the whole source and read its `sentences` (e.g. `jq -r '.sentences[] | "\(.start)\t\(.text)"' source.json`).
- Boundaries that follow speech, as a starting point: `start` = first word − 0.15 s; `end` = start of the next sentence's first word.
- To verify a speech cut, transcribe the clip: its `text` should open and close on the intended words.
- Flags explained, probing, finding pauses, grabbing a frame: [docs/ffmpeg.md](docs/ffmpeg.md).

## Composition

- **Timings are relative to their media file**, so a `<Series.Sequence>` holding one `<Audio>`/`<Video>` (from `@remotion/media`, file via `staticFile()`) and everything synced to it needs no offsets. Sequence length from the media: `Math.floor(duration * fps)`, plus whatever pause you want after a voice-over line (the example uses 0.6 s).
- **Subtitles**, when the video has them: a ready element is `<BasicCaptions>`. Copy its source from https://www.remotion.dev/elements/captions/basic-captions.md into `src/basic-captions.tsx` and give it the JSON's `captions` array: imported from the JSON, or pasted inline into the `captions` prop when the person wants to edit captions in Studio. It shows a few words at a time as plain white text on a grey box (Arial, 64 px); for another look or a highlighted current word, write your own component over `words`.
- **Sync to speech**: frame = `Math.round(word.start * fps)`.
- **Size** is set on the composition, e.g. 1920×1080 horizontal or 1080×1920 vertical. Two ways to fit horizontal footage into a vertical frame: `objectFit="cover"` crops the sides (a still shows what is lost); `objectFit="contain"` over a blurred, muted copy of the same video keeps the whole picture.
- **Several output videos are several compositions**, one per video, rendered to separate files. Clips go back to back in one composition when they form a single video.
- Type-checked references: [docs/examples/Narrated.tsx](docs/examples/Narrated.tsx) + [Root.tsx](docs/examples/Root.tsx) (voice-over scenes), [docs/examples/Clips.tsx](docs/examples/Clips.tsx) (footage with captions, a title, a progress bar).

## Preview and render

Start `npx remotion studio` in the background and let the person look. Render to `out/` only when they ask for the file. Before handing over: `npx tsc` passes, and a still (`npx remotion still <Id> out/check.png --frame=<n>`) shows what you intended.

## Overrides of the Remotion skill

`remotion-best-practices` is written for a generic Remotion project. Where it disagrees with this file, this file wins:

| Topic | The skill says | Here |
| --- | --- | --- |
| Transcription | `remotion-captions/transcribe-captions.md`: Whisper WebGPU via `@remotion/whisper-webgpu` | `scripts/transcribe.py` (Parakeet). Its `captions` output is already the `Caption[]` the skill expects |
| Voice-over | `remotion-markup/voiceover.md`: ElevenLabs | `scripts/tts.py` (OpenRouter), mp3. Keep that guide's `calculateMetadata` and `<Audio>` advice |
| Trimming footage | `remotion-markup/ffmpeg.md`: prefer `trimBefore` on the full source | A long or variable-frame-rate source is cut with ffmpeg first. `trimBefore`/`durationInFrames` suit short constant-frame-rate files and nudging a cut by a few frames |
| ffmpeg | Not needed, use `npx remotion ffmpeg` | System `ffmpeg`/`ffprobe` are required; the scripts call them |

## Setup (once per machine)

Requires `uv`, Node.js 18+ (`npx`), and **`ffmpeg` + `ffprobe` on PATH** (check: `ffmpeg -version`). When ffmpeg is missing, ask the person to install it: `brew install ffmpeg` / `sudo apt install ffmpeg` / `winget install Gyan.FFmpeg`. `jq` is optional, for reading timings.

```bash
cp .env.example .env               # then put OPENROUTER_API_KEY into .env (voice-over only)
uv run scripts/download_model.py   # ~2.4 GB, optional: otherwise fetched on the first transcribe
```

## Skills (`.agents/skills/`, symlinked into `.claude/skills/`)

| Skill | Use it for |
| --- | --- |
| `remotion-best-practices` | Third-party, pinned in `skills-lock.json`. Everything about writing, previewing and rendering Remotion; a router whose parts (`remotion-markup/`, `remotion-captions/`, `remotion-create/`, `remotion-studio/`, `remotion-render/`, …) are subfolders with a `REFERENCE.md` |
| `voiceover-tts` | This repo. Voice-over through OpenRouter |
| `speech-timestamps` | This repo. Word/token timings, local |
| `video-clipping` | This repo. Picking and cutting moments from existing footage |

Update the Remotion skill: `npx skills@1.7.0 add remotion-dev/skills --skill remotion-best-practices --yes`.

## Conventions

- **Files.** Inputs and intermediates in `work/<video>/` (git-ignored): scene texts, source footage, picks. Media the composition plays in the project's `public/`: `public/voiceover/scene-01.{mp3,json}`, `public/clips/clip-01.{mp4,json}`.
- **ffmpeg cuts and measures; Remotion draws.** Captions, titles and effects go in the composition: common ffmpeg builds lack the `subtitles`/`drawtext` filters.
- **Secrets.** `OPENROUTER_API_KEY` lives in `.env` or the environment only: keep it out of output, logs and every other file.
- **Languages.** Parakeet v3 auto-detects 25 European languages; other languages give unusable timings, so tell the person.
