---
name: voiceover-tts
description: Generate a voice-over (text-to-speech) for a video through OpenRouter using the openai-compatible API. Use when a video needs narration, when asked to write a narration script, or to re-take a line of voice-over.
---

# Voice-over through OpenRouter

Run from the repo root. Needs `OPENROUTER_API_KEY` in `.env` or the environment.

```bash
uv run scripts/tts.py --file work/demo/scene-01.txt -o videos/my-video/public/voiceover/scene-01.mp3
uv run scripts/tts.py --text "Hello!" --voice Puck -o out/hello.mp3
uv run scripts/tts.py --file scene.txt -o out/s.mp3 -i "Cheerful, fast, like a TV ad announcer."   # voice style
```

Defaults: model `google/gemini-3.8-flash-tts`, voice `Zephyr`. Override with `--model`, `--voice` or `OPENROUTER_TTS_MODEL` / `OPENROUTER_TTS_VOICE`. The model returns raw PCM; the script encodes it with ffmpeg into the format of the `-o` extension.

`-i/--instructions` (or `--instructions-file`, `OPENROUTER_TTS_INSTRUCTIONS`) changes **how** the same voice speaks: mood, pace, persona, e.g. sad, cheerful, announcer. Write it as full sentences. A different instruction changes the voice's character, so reusing one keeps a video consistent.

## Voices

Female: Zephyr (default), Kore, Leda, Aoede, Callirrhoe, Autonoe, Despina, Erinome, Laomedeia, Achernar, Gacrux, Pulcherrima, Vindemiatrix, Sulafat.
Male: Puck, Charon, Fenrir, Orus, Enceladus, Iapetus, Umbriel, Algieba, Algenib, Rasalgethi, Alnilam, Schedar, Achird, Zubenelgenubi, Sadachbia, Sadaltager.

## Re-takes

- The voice, model and `-i` text of a video are recorded in `videos/<name>/NOTES.md`. Read them before re-taking a line and change only what was asked; write them there when you first choose them.
- A changed instruction on one scene makes it sound different from its neighbours. When that is not the point of the request, tell the person and offer to re-take the others to match.
- The output file is replaced only when the request succeeds, so a failed re-take keeps the previous take. Copy the old take aside first if the person may want it back.
- A new take has a new length: scenes sized from the timings JSON need it transcribed again; durations written by hand need editing.

## Good to know

- One text file and one mp3 per scene (`work/<name>/scene-NN.txt`) lets a single line be re-taken alone; one file for the whole narration works too.
- If the person describes a mood or character for the voice, put it in `--instructions`, not in the narration text.
- Give `-o` an `.mp3` (or `.wav`) name for Remotion; `.pcm` keeps the raw headerless bytes, which players cannot open.
- If the key is missing, ask the person for it and put it in `.env`. Never print it or write it anywhere else.
- The model reads text literally: spell numbers and acronyms the way they should sound. Speech runs at roughly 150 words per minute.

## More

- Voices, request fields, error codes, SDK/curl examples: `docs/openrouter-tts.md`
- A full worked example of a narrated video: `docs/workflows/narrated-video.md`
- Word timings for subtitles or sync: skill `speech-timestamps`
