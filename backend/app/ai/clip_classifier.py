"""CLIP zero-shot accident detector.

A much more robust accident/normal decision than our small ResNet: it uses
OpenAI CLIP (ViT-B/32), trained on 400M image-text pairs, so it understands the
*concept* of a car accident and generalises to wide pileups, close-up crashes,
stylised/AI images and unusual angles that a small CNN trained on a few thousand
photos misses.

How it works: we embed a set of "accident" text prompts and "normal" text
prompts once, then for each photo we compare its CLIP image embedding to both.
The decision is the **margin** = (best accident similarity) - (best normal
similarity); a photo is an accident when the margin clears a calibrated
threshold. Non-accident photos sit near/below zero margin, real accidents well
above it.

Safe + optional: if ``open_clip`` isn't installed or ``CLIP_CLASSIFIER_ENABLED``
is false, :func:`predict_accident_margin` returns ``None`` and the caller falls
back to the ResNet classifier / rules. Nothing crashes if CLIP is unavailable.
"""
from __future__ import annotations

import io
import logging
import os
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Prompt banks. More "normal" prompts (incl. ordinary road/traffic scenes) make
# the detector reject non-accident street photos instead of over-flagging them.
ACCIDENT_PROMPTS = [
    "a car accident", "a car crash", "a traffic accident", "wrecked cars",
    "a vehicle collision", "damaged cars after a crash", "a multi-car pileup",
    "a road accident scene", "an overturned car", "a car with crumpled bodywork",
]
NORMAL_PROMPTS = [
    "a normal street scene", "an ordinary road", "cars in traffic", "a parked car",
    "a clean undamaged car", "an empty road", "a building", "an everyday outdoor scene",
    "people walking", "a landscape", "a person", "an indoor scene",
]

_model = None
_preprocess = None
_acc_text = None      # cached accident prompt embeddings
_norm_text = None     # cached normal prompt embeddings
_probe = None         # (coef, intercept) of a logistic-regression probe, if present
_load_attempted = False
_unavailable = False


def _weights_dir() -> str:
    return os.environ.get("CLIP_CACHE_DIR") or os.environ.get("ML_WEIGHTS_DIR") or "/app/weights"


def _load() -> bool:
    """Load CLIP + precompute prompt embeddings once. True if usable."""
    global _model, _preprocess, _acc_text, _norm_text, _load_attempted, _unavailable
    if _model is not None:
        return True
    if _unavailable or _load_attempted:
        return _model is not None
    _load_attempted = True
    try:
        import torch
        import open_clip
    except ImportError as exc:
        logger.warning("open_clip not installed; CLIP detector disabled: %s", exc)
        _unavailable = True
        return False
    try:
        # Persist the ~600 MB weights on the mounted weights volume so they are
        # not re-downloaded on every container restart.
        cache_dir = _weights_dir()
        model, _, preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32", pretrained="openai", cache_dir=cache_dir
        )
        tok = open_clip.get_tokenizer("ViT-B-32")
        model.eval()
        with torch.no_grad():
            at = model.encode_text(tok(ACCIDENT_PROMPTS)); at /= at.norm(dim=-1, keepdim=True)
            nt = model.encode_text(tok(NORMAL_PROMPTS)); nt /= nt.norm(dim=-1, keepdim=True)
        _model, _preprocess, _acc_text, _norm_text = model, preprocess, at, nt
        # Optional trained linear probe (much more accurate than the raw margin).
        _load_probe()
        logger.info("Loaded CLIP accident detector (ViT-B-32, openai)%s.",
                    " + linear probe" if _probe is not None else " (zero-shot)")
        return True
    except Exception as exc:  # noqa: BLE001 - any load error => fall back
        logger.warning("Failed to load CLIP (%s); falling back to ResNet/rules.", exc)
        _unavailable = True
        return False


def _load_probe() -> None:
    """Load the logistic-regression probe (clip_probe.npz) if it exists."""
    global _probe
    try:
        import numpy as np
        from pathlib import Path
        path = Path(_weights_dir()) / "clip_probe.npz"
        if not path.exists():
            return
        data = np.load(str(path))
        _probe = (data["coef"].astype("float32"), float(data["intercept"][0]))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load CLIP probe (%s); using zero-shot margin.", exc)
        _probe = None


def _image_features(image_bytes: bytes):
    import torch
    from PIL import Image
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    x = _preprocess(img).unsqueeze(0)
    with torch.no_grad():
        f = _model.encode_image(x); f /= f.norm(dim=-1, keepdim=True)
    return f


def predict_accident_prob(image_bytes: bytes) -> Optional[float]:
    """Return P(accident) in [0,1] from CLIP, or ``None`` if unavailable.

    Uses the trained linear probe when present (far more accurate); otherwise
    falls back to a sigmoid of the zero-shot prompt margin.
    """
    if not getattr(settings, "CLIP_CLASSIFIER_ENABLED", False):
        return None
    if not _load():
        return None
    try:
        import numpy as np
        f = _image_features(image_bytes)
        if _probe is not None:
            coef, intercept = _probe
            z = float(np.dot(coef.reshape(-1), f[0].numpy()) + intercept)
            return float(1.0 / (1.0 + np.exp(-z)))
        # Zero-shot fallback: map the prompt margin into a probability.
        margin = float((f @ _acc_text.T).max().item() - (f @ _norm_text.T).max().item())
        return float(1.0 / (1.0 + np.exp(-margin * 60.0)))
    except Exception as exc:  # noqa: BLE001
        logger.warning("CLIP inference failed (%s); falling back.", exc)
        return None


def predict_accident_margin(image_bytes: bytes) -> Optional[float]:
    """Return the accident **margin** (accident_sim - normal_sim), or ``None``.

    ``None`` means CLIP is disabled/unavailable — caller should fall back. A
    margin >= ``CLIP_MARGIN_THRESHOLD`` means the photo is an accident.
    """
    if not getattr(settings, "CLIP_CLASSIFIER_ENABLED", False):
        return None
    if not _load():
        return None
    try:
        import torch
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        x = _preprocess(img).unsqueeze(0)
        with torch.no_grad():
            f = _model.encode_image(x); f /= f.norm(dim=-1, keepdim=True)
            acc = float((f @ _acc_text.T).max().item())
            nrm = float((f @ _norm_text.T).max().item())
        return acc - nrm
    except Exception as exc:  # noqa: BLE001
        logger.warning("CLIP inference failed (%s); falling back.", exc)
        return None
