# Text-to-speech through OpenRouter

OpenRouter exposes an OpenAI-compatible API. To use it with the `openai` library you only change two things: `base_url` and `api_key`.

Model page: https://openrouter.ai/google/gemini-3.8-flash-tts · API keys: https://openrouter.ai/settings/keys · API docs: https://openrouter.ai/docs/api/api-reference/tts/create-speech

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | – (required) | Bearer token. Put it in `.env` (copy `.env.example`) or export it. |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | Swap only if proxying. |
| `OPENROUTER_TTS_MODEL` | `google/gemini-3.8-flash-tts` | Any OpenRouter model that serves `/audio/speech`. |
| `OPENROUTER_TTS_VOICE` | `Zephyr` | Voice id, provider-specific. |

`scripts/tts.py` reads `.env` from the repo root (real environment variables win).

## Use the script

```bash
uv run scripts/tts.py --text "Hello! This is a test." -o out/hello.mp3
uv run scripts/tts.py --file work/demo/scene-01.txt --voice Puck -o videos/my-video/public/voiceover/scene-01.mp3
cat script.txt | uv run scripts/tts.py -o out/voice.mp3
uv run scripts/tts.py --model google/gemini-3.8-flash-tts --voice Kore --text "..." -o out/x.wav   # format follows the extension
uv run scripts/tts.py --file scene.txt -o out/x.mp3 -i "Cheerful, fast, like an ad announcer."   # voice style
```

Gemini TTS models on OpenRouter return raw PCM (16-bit mono, 24 kHz) whatever `response_format` asks for. The script therefore requests PCM and encodes it with ffmpeg into the format of the output file's extension (`.mp3`, `.wav`, …); an output ending in `.pcm` keeps the raw bytes.

It prints the file size, the OpenRouter generation id and the duration. Exit code is non-zero on API errors with a hint for the HTTP status.

## The same thing in your own code

```python
from openai import OpenAI
import os

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

with client.audio.speech.with_streaming_response.create(
    model="google/gemini-3.8-flash-tts",
    voice="Zephyr",
    input="Hello! This is a text-to-speech test.",
    response_format="pcm",
) as response:
    response.stream_to_file("hello.pcm")   # body is raw audio bytes (16-bit mono PCM, 24 kHz), not JSON
```

```bash
curl https://openrouter.ai/api/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  --output hello.pcm \
  -d '{"model":"google/gemini-3.8-flash-tts","input":"Hello!","voice":"Zephyr","response_format":"pcm"}'
ffmpeg -nostdin -y -loglevel error -f s16le -ar 24000 -ac 1 -i hello.pcm hello.mp3   # raw PCM → a playable file
```

## `google/gemini-3.8-flash-tts` request fields

- `model` (required) – `"google/gemini-3.8-flash-tts"`
- `input` (required) – text to speak
- `voice` (optional) – one of: Zephyr, Puck, Charon, Kore, Fenrir, Leda, Orus, Aoede, Callirrhoe, Autonoe, Enceladus, Iapetus, Umbriel, Algieba, Despina, Erinome, Algenib, Rasalgethi, Laomedeia, Achernar, Alnilam, Schedar, Gacrux, Pulcherrima, Achird, Zubenelgenubi, Vindemiatrix, Sadachbia, Sadaltager, Sulafat
- `response_format` (optional) – the API accepts `mp3` and `pcm`, but Gemini models answer with PCM either way. Saving that body under an `.mp3` name gives a file nothing can play.
- `instructions` (optional) – delivery direction for the whole request, see [Voice style](#voice-style-instructions).
- `speed`, `input_references`, `provider`, `session_id`, `trace`, `user` – also accepted by OpenRouter's `/audio/speech` ([spec](https://openrouter.ai/docs/api/api-reference/tts/create-speech)). `speed` is honored only by some models; `input_references` is voice cloning/design from a reference clip; `user` and `session_id` are for usage attribution and are not sent to the provider.
- `input` may also be an array of turns `{text, voice?, instructions?}` for multi-speaker dialogue (Gemini TTS only). Not wired into `tts.py`; call the API directly if needed.

Response: raw audio bytes, headerless 16-bit mono PCM at 24 kHz; `X-Generation-Id` identifies the billed generation.

## Voice style (instructions)

The same voice can be performed differently by giving it a direction. Pass one or more **full sentences** describing how to deliver the text:

```bash
uv run scripts/tts.py --file scene.txt -o out/sad.mp3 \
  -i "Speak softly and slowly, with a sad, tired voice, as if you are about to cry."
uv run scripts/tts.py --file scene.txt -o out/ad.mp3 \
  -i "High-energy TV advertisement announcer: fast, bright, big smile in the voice, punchy pauses before key words."
```

```python
client.audio.speech.create(
    model="google/gemini-3.8-flash-tts", voice="Zephyr", input="...",
    instructions="Whisper conspiratorially, like sharing a secret.",
    response_format="pcm",
)
```

- Works with Gemini TTS and OpenAI `gpt-4o-mini-tts`; other models silently ignore it (so a "styled" result that sounds neutral usually means the model doesn't support it).
- Describe: emotion, pace, energy, persona/scene ("late-night radio host"), accent, pauses, what to emphasize. Be concrete; one paragraph is plenty.
- The text to speak goes in `input`, the direction in `instructions`; don't write stage directions into the narration text itself or they may be read aloud.
- Keep the instruction constant across all scenes of a video (use `--instructions-file` or `OPENROUTER_TTS_INSTRUCTIONS`) so the voice stays consistent, and change it per scene only on purpose.
- Style changes the speaking duration, so always re-run [`transcribe.py`](timestamps.md).
- If a model has no `instructions` support, the usual fallback is to pick another model or to prepend a natural-language direction to the text itself; the second is model-dependent and untested here.

## Errors

JSON body `{"error": {"code": <n>, "message": "..."}}` with the HTTP status.

| Status | Meaning |
| --- | --- |
| 400 | Malformed request or unsupported option (e.g. a voice the model doesn't have) |
| 401 | Missing/invalid API key (a malformed or unknown key is reported as "Missing Authentication header" even though the header was sent) |
| 402 | Insufficient credits |
| 403 | Spend limit reached, key disabled, or access blocked |
| 404 | Unknown model / no provider can serve it |
| 429 | Rate limited, retry with backoff |
| 502 | Upstream failure; failed generations are not billed, just retry |

## Tips

- Generate **per scene**, not one giant file: easier to re-take one line, and scene lengths come straight from the audio.
- Gemini TTS follows the language of the text. Write numbers and abbreviations the way they should be spoken.
- Re-synthesizing the same text produces different timing; re-run [`transcribe.py`](timestamps.md) after every re-take.
