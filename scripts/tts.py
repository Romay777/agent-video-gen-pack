#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["openai>=1.70"]
# ///
"""Text-to-speech through OpenRouter, using the regular `openai` SDK.

    uv run scripts/tts.py --text "Hello there." -o out/hello.mp3
    uv run scripts/tts.py --file script.txt --voice Puck -o public/voiceover/scene-01.mp3
    uv run scripts/tts.py --file script.txt -o out/a.mp3 \\
        --instructions "Speak like an upbeat radio announcer, fast and bright."
    echo "Hello" | uv run scripts/tts.py -o out/hello.mp3

Config (env vars or `.env` in the repo root, see `.env.example`):
    OPENROUTER_API_KEY      required
    OPENROUTER_BASE_URL     default https://openrouter.ai/api/v1
    OPENROUTER_TTS_MODEL    default google/gemini-3.8-flash-tts
    OPENROUTER_TTS_VOICE    default Zephyr
    OPENROUTER_TTS_INSTRUCTIONS   optional default delivery instructions
    OPENROUTER_USER         optional end-user/client id sent as `user` for usage attribution

Gemini TTS models on OpenRouter return raw PCM (16-bit mono, 24 kHz) whatever format is
requested, so the script asks for PCM and encodes it with ffmpeg into the format named by
the output file's extension (.mp3, .wav, ...). An output ending in .pcm keeps the raw bytes.

`--instructions` is free-form direction for HOW the text is delivered (mood, pace, accent,
persona). The voice stays the same; the performance changes. Supported by Gemini TTS and
OpenAI gpt-4o-mini-tts on OpenRouter; other models ignore it.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from openai import APIConnectionError, APIStatusError, OpenAI

REPO_ROOT = Path(__file__).resolve().parent.parent

HINTS = {
    400: "Malformed request or an option the routed provider does not support (check --voice).",
    401: "Missing or invalid OPENROUTER_API_KEY. Create one at https://openrouter.ai/settings/keys",
    402: "Insufficient OpenRouter credits.",
    403: "Spend limit reached, key disabled, or access blocked.",
    404: "Unknown model, or no provider can serve it. Check OPENROUTER_TTS_MODEL.",
    429: "Rate limited. Wait and retry with backoff.",
    502: "Upstream audio operation failed (not billed). Retry.",
}


def load_dotenv(path: Path) -> None:
    """Minimal .env reader; real environment variables win."""
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip().strip("'\"")
        if value:
            os.environ.setdefault(key.strip(), value)


def audio_duration(path: Path) -> float | None:
    if shutil.which("ffprobe") is None:
        return None
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def main() -> int:
    load_dotenv(REPO_ROOT / ".env")
    load_dotenv(Path.cwd() / ".env")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = parser.add_mutually_exclusive_group()
    src.add_argument("--text", help="Text to speak.")
    src.add_argument("--file", type=Path, help="Read the text from this file (UTF-8). Default: stdin.")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Output audio file, e.g. out/voice.mp3")
    parser.add_argument("--voice", default=os.environ.get("OPENROUTER_TTS_VOICE", "Zephyr"))
    parser.add_argument("--model", default=os.environ.get("OPENROUTER_TTS_MODEL", "google/gemini-3.8-flash-tts"))
    parser.add_argument("--sample-rate", type=int, default=24000,
                        help="Sample rate of the PCM the model returns (Gemini TTS: 24000).")
    style = parser.add_mutually_exclusive_group()
    style.add_argument("-i", "--instructions", default=os.environ.get("OPENROUTER_TTS_INSTRUCTIONS"),
                       help="Delivery/voice-style instruction, one or more full sentences "
                            "(e.g. 'Sad and quiet, as if telling a secret.').")
    style.add_argument("--instructions-file", type=Path, help="Read the instructions from this file (UTF-8).")
    parser.add_argument("--user", default=os.environ.get("OPENROUTER_USER"),
                        help="Client/end-user id, sent as OpenRouter `user` so usage can be attributed.")
    parser.add_argument("--session-id", help="Optional OpenRouter session id to group related requests.")
    args = parser.parse_args()

    if args.text is not None:
        text = args.text
    elif args.file is not None:
        text = args.file.read_text(encoding="utf-8")
    else:
        if sys.stdin.isatty():
            parser.error("provide --text, --file, or pipe text on stdin")
        text = sys.stdin.read()
    text = text.strip()
    if not text:
        parser.error("input text is empty")

    instructions = args.instructions
    if args.instructions_file is not None:
        instructions = args.instructions_file.read_text(encoding="utf-8")
    instructions = (instructions or "").strip() or None

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("error: OPENROUTER_API_KEY is not set (export it or put it in .env).", file=sys.stderr)
        return 2

    client = OpenAI(
        base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        api_key=api_key,
    )

    # `instructions` is a native SDK argument; `user` / `session_id` are OpenRouter extensions.
    options: dict = {}
    if instructions:
        options["instructions"] = instructions
    extra_body = {k: v for k, v in (("user", args.user), ("session_id", args.session_id)) if v}
    if extra_body:
        options["extra_body"] = extra_body

    raw_output = args.output.suffix.lower() == ".pcm"
    if not raw_output and shutil.which("ffmpeg") is None:
        print("error: ffmpeg is not on PATH; it encodes the PCM the model returns.", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Stream into a sibling file and swap the result in on success, so a failed re-take
    # leaves the previous take at `args.output` untouched.
    partial = args.output.with_name(args.output.name + ".part")
    generation_id = None
    try:
        # The response body is raw audio bytes, not JSON.
        with client.audio.speech.with_streaming_response.create(
            model=args.model,
            voice=args.voice,
            input=text,
            response_format="pcm",
            **options,
        ) as response:
            generation_id = response.headers.get("X-Generation-Id")
            response.stream_to_file(partial)
    except APIStatusError as e:
        hint = HINTS.get(e.status_code, "")
        print(f"error: OpenRouter returned HTTP {e.status_code}: {e.message}\n{hint}", file=sys.stderr)
        partial.unlink(missing_ok=True)
        return 1
    except APIConnectionError as e:
        print(f"error: could not reach OpenRouter: {e}", file=sys.stderr)
        partial.unlink(missing_ok=True)
        return 1
    if raw_output:
        os.replace(partial, args.output)
    else:
        # ffmpeg picks the encoder from the extension, so the temporary file keeps it.
        encoded = args.output.with_name(f"{args.output.stem}.part{args.output.suffix}")
        result = subprocess.run(
            ["ffmpeg", "-nostdin", "-y", "-loglevel", "error",
             "-f", "s16le", "-ar", str(args.sample_rate), "-ac", "1", "-i", str(partial), str(encoded)],
            capture_output=True, text=True,
        )
        partial.unlink(missing_ok=True)
        if result.returncode != 0:
            print(f"error: ffmpeg could not encode the audio:\n{result.stderr.strip()}", file=sys.stderr)
            encoded.unlink(missing_ok=True)
            return 1
        os.replace(encoded, args.output)

    size_kb = args.output.stat().st_size / 1024
    print(f"wrote {args.output} ({size_kb:.0f} KiB, model={args.model}, voice={args.voice}"
          f"{', styled' if instructions else ''})")
    if generation_id:
        print(f"generation id: {generation_id}")
    if raw_output:
        duration = args.output.stat().st_size / (2 * args.sample_rate)
    else:
        duration = audio_duration(args.output)
    if duration is not None:
        print(f"duration: {duration:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
