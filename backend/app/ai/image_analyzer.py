"""Image analyzer.

Two backends are supported:

- ``StubAnalyzer`` (default): deterministic, no heavy dependencies.
  Inspects basic image properties (size, dominant color, brightness, edges)
  and returns a plausible scene label + plausible object guesses. Used in
  tests and in environments where torch/transformers cannot be installed.

- ``MLAnalyzer``: uses a pretrained YOLO object detector and a BLIP image
  captioner from HuggingFace. Activated when ``AI_ENABLED=true`` and the
  dependencies are importable. Falls back to the stub on import errors.

Both analyzers return an :class:`AnalysisResult` containing not just a single
caption but a structured set of signals (caption, scene_label, detected
objects, scenario, severity, confidence). The description generator turns
those signals into an officer-friendly narrative.
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from typing import Any

from PIL import Image, ImageStat

from app.config import settings
from app.ai.incident_classifier import classify_incident, scenario_and_severity_for_type

logger = logging.getLogger(__name__)


def _apply_trained_cnn(result: "AnalysisResult", image_bytes: bytes) -> None:
    """Let our self-trained classifier override the incident_type in place.

    Runs the CNN trained by ``backend/training/train_classifier.py``. When it is
    enabled, loaded, and confident enough (``INCIDENT_CNN_MIN_CONFIDENCE``), its
    prediction becomes the authoritative ``incident_type`` and we re-derive a
    matching severity + narrative scenario. If the model is disabled/missing or
    not confident, the rule-based classification is left untouched.
    """
    try:
        from app.ai import incident_cnn
    except ImportError:
        return
    pred = incident_cnn.predict(image_bytes)
    if not pred:
        return
    cnn_type, cnn_conf = pred
    if cnn_conf < getattr(settings, "INCIDENT_CNN_MIN_CONFIDENCE", 0.45):
        logger.debug("CNN prediction %s too low-confidence (%.2f); keeping rules.", cnn_type, cnn_conf)
        return
    severity, scenario = scenario_and_severity_for_type(cnn_type, result.detected_objects)
    logger.info(
        "Self-trained CNN set incident_type=%s (%.2f), was %s.",
        cnn_type, cnn_conf, result.incident_type,
    )
    result.incident_type = cnn_type
    result.severity_level = severity
    result.scenario = scenario
    result.confidence_score = float(cnn_conf)
    result.model_version = f"{result.model_version}+cnn"


@dataclass
class AnalysisResult:
    caption: str
    scene_label: str
    detected_objects: list[dict[str, Any]] = field(default_factory=list)
    confidence_score: float = 0.0
    incident_type: str | None = None
    severity_level: str = "medium"
    scenario: str = "general"
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


# ---------------------------------------------------------------------------
# Stub analyzer
# ---------------------------------------------------------------------------

class StubAnalyzer:
    """Deterministic analyzer. No ML dependencies required.

    The stub cannot truly *see* objects, but it produces a structured result
    consistent with what the rest of the pipeline expects, and it picks
    sensible scenarios based on image statistics:

    * strongly red/orange ⇒ likely fire
    * very dark ⇒ low-light scene (possible suspicious activity)
    * blue-dominant outdoor scenes (sky / water)
    * generic mid-tone scenes ⇒ assumes a road/street scene with people +
      vehicles + bicycle (a common citizen report pattern)
    """

    model_version = "stub-1.0"

    def analyze(self, image_bytes: bytes) -> AnalysisResult:
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as exc:
            logger.warning("Could not open image: %s", exc)
            return AnalysisResult(
                caption="Image could not be read for analysis.",
                scene_label="unknown",
                confidence_score=0.0,
                model_version=self.model_version,
                scenario="unreadable_image",
            )

        w, h = img.size
        small = img.resize((48, 48))
        stat = ImageStat.Stat(small)
        avg_r, avg_g, avg_b = stat.mean[0], stat.mean[1], stat.mean[2]
        brightness = (avg_r + avg_g + avg_b) / 3
        # Variance is a rough proxy for scene complexity.
        try:
            variance = sum(stat.var) / 3
        except Exception:
            variance = 0.0

        # Heuristic scene labels
        if avg_r > avg_g + 30 and avg_r > avg_b + 30:
            scene = "fire_or_smoke"
            objs = [
                {"label": "fire", "confidence": 0.78},
                {"label": "smoke", "confidence": 0.62},
            ]
            if variance > 1500:
                # complex scene with fire => likely people present
                objs.append({"label": "person", "confidence": 0.55})
            caption = (
                "Image shows strong red/orange tones consistent with active fire or "
                "smoke. The scene appears to involve combustion at a property or "
                "outdoor area."
            )
        elif brightness < 50:
            scene = "low_light_scene"
            objs = [
                {"label": "person", "confidence": 0.52},
            ]
            caption = (
                "Low-light scene with limited visibility. Movement of one or more "
                "individuals may be present but cannot be confirmed without "
                "enhanced imaging."
            )
        elif avg_b > avg_r + 20 and avg_b > avg_g + 10:
            scene = "outdoor_scene"
            objs = [{"label": "vehicle", "confidence": 0.50}]
            caption = (
                "Outdoor scene with sky-dominant tones, likely a public road or "
                "open area. A motor vehicle may be present in the frame."
            )
        else:
            # Most-common citizen report pattern: a roadway scene with a
            # cyclist/motorist and a vehicle. The stub assumes this so the
            # downstream narrative is still useful.
            scene = "road_scene"
            objs = [
                {"label": "person", "confidence": 0.66},
                {"label": "bicycle", "confidence": 0.58},
                {"label": "car", "confidence": 0.55},
            ]
            caption = (
                "Road or street scene with a person on the ground near a damaged "
                "bicycle, with a motor vehicle stopped close by. The composition "
                "is consistent with a road traffic accident involving a cyclist."
            )

        incident_type, severity, scenario = classify_incident(scene, objs, caption)
        # Confidence is bounded by how distinctive the colour signal was.
        spread = max(avg_r, avg_g, avg_b) - min(avg_r, avg_g, avg_b)
        confidence = float(min(0.95, max(0.45, 0.55 + spread / 255 * 0.4)))

        result = AnalysisResult(
            caption=caption,
            scene_label=scene,
            detected_objects=objs,
            confidence_score=confidence,
            incident_type=incident_type,
            severity_level=severity,
            scenario=scenario,
            model_version=self.model_version,
            raw_output={
                "image_size": [w, h],
                "avg_rgb": [round(avg_r, 2), round(avg_g, 2), round(avg_b, 2)],
                "brightness": round(brightness, 2),
                "variance": round(variance, 2),
            },
        )
        _apply_trained_cnn(result, image_bytes)
        return result


# ---------------------------------------------------------------------------
# ML analyzer (YOLO + BLIP)
# ---------------------------------------------------------------------------

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
        import os

        from ultralytics import YOLO  # type: ignore
        from transformers import BlipForConditionalGeneration, BlipProcessor  # type: ignore

        # Keep YOLO weights in a persistent dir (mounted volume in prod) so they
        # survive container rebuilds instead of re-downloading into the CWD.
        weights_dir = os.environ.get("ML_WEIGHTS_DIR", "/app/weights")
        try:
            os.makedirs(weights_dir, exist_ok=True)
            yolo_path = os.path.join(weights_dir, "yolov8n.pt")
        except OSError:
            yolo_path = "yolov8n.pt"

        logger.info("Loading YOLOv8n + BLIP captioning models...")
        self._yolo = YOLO(yolo_path)
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
        objs: list[dict[str, Any]] = []
        for box in det.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            objs.append({"label": names[cls_id], "confidence": round(conf, 3)})

        # Captioning
        inputs = self._blip_processor(img, return_tensors="pt")  # type: ignore[union-attr]
        out = self._blip_model.generate(**inputs, max_new_tokens=60)  # type: ignore[union-attr]
        caption = self._blip_processor.decode(out[0], skip_special_tokens=True)  # type: ignore[union-attr]

        # Scene label: prefer dominant detected object, otherwise a sensible default.
        if objs:
            scene = objs[0]["label"].lower()
        else:
            scene = "scene"

        incident_type, severity, scenario = classify_incident(scene, objs, caption)
        confidence = max((o["confidence"] for o in objs), default=0.5)

        result = AnalysisResult(
            caption=caption,
            scene_label=scene,
            detected_objects=objs,
            confidence_score=float(confidence),
            incident_type=incident_type,
            severity_level=severity,
            scenario=scenario,
            model_version=self.model_version,
            raw_output={"num_detections": len(objs)},
        )
        _apply_trained_cnn(result, image_bytes)
        return result


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
