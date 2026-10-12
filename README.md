# Agent Video Gen Pack

A folder you point an AI coding agent at, so it can make **narrated, subtitled videos with [Remotion](https://www.remotion.dev)** from a plain request.

- **Remotion agent skills** installed locally in `.agents/skills/` (symlinked into `.claude/skills/`).
- **Voice-over** via [OpenRouter](https://openrouter.ai) text-to-speech (default `google/gemini-3.8-flash-tts`), called through the `openai` library.
- **Word-level timings** from NVIDIA Parakeet TDT 0.6B v3 running locally, for subtitles and synced animation.
- `AGENTS.md` tells the agent how the pieces fit together.

## Setup

Requirements: [`uv`](https://docs.astral.sh/uv/), Node.js, `ffmpeg`.

```bash
cp .env.example .env                 # add your OPENROUTER_API_KEY (https://openrouter.ai/settings/keys)
uv run scripts/download_model.py     # optional: pre-download the speech-recognition model (~2.4 GB)
```

## Use

Open this folder in your agent (Claude Code, Codex, Cursor, …) and ask, for example:

> Make a 45-second explainer video about how bees make honey. Calm female voice, 1080×1920, subtitles.

The agent will write the script, synthesize the voice-over, transcribe it for timings, build the Remotion project in a subfolder, and open Studio for you to preview.

## Scripts

| Command | Does |
| --- | --- |
| `uv run scripts/tts.py --text "..." -o out/a.mp3` | Text → speech through OpenRouter (`-i "cheerful announcer"` to change the delivery style) |
| `uv run scripts/transcribe.py out/a.mp3` | Speech → word/token timings JSON (+ Remotion captions) |
| `uv run scripts/download_model.py` | Pre-fetch the Parakeet model and VAD |

## Layout

```
AGENTS.md  CLAUDE.md          instructions for agents
docs/                         OpenRouter TTS, timings, Remotion setup, workflow (+ examples/)
                              client-billing-research.md  (owner notes: per-client spend tracking)
scripts/                      tts.py, transcribe.py, download_model.py, asr_models.py
.agents/skills/               remotion-* (third-party) + voiceover-tts, speech-timestamps (ours)
skills-lock.json              pinned sources of the installed Remotion skills
.cache/models/                downloaded ASR models (git-ignored)
```

## Update the Remotion skills

```bash
npx --yes skills@1.7.0 add remotion-dev/skills --yes
```
