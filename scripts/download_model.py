#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["onnx-asr[cpu,hub]>=0.7"]
# ///
"""Pre-download the local speech-recognition models so the first transcription is not slow.

    uv run scripts/download_model.py                 # Parakeet TDT 0.6B v3 (+ Silero VAD)
    uv run scripts/download_model.py --quantization int8   # smaller/faster variant

Models are stored in <repo>/.cache/models/ (git-ignored; see scripts/asr_models.py for why).
`scripts/transcribe.py` downloads the same files lazily, so running this is optional.
"""

from __future__ import annotations

import argparse
import time

import asr_models


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quantization", choices=["int8"], default=None,
                        help="Download the int8-quantized model instead of the full-precision one.")
    parser.add_argument("--no-vad", action="store_true", help="Skip the Silero VAD model.")
    args = parser.parse_args()

    start = time.time()
    print(f"Downloading {asr_models.ASR_MODEL} (quantization={args.quantization or 'none'}) ...")
    asr_models.load_asr(args.quantization)
    if not args.no_vad:
        print("Downloading silero VAD ...")
        asr_models.load_vad()
    print(f"Done in {time.time() - start:.0f}s. Models are in {asr_models.MODELS_DIR}; later runs need no network.")


if __name__ == "__main__":
    main()
