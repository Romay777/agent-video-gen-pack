# Word and token timings (local speech recognition)

`scripts/transcribe.py` runs NVIDIA **Parakeet TDT 0.6B v3** locally (ONNX, via [`onnx-asr`](https://github.com/istupakov/onnx-asr)) on a voice-over and tells you when each word was spoken. No network or API key needed after the model is downloaded.

## Commands

```bash
uv run scripts/download_model.py                       # optional pre-download (~2.4 GB + 2 MB VAD) into .cache/models/
uv run scripts/transcribe.py videos/my-video/public/voiceover/scene-01.mp3
uv run scripts/transcribe.py in.mp3 -o work/in.json --vad always
uv run scripts/transcribe.py in.mp3 --quantization int8   # smaller/faster; run download_model.py --quantization int8 first
```

Default output path: `<audio>.timestamps.json` next to the input (e.g. `scene-01.mp3.timestamps.json`); pass `-o` to choose.
Any file `ffmpeg` can read works; it is converted to 16 kHz mono WAV in a temp dir first.
Speed on an Apple-silicon CPU: ~45 s of audio in ~5 s after the models are cached.

## Output

```jsonc
{
  "audio": "public/voiceover/scene-01.mp3",
  "duration": 6.44,                         // seconds
  "model": "nvidia/parakeet-tdt-0.6b-v3 (onnx-asr)",
  "vad": false,                             // true when Silero VAD chunking was used
  "text": "Hello there, this is a short test ...",
  "words":     [{ "text": "there,", "start": 0.48, "end": 0.88, "confidence": 0.99 }],
  "tokens":    [{ "text": " there", "start": 0.48, "end": 0.72, "confidence": 1.0 }],  // raw model tokens
  "sentences": [{ "text": "Hello there, ... timestamps.", "start": 0.0, "end": 4.32 }],
  "captions":  [{ "text": " there,", "startMs": 480, "endMs": 880, "timestampMs": 680, "confidence": 0.99 }]
}
```

- `words` – use for karaoke-style highlighting, per-word animation, and cutting scenes on a word.
- `tokens` – sub-word pieces (`" sh"`, `"ort"`); a leading space marks the start of a word. Use for finer effects.
- `sentences` – split on `. ! ? …`; handy for one subtitle line or one scene beat per sentence.
- `captions` – exactly Remotion's `Caption` type (`@remotion/captions`): every entry except the first has a leading space, times in ms.
- `confidence` is the model's probability (word = weakest alphanumeric token). Values below ~0.7 usually mean a rare word, a name, or a mispronunciation worth a listen; compare `text` to your script.

## Accuracy and limits — read before relying on `end`

- The model reports only each token's **start**, on a **0.08 s** grid. `end` is derived: next token's start, capped at 0.4 s so a word before a pause doesn't stretch across the silence. The final word is capped the same way.
- Absolute times were checked against a clip with known silence gaps and were within ~0.02 s (plus the 0.08 s quantization).
- The recognized text is a transcription, not your script: punctuation and capitalization come from the model, numbers may be spelled differently ("20" vs "twenty"). To show the script text with the audio timing, align by word order or use the recognized text as-is.
- ~20–30 s is the per-pass limit. Audio longer than 20 s automatically goes through Silero VAD, which splits on pauses and transcribes each speech segment. A voice-over with **no** pauses over ~30 s may produce an overly long VAD segment; prefer per-scene audio files.
- Languages: 25 European languages with automatic detection (English, Russian, German, French, Spanish, Italian, Polish, Ukrainian, …). Not suitable for Chinese, Japanese, Arabic, etc.

## Implementation notes (for when you change the scripts)

- `onnx_asr` result objects: `TimestampedResult(text, tokens, timestamps, logprobs)`; with VAD, `TimestampedSegmentResult(start, end, text, tokens, timestamps, logprobs)`. **Token timestamps are relative to the segment**; add `segment.start`.
- Chain order matters: `load_model(...).with_vad(vad).with_timestamps()`. Reversing it drops the timestamps.
- Models are stored under `.cache/models/` as real files, not in the HuggingFace symlink cache, because current `onnxruntime` rejects external-weight files (`encoder-model.onnx.data`) that resolve outside the model directory.
- `scripts/asr_models.py` pins `CPUExecutionProvider`. Remove `PROVIDERS` there to try CoreML/CUDA.
- Alternative runtime: NVIDIA NeMo (`pip install nemo_toolkit['asr']`, `ASRModel.from_pretrained("nvidia/parakeet-tdt-0.6b-v3").transcribe([...], timestamps=True)` → `output[0].timestamp['word']`). Heavier (PyTorch) and not needed here.
- License of the model: CC BY 4.0.
