#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["onnx-asr[cpu,hub]>=0.7"]
# ///
"""Transcribe a voice-over locally with NVIDIA Parakeet TDT 0.6B v3 and emit word/token timings.

    uv run scripts/transcribe.py public/voiceover.mp3
    uv run scripts/transcribe.py out/scene-01.mp3 -o public/voiceover/scene-01.json

Output JSON (all times in seconds unless the key ends in Ms):
    audio, duration, model, text
    words:     [{text, start, end, confidence}]       one per spoken word (punctuation attached)
    tokens:    [{text, start, end, confidence}]       raw model tokens, text keeps the leading space
    sentences: [{text, start, end}]                   split on . ! ? …
    captions:  [{text, startMs, endMs, timestampMs, confidence}]   Remotion `Caption` type

Parakeet reports the START of each token only (0.08 s grid). `end` is the next token's start,
capped at MAX_TOKEN_SECONDS so a word before a pause does not stretch over the silence.
Any ffmpeg-readable input works (mp3, wav, m4a, mp4...). Models load from .cache/models
(run scripts/download_model.py once to fetch them ahead of time).
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

MAX_TOKEN_SECONDS = 0.4
VAD_AUTO_THRESHOLD_SECONDS = 20.0  # most Parakeet pipelines handle ~20-30 s per pass
SENTENCE_END = (".", "!", "?", "…")


def to_16k_mono_wav(src: Path, dst: Path) -> None:
    if shutil.which("ffmpeg") is None:
        raise SystemExit("error: ffmpeg is required (brew install ffmpeg).")
    result = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", str(dst)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"error: ffmpeg could not read {src}:\n{result.stderr.strip()}")


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


def recognize(wav: Path, duration: float, vad_mode: str, quantization: str | None):
    """Return a list of (offset_seconds, segment_end_seconds, TimestampedResult-like)."""
    import asr_models

    use_vad = vad_mode == "always" or (vad_mode == "auto" and duration > VAD_AUTO_THRESHOLD_SECONDS)
    model = asr_models.load_asr(quantization)
    if use_vad:
        # Order matters: with_vad(...).with_timestamps(). Token timestamps are relative to each
        # segment, so the segment start must be added back.
        model = model.with_vad(asr_models.load_vad()).with_timestamps()
        return [(seg.start, seg.end, seg) for seg in model.recognize(str(wav))], True
    result = model.with_timestamps().recognize(str(wav))
    return [(0.0, duration, result)], False


def build_tokens(segments) -> list[dict]:
    """Flatten segments to absolute-time tokens; mark the first token of each segment."""
    tokens: list[dict] = []
    for offset, seg_end, seg in segments:
        count = len(seg.tokens)
        for i, (text, ts, lp) in enumerate(zip(seg.tokens, seg.timestamps, seg.logprobs)):
            start = offset + ts
            if i + 1 < count:
                end = offset + seg.timestamps[i + 1]
            else:
                end = seg_end
            end = min(max(end, start), start + MAX_TOKEN_SECONDS)
            tokens.append({
                "text": text,
                "start": start,
                "end": end,
                "confidence": math.exp(lp),
                "_segment_start": i == 0,
            })
    return tokens


def group_words(tokens: list[dict]) -> list[dict]:
    """SentencePiece tokens carry a leading space on word starts; others continue the word."""
    words: list[dict] = []
    current: dict | None = None
    for tok in tokens:
        starts_word = current is None or tok["_segment_start"] or tok["text"].startswith(" ")
        if starts_word:
            current = {"text": tok["text"].strip(), "start": tok["start"], "end": tok["end"], "_conf": []}
            words.append(current)
        else:
            current["text"] += tok["text"]
            current["end"] = tok["end"]
        if any(c.isalnum() for c in tok["text"]):  # trailing punctuation says nothing about the word
            current["_conf"].append(tok["confidence"])
    for w in words:
        confs = w.pop("_conf")
        w["confidence"] = min(confs) if confs else 1.0  # a word is only as certain as its weakest token
    return [w for w in words if w["text"]]


def group_sentences(words: list[dict]) -> list[dict]:
    sentences: list[dict] = []
    buf: list[dict] = []
    for w in words:
        buf.append(w)
        if w["text"].endswith(SENTENCE_END):
            sentences.append(_sentence(buf))
            buf = []
    if buf:
        sentences.append(_sentence(buf))
    return sentences


def _sentence(words: list[dict]) -> dict:
    return {"text": " ".join(w["text"] for w in words), "start": words[0]["start"], "end": words[-1]["end"]}


def to_captions(words: list[dict]) -> list[dict]:
    """Remotion `Caption` objects: a leading space on every word but the first."""
    captions = []
    for i, w in enumerate(words):
        start_ms = round(w["start"] * 1000)
        end_ms = round(w["end"] * 1000)
        captions.append({
            "text": w["text"] if i == 0 else " " + w["text"],
            "startMs": start_ms,
            "endMs": end_ms,
            "timestampMs": round((start_ms + end_ms) / 2),
            "confidence": round(w["confidence"], 4),
        })
    return captions


def rounded(items: list[dict], keys=("start", "end")) -> list[dict]:
    out = []
    for item in items:
        item = {k: v for k, v in item.items() if not k.startswith("_")}
        for k in keys:
            item[k] = round(item[k], 3)
        if "confidence" in item:
            item["confidence"] = round(item["confidence"], 4)
        out.append(item)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("audio", type=Path, help="Audio (or video) file to transcribe.")
    parser.add_argument("-o", "--output", type=Path, help="Output JSON. Default: <audio>.timestamps.json next to the input.")
    parser.add_argument("--vad", choices=["auto", "always", "never"], default="auto",
                        help=f"Silero VAD chunking for long audio. auto = on above {VAD_AUTO_THRESHOLD_SECONDS:.0f}s.")
    parser.add_argument("--quantization", choices=["int8"], default=None, help="Use the int8 model (smaller, faster).")
    args = parser.parse_args()

    if not args.audio.is_file():
        print(f"error: {args.audio} not found", file=sys.stderr)
        return 2
    output = args.output or args.audio.with_suffix(args.audio.suffix + ".timestamps.json")

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "audio-16k.wav"
        to_16k_mono_wav(args.audio, wav)
        duration = wav_duration(wav)
        segments, used_vad = recognize(wav, duration, args.vad, args.quantization)

    tokens = build_tokens(segments)
    words = group_words(tokens)
    if not words:
        print("error: no speech recognized", file=sys.stderr)
        return 1

    data = {
        "audio": str(args.audio),
        "duration": round(duration, 3),
        "model": "nvidia/parakeet-tdt-0.6b-v3 (onnx-asr)",
        "vad": used_vad,
        "text": " ".join(w["text"] for w in words),
        "words": rounded(words),
        "tokens": rounded(tokens),
        "sentences": rounded(group_sentences(words)),
        "captions": to_captions(words),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output}: {len(words)} words, {len(tokens)} tokens, {duration:.2f}s audio (vad={used_vad})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
