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

`-i/--instructions` (or `--instructions-file`, `OPENROUTER_TTS_INSTRUCTIONS`) changes **how** the same voice speaks: mood, pace, persona, e.g. sad, cheerful, announcer. Write it as full sentences. A different instruction changes the voice's character, so reusing one keeps a video consistent.

## Good to know

- One text file and one mp3 per scene (`work/<video>/scene-NN.txt`) lets a single line be re-taken alone; one file for the whole narration works too.
- If the person describes a mood or character for the voice, put it in `--instructions`, not in the narration text.
- Use `mp3` for Remotion: `pcm` has no documented sample rate.
- If the key is missing, ask the person for it and put it in `.env`. Never print it or write it anywhere else.
- A re-take changes the timing: when the video uses timings (subtitles, word sync), transcribe the new file again.
- The model reads text literally: spell numbers and acronyms the way they should sound. Speech runs at roughly 150 words per minute.

## More

- Voices, request fields, error codes, SDK/curl examples: `docs/openrouter-tts.md`
- A full worked example of a narrated video: `docs/workflows/narrated-video.md`
- Word timings for subtitles or sync: skill `speech-timestamps`
