---
name: speech-timestamps
description: Get per-word and per-token timings from an audio file locally (NVIDIA Parakeet TDT 0.6B v3) to sync subtitles and animation with a voice-over in Remotion. Use after generating speech, or for any audio that needs subtitles or word-level timing.
---

# Word and token timings

```bash
uv run scripts/transcribe.py <project>/public/voiceover/scene-01.mp3 -o <project>/public/voiceover/scene-01.json
```

First run downloads ~2.4 GB into `.cache/models/` (or run `uv run scripts/download_model.py` beforehand). No API key, no network afterwards.

## Output JSON

`duration`, `text`, then arrays: `words` / `tokens` (`{text, start, end, confidence}` in seconds), `sentences` (`{text, start, end}`), and `captions` (Remotion `Caption[]`: `{text, startMs, endMs, timestampMs, confidence}`).

## How to use it in Remotion

- Scene length: `Math.ceil((duration + padSeconds) * fps)`.
- Subtitles: give `captions` to `<BasicCaptions>` (see skill `remotion-captions`). Times are relative to the audio file, so keep audio and captions in the same `<Series.Sequence>`.
- Animations: frame = `Math.round(word.start * fps)`.
- Working example: `docs/examples/Narrated.tsx`.

## Know the limits

- Only token **starts** are measured (0.08 s grid); `end` is derived and capped at 0.4 s.
- The text is a transcription, not your script. Check low `confidence` words (< 0.7) and mismatches against the script, then re-take that scene.
- Audio > 20 s is chunked with VAD on pauses; prefer short per-scene files.
- 25 European languages, auto-detected. English and Russian included.

Details and internals: `docs/timestamps.md`.
