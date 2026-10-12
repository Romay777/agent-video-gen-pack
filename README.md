# Agent Video Gen Pack

A folder you point an AI coding agent at, so it can make **videos with [Remotion](https://www.remotion.dev)** from a plain request. It gives the agent building blocks (voice-over, word timings, cutting footage, composition, optional subtitles) and two worked example routes; the agent combines the blocks however the request needs:

- **Narrated video**: motion graphics from an idea, with an AI voice-over. [docs/workflows/narrated-video.md](docs/workflows/narrated-video.md)
- **Clips from an existing video**: cut footage that already has speech into clips, with subtitles and effects on top. [docs/workflows/clip-existing-video.md](docs/workflows/clip-existing-video.md)

What is inside:

- **The Remotion agent skill** (`remotion-best-practices`, a bundle of all Remotion skills) installed locally in `.agents/skills/` (symlinked into `.claude/skills/`).
- **Voice-over** via [OpenRouter](https://openrouter.ai) text-to-speech (default `google/gemini-3.8-flash-tts`), called through the `openai` library.
- **Word-level timings** from NVIDIA Parakeet TDT 0.6B v3 running locally, for subtitles and synced animation.
- **A guide to cutting existing footage** with `ffmpeg`; the agent runs ffmpeg itself.
- `AGENTS.md` tells the agent how the pieces fit together.

## Setup

Requirements: [`uv`](https://docs.astral.sh/uv/), Node.js 18+, and **`ffmpeg`** (required by both workflows; install: [docs/ffmpeg.md](docs/ffmpeg.md)).

```bash
brew install ffmpeg                  # macOS; Linux: sudo apt install ffmpeg; Windows: winget install Gyan.FFmpeg
cp .env.example .env                 # add your OPENROUTER_API_KEY (https://openrouter.ai/settings/keys); only the voice-over needs it
uv run scripts/download_model.py     # optional: pre-download the speech-recognition model (~2.4 GB)
```

## Use

Open this folder in your agent (Claude Code, Codex, Cursor, …) and ask, for example:

> Make a 45-second explainer video about how bees make honey. Calm female voice, 1080×1920, subtitles.

The agent will write the script, create a Remotion project in `videos/`, synthesize the voice-over, transcribe it for timings, build the composition, and open Studio for you to preview.

> Here is `~/Downloads/podcast.mp4`. Cut the three best moments into vertical shorts with subtitles and a title.

The agent will transcribe the recording, propose the moments, cut them with ffmpeg, and lay captions and effects over them in Remotion.

## Scripts

| Command | Does |
| --- | --- |
| `uv run scripts/tts.py --text "..." -o out/a.mp3` | Text → speech through OpenRouter (`-i "cheerful announcer"` to change the delivery style) |
| `uv run scripts/transcribe.py out/a.mp3` | Speech (audio or video file) → word/token timings JSON (+ Remotion captions) |
| `uv run scripts/download_model.py` | Pre-fetch the Parakeet model and VAD |

## Layout

```
AGENTS.md  CLAUDE.md          instructions for agents
docs/workflows/               worked example routes: narrated-video.md, clip-existing-video.md
docs/                         OpenRouter TTS, timings, ffmpeg, Remotion setup (+ examples/)
                              client-billing-research.md  (owner notes: per-client spend tracking)
scripts/                      tts.py, transcribe.py, download_model.py, asr_models.py
.agents/skills/               remotion-best-practices (third-party) + voiceover-tts, speech-timestamps, video-clipping (ours)
skills-lock.json              pinned source of the installed Remotion skill
.cache/models/                downloaded ASR models (git-ignored)
videos/<name>/                one Remotion project per video, with its NOTES.md (git-ignored)
work/                         scene texts, picks, intermediate files (git-ignored)
```

## Update the Remotion skill

```bash
npx --yes skills@1.7.0 add remotion-dev/skills --skill remotion-best-practices --yes
```
