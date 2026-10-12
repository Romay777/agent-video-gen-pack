---
name: speech-timestamps
description: Get per-word and per-token timings from an audio or video file locally (NVIDIA Parakeet TDT 0.6B v3) to sync subtitles and animation with a voice-over in Remotion. Use after generating speech, after cutting a clip, or for any audio that needs subtitles or word-level timing.
---

# Word and token timings

```bash
uv run scripts/transcribe.py videos/my-video/public/voiceover/scene-01.mp3 -o videos/my-video/public/voiceover/scene-01.json
```

First run downloads ~2.4 GB into `.cache/models/` (or run `uv run scripts/download_model.py` beforehand). No API key, no network afterwards.

## Output JSON

`duration`, `text`, then arrays: `words` / `tokens` (`{text, start, end, confidence}` in seconds), `sentences` (`{text, start, end}`), and `captions` (Remotion `Caption[]`: `{text, startMs, endMs, timestampMs, confidence}`).

## How to use it in Remotion

- Length: a voice-over line is `Math.ceil((duration + pauseSeconds) * fps)` frames; a video clip is `Math.floor(duration * fps)`.
- Subtitles: give `captions` to a captions element such as `<BasicCaptions>` or word-highlight captions (see `remotion-captions/display-captions.md` in skill `remotion-best-practices`). Times are relative to the audio file, so keep audio and captions in the same `<Series.Sequence>`.
- Animations: frame = `Math.round(word.start * fps)`.
- Working examples: `docs/examples/Narrated.tsx` (voice-over), `docs/examples/Clips.tsx` (existing footage).

## Know the limits

- Only token **starts** are measured (0.08 s grid); `end` is derived and capped at 0.4 s.
- The text is a transcription, not your script. Check low `confidence` words (< 0.7) and mismatches against what was meant; for a generated voice-over, rephrase and re-take that line.
- Audio > 20 s is chunked with VAD on pauses; prefer short per-scene files.
- 25 European languages, auto-detected. English and Russian included.
- No speech in the file: `error: no speech recognized`, no JSON.

Details and internals: `docs/timestamps.md`.
