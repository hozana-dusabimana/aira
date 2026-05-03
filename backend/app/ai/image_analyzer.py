"""Image analyzer.

Two backends are supported:

- ``StubAnalyzer`` (default): deterministic, no heavy dependencies.
  Inspects basic image properties (size, dominant color, brightness)
  and returns a plausible description. Used in tests and in environments
  where torch/transformers cannot be installed.

- ``MLAnalyzer``: uses a pretrained YOLO object detector and a BLIP image
  captioner from HuggingFace. Activated when ``AI_ENABLED=true`` and the
  dependencies are importable. Falls back to the stub on import errors.
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from typing import Any

from PIL import Image

from app.config import settings
from app.ai.incident_classifier import classify_incident

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    caption: str
    scene_label: str
    detected_objects: list[dict[str, Any]] = field(default_factory=list)
    confidence_score: float = 0.0
    incident_type: str | None = None
    severity_level: str = "medium"
    model_version: str = "stub-1.0"
    raw_output: dict[str, Any] = field(default_factory=dict)

    def to_description(self) -> str:
        objs = ", ".join(o.get("label", "object") for o in self.detected_objects[:5]) or "scene elements"
        return (
            f"{self.caption.strip().rstrip('.')}. "
            f"Detected: {objs}. "
            f"Likely incident type: {self.incident_type or 'unspecified'} "
            f"(severity: {self.severity_level})."
        )


class StubAnalyzer:
    """Deterministic analyzer. No ML dependencies required."""

    model_version = "stub-1.0"

    def analyze(self, image_bytes: bytes) -> AnalysisResult:
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as exc:
            logger.warning("Could not open image: %s", exc)
            return AnalysisResult(
                caption="Unreadable image submitted.",
                scene_label="unknown",
                confidence_score=0.0,
                model_version=self.model_version,
            )

        w, h = img.size
        small = img.resize((32, 32))
        pixels = list(small.getdata())
        n = len(pixels)
        avg_r = sum(p[0] for p in pixels) / n
        avg_g = sum(p[1] for p in pixels) / n
        avg_b = sum(p[2] for p in pixels) / n
        brightness = (avg_r + avg_g + avg_b) / 3

        # Heuristic scene labels
        if avg_r > avg_g + 30 and avg_r > avg_b + 30:
            scene = "fire_or_smoke"
            objs = [{"label": "fire", "confidence": 0.62}, {"label": "smoke", "confidence": 0.58}]
            caption = "Scene appears to contain strong red/orange tones suggesting fire or smoke."
        elif brightness < 50:
            scene = "low_light_scene"
            objs = [{"label": "person", "confidence": 0.55}]
            caption = "Low-light scene with limited visibility."
        elif avg_b > avg_r + 20 and avg_b > avg_g + 10:
            scene = "outdoor_water_or_sky"
            objs = [{"label": "vehicle", "confidence": 0.5}]
            caption = "Outdoor scene with sky or water-dominant tones."
        else:
            scene = "general_scene"
            objs = [
                {"label": "person", "confidence": 0.61},
                {"label": "vehicle", "confidence": 0.45},
            ]
            caption = "General outdoor or indoor scene with people and/or vehicles."

        incident_type, severity = classify_incident(scene, objs)
        confidence = float(min(0.95, max(0.45, (max(avg_r, avg_g, avg_b) / 255) * 0.9)))

        return AnalysisResult(
            caption=caption,
            scene_label=scene,
            detected_objects=objs,
            confidence_score=confidence,
            incident_type=incident_type,
            severity_level=severity,
            model_version=self.model_version,
            raw_output={
                "image_size": [w, h],
                "avg_rgb": [round(avg_r, 2), round(avg_g, 2), round(avg_b, 2)],
                "brightness": round(brightness, 2),
            },
        )


class MLAnalyzer:
    """ML-backed analyzer using YOLO + BLIP captioning. Lazy-loaded."""

    model_version = "yolo+blip-1.0"

    def __init__(self) -> None:
        self._yolo = None
        self._blip_processor = None
        self._blip_model = None

    def _load(self) -> None:
        if self._yolo is not None:
            return
        from ultralytics import YOLO  # type: ignore
        from transformers import BlipForConditionalGeneration, BlipProcessor  # type: ignore

        logger.info("Loading YOLOv8n + BLIP captioning models...")
        self._yolo = YOLO("yolov8n.pt")
        self._blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        self._blip_model = BlipForConditionalGeneration.from_pretrained(
            "Salesforce/blip-image-captioning-base"
        )

    def analyze(self, image_bytes: bytes) -> AnalysisResult:
        try:
            self._load()
        except ImportError as exc:
            logger.warning("ML deps unavailable at analyze time, using stub: %s", exc)
            return StubAnalyzer().analyze(image_bytes)
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # Object detection
        det = self._yolo.predict(img, verbose=False)[0]  # type: ignore[union-attr]
        names = det.names
        objs = []
        for box in det.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            objs.append({"label": names[cls_id], "confidence": round(conf, 3)})

        # Captioning
        inputs = self._blip_processor(img, return_tensors="pt")  # type: ignore[union-attr]
        out = self._blip_model.generate(**inputs, max_new_tokens=40)  # type: ignore[union-attr]
        caption = self._blip_processor.decode(out[0], skip_special_tokens=True)  # type: ignore[union-attr]

        scene = objs[0]["label"] if objs else "scene"
        incident_type, severity = classify_incident(scene, objs)
        confidence = max((o["confidence"] for o in objs), default=0.5)

        return AnalysisResult(
            caption=caption,
            scene_label=scene,
            detected_objects=objs,
            confidence_score=float(confidence),
            incident_type=incident_type,
            severity_level=severity,
            model_version=self.model_version,
            raw_output={"num_detections": len(objs)},
        )


def get_analyzer():
    if not settings.AI_ENABLED:
        return StubAnalyzer()
    # Probe imports up-front so we can pick the stub if the ML stack is missing.
    try:
        import ultralytics  # noqa: F401
        import transformers  # noqa: F401
    except ImportError as exc:
        logger.warning(
            "AI_ENABLED=true but ML deps not installed (%s); using StubAnalyzer. "
            "Run: pip install -r requirements-ml.txt", exc,
        )
        return StubAnalyzer()
    return MLAnalyzer()
