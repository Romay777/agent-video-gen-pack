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
    400: "Malformed request or an option the routed provider does not support (check --voice / --format).",
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
    parser.add_argument("--format", choices=["mp3", "pcm"], default="mp3",
                        help="mp3 (default, use this for Remotion) or raw pcm.")
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

    args.output.parent.mkdir(parents=True, exist_ok=True)
    generation_id = None
    try:
        # The response body is raw audio bytes, not JSON.
        with client.audio.speech.with_streaming_response.create(
            model=args.model,
            voice=args.voice,
            input=text,
            response_format=args.format,
            **options,
        ) as response:
            generation_id = response.headers.get("X-Generation-Id")
            response.stream_to_file(args.output)
    except APIStatusError as e:
        hint = HINTS.get(e.status_code, "")
        print(f"error: OpenRouter returned HTTP {e.status_code}: {e.message}\n{hint}", file=sys.stderr)
        args.output.unlink(missing_ok=True)
        return 1
    except APIConnectionError as e:
        print(f"error: could not reach OpenRouter: {e}", file=sys.stderr)
        args.output.unlink(missing_ok=True)
        return 1

    size_kb = args.output.stat().st_size / 1024
    print(f"wrote {args.output} ({size_kb:.0f} KiB, model={args.model}, voice={args.voice}"
          f"{', styled' if instructions else ''})")
    if generation_id:
        print(f"generation id: {generation_id}")
    if args.format == "mp3":
        duration = audio_duration(args.output)
        if duration is not None:
            print(f"duration: {duration:.2f}s")
    else:
        print("raw PCM: sample rate is not documented by OpenRouter; convert with ffmpeg "
              "(e.g. -f s16le -ar 24000 -ac 1 -i in.pcm out.wav) and verify by ear. Prefer --format mp3.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
