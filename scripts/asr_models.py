"""Shared model loading for download_model.py and transcribe.py.

Models are stored as real files under <repo>/.cache/models/ (git-ignored), NOT in the
HuggingFace symlink cache: recent onnxruntime refuses to load external-weight files
(`encoder-model.onnx.data`) that resolve outside the model directory, which is exactly
what HF-cache symlinks do.
"""

from __future__ import annotations

from pathlib import Path

import onnx_asr

REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = REPO_ROOT / ".cache" / "models"

ASR_MODEL = "nemo-parakeet-tdt-0.6b-v3"
VAD_MODEL = "silero"


# CPU is plenty for a 0.6B model on short voice-overs and avoids CoreML/CUDA provider
# warnings and nondeterminism. Drop `providers` to let onnxruntime pick an accelerator.
PROVIDERS = ["CPUExecutionProvider"]


def asr_dir(quantization: str | None) -> Path:
    return MODELS_DIR / f"{ASR_MODEL}{'-' + quantization if quantization else ''}"


def load_asr(quantization: str | None = None):
    """Load Parakeet TDT 0.6B v3, downloading it into .cache/models on first use."""
    return onnx_asr.load_model(
        ASR_MODEL, path=asr_dir(quantization), quantization=quantization, providers=PROVIDERS
    )


def load_vad():
    """Load Silero VAD (small), downloading it into .cache/models on first use."""
    return onnx_asr.load_vad(VAD_MODEL, path=MODELS_DIR / f"{VAD_MODEL}-vad", providers=PROVIDERS)
