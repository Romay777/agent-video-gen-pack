---
name: voiceover-tts
description: Generate a voice-over (text-to-speech) for a video through OpenRouter using the openai-compatible API. Use when a video needs narration, when asked to write a narration script, or to re-take a line of voice-over.
---

# Voice-over through OpenRouter

Run from the repo root. Needs `OPENROUTER_API_KEY` in `.env` or the environment.

```bash
uv run scripts/tts.py --file work/<video>/scene-01.txt -o <remotion-project>/public/voiceover/scene-01.mp3
uv run scripts/tts.py --text "Hello!" --voice Puck -o out/hello.mp3
uv run scripts/tts.py --file scene.txt -o out/s.mp3 -i "Cheerful, fast, like a TV ad announcer."   # voice style
```

Defaults: model `google/gemini-3.8-flash-tts`, voice `Zephyr`, format `mp3`. Override with `--model`, `--voice`, `--format` or `OPENROUTER_TTS_MODEL` / `OPENROUTER_TTS_VOICE`.

`-i/--instructions` (or `--instructions-file`, `OPENROUTER_TTS_INSTRUCTIONS`) changes **how** the same voice speaks: mood, pace, persona, e.g. sad, cheerful, announcer. Write it as full sentences; keep it identical across scenes unless the story needs a change.

## Rules

- One file per scene; keep the text in `work/<video>/scene-NN.txt`.
- If the person describes a mood or character for the voice, put it in `--instructions`, not in the narration text.
- Always `mp3` for Remotion. `pcm` has no documented sample rate.
- If the key is missing, ask the person for it and put it in `.env`. Never print it or write it anywhere else.
- After every (re-)take run `uv run scripts/transcribe.py` on the new file; the old timings no longer match.
- Write narration to be heard: short sentences, numbers and acronyms spelled the way they are spoken, ~150 words per minute.

## More

- Voices, request fields, error codes, SDK/curl examples: `docs/openrouter-tts.md`
- Script writing and the whole pipeline: `docs/workflow.md`
- Next step: skill `speech-timestamps`
