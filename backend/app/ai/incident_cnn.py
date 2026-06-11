"""Inference wrapper for OUR self-trained incident-type classifier.

The model is trained by ``backend/training/train_classifier.py`` (a ResNet-18
fine-tuned on our own labelled incident photos) and saved to
``incident_classifier.pt``. This module loads that checkpoint lazily at
inference time and exposes a single :func:`predict` helper.

Design goals:

* **Optional / non-breaking.** If torch isn't installed, the checkpoint is
  missing, or ``INCIDENT_CNN_ENABLED`` is false, :func:`predict` returns
  ``None`` and the caller falls back to the existing rule-based classifier.
  Nothing crashes if the model hasn't been trained yet.
* **Self-contained.** No dependency on the training package; it rebuilds the
  same architecture and loads the saved ``state_dict``.
"""
from __future__ import annotations

import io
import logging
import os
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Resolved default location: backend/weights/incident_classifier.pt
_DEFAULT_WEIGHTS = Path(__file__).resolve().parents[2] / "weights" / "incident_classifier.pt"

_model = None          # cached torch model
_classes: list[str] = []
_img_size = 224
_load_attempted = False
_unavailable = False


def _weights_path() -> Path:
    override = getattr(settings, "CLASSIFIER_WEIGHTS", "") or os.environ.get("CLASSIFIER_WEIGHTS", "")
    if override:
        return Path(override)
    # Honour the same persistent weights dir the YOLO model uses, if set.
    ml_dir = os.environ.get("ML_WEIGHTS_DIR")
    if ml_dir:
        candidate = Path(ml_dir) / "incident_classifier.pt"
        if candidate.exists():
            return candidate
    return _DEFAULT_WEIGHTS


def _load() -> bool:
    """Load the model once. Returns True if a usable model is available."""
    global _model, _classes, _img_size, _load_attempted, _unavailable
    if _model is not None:
        return True
    if _unavailable or _load_attempted:
        return _model is not None
    _load_attempted = True

    path = _weights_path()
    if not path.exists():
        logger.info("Incident CNN weights not found at %s; using rule classifier.", path)
        _unavailable = True
        return False
    try:
        import torch
        import torch.nn as nn
        from torchvision import models
    except ImportError as exc:
        logger.warning("torch/torchvision unavailable, incident CNN disabled: %s", exc)
        _unavailable = True
        return False

    try:
        ckpt = torch.load(str(path), map_location="cpu")
        _classes = list(ckpt["classes"])
        _img_size = int(ckpt.get("img_size", 224))
        model = models.resnet18(weights=None)
        model.fc = nn.Sequential(
            nn.Dropout(0.3), nn.Linear(model.fc.in_features, len(_classes))
        )
        model.load_state_dict(ckpt["state_dict"])
        model.eval()
        _model = model
        logger.info("Loaded self-trained incident CNN (%d classes) from %s", len(_classes), path)
        return True
    except Exception as exc:  # noqa: BLE001 - any load error => fall back
        logger.warning("Failed to load incident CNN (%s); using rule classifier.", exc)
        _unavailable = True
        return False


def predict(image_bytes: bytes) -> Optional[tuple[str, float]]:
    """Return ``(incident_type, confidence)`` from the trained CNN, or ``None``.

    ``None`` means "model not available / disabled" — caller should fall back to
    the rule-based classifier.
    """
    if not getattr(settings, "INCIDENT_CNN_ENABLED", False):
        return None
    if not _load():
        return None
    try:
        import torch
        from torchvision import transforms
        from PIL import Image

        norm = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        tf = transforms.Compose([
            transforms.Resize((_img_size, _img_size)),
            transforms.ToTensor(),
            norm,
        ])
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        x = tf(img).unsqueeze(0)
        with torch.no_grad():
            probs = torch.softmax(_model(x), dim=1)[0]  # type: ignore[misc]
        idx = int(probs.argmax().item())
        return _classes[idx], float(probs[idx].item())
    except Exception as exc:  # noqa: BLE001
        logger.warning("Incident CNN inference failed (%s); falling back.", exc)
        return None
