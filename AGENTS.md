# Agent Video Gen Pack

Make videos with [Remotion](https://www.remotion.dev) (React → MP4) that have an AI voice-over and word-synced subtitles.
You are expected to run the whole pipeline yourself from a person's request: **script → voice-over → timings → Remotion composition → preview/render**.

## Pipeline

1. **Script.** Write the narration, split into scenes (1–3 sentences each). Keep a plain-text file per scene, e.g. `work/<video>/scene-01.txt`. Rules for good narration: see [docs/workflow.md](docs/workflow.md#writing-the-script).
2. **Voice-over.** `uv run scripts/tts.py --file work/<video>/scene-01.txt -o <remotion-project>/public/voiceover/scene-01.mp3`
   OpenRouter TTS, default model `google/gemini-3.8-flash-tts`, voice `Zephyr`. Add `-i "<how it should sound>"` for a voice style (sad, cheerful, announcer, …). Details: [docs/openrouter-tts.md](docs/openrouter-tts.md).
3. **Timings.** `uv run scripts/transcribe.py <...>/scene-01.mp3 -o <...>/scene-01.json`
   Local Parakeet TDT 0.6B v3 → per-word and per-token start/end times plus Remotion `Caption[]`. Details: [docs/timestamps.md](docs/timestamps.md).
4. **Video.** Create or reuse a Remotion project (`npx create-video@latest`, see [docs/remotion-setup.md](docs/remotion-setup.md)), build compositions following the installed `remotion-*` skills, size each scene from its audio length, drive subtitles/animation from the timings. Example: [docs/workflow.md](docs/workflow.md#building-the-composition).
5. **Preview first, render on request.** Start Remotion Studio and let the person look; render to `out/` only when asked (`remotion-render` skill).

## Setup (once per machine)

```bash
cp .env.example .env          # then put OPENROUTER_API_KEY into .env  (never commit it, never print it)
uv run scripts/download_model.py   # ~2.4 GB, optional: otherwise fetched on the first transcribe
```

Requires: `uv`, Node.js 18+ (`npx`), `ffmpeg`/`ffprobe` on PATH. Python deps are declared inline in each script; `uv run` installs them.

## Skills (`.agents/skills/`, symlinked into `.claude/skills/`)

| Skill | Use it for |
| --- | --- |
| `remotion-best-practices` | Router; load first when the task is "make a video" |
| `remotion-create` | New project / composition |
| `remotion-markup` | Writing compositions: animation, layout, fonts, audio, transitions, timing, `voiceover.md` |
| `remotion-captions` | Showing subtitles (`Caption` type, Basic Captions element) |
| `remotion-studio`, `remotion-render` | Preview, render to file |
| `remotion-docs`, `remotion-multimedia`, `remotion-maps`, `remotion-interactivity`, `remotion-saas`, `remotion-upgrade` | As their names say |
| `voiceover-tts` | **This repo.** Generate speech through OpenRouter |
| `speech-timestamps` | **This repo.** Word/token timings from audio, local |

Remotion skills are third-party and pinned in `skills-lock.json`. Update with `npx remotion skills update` (inside a Remotion project) or re-run `npx skills@1.7.0 add remotion-dev/skills --yes` here.

## Conventions and gotchas

- **TTS provider override.** `remotion-markup/voiceover.md` defaults to ElevenLabs. In this repo use `scripts/tts.py` (OpenRouter) instead; keep that guide's `calculateMetadata` and `<Audio>` advice.
- **Audio goes in the Remotion project's `public/`** (e.g. `public/voiceover/scene-01.mp3`) and is referenced with `staticFile()`. Use **mp3**; `pcm` has no documented sample rate.
- **One audio file per scene** is the default: the scene's length is its audio duration plus padding, and each timings JSON is relative to that scene's own start, so it can be dropped inside a `<Sequence>` unchanged.
- **Word times are start-accurate to ±0.08 s**; ends are derived (next start, capped at 0.4 s). Don't treat `end` as a measured silence boundary.
- **Subtitles:** `remotion-captions` wants captions inlined in the `captions` prop of `<BasicCaptions>`; paste the `captions` array from the timings JSON.
- **Secrets:** `OPENROUTER_API_KEY` lives in `.env` or the environment only. Don't echo it, log it, or write it into any file other than `.env`.
- **Generated artifacts** (`.cache/`, `out/`, `*.pcm`, `.env`) are git-ignored.
- **Language:** Parakeet v3 auto-detects 25 European languages (including English and Russian). Gemini TTS follows the language of the input text.
