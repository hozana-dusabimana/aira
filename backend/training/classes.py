"""Canonical incident classes for the AIRA image classifier.

These MUST match the ``incident_type`` values used elsewhere in the backend
(see ``app/ai/incident_classifier.py``) so the trained model's predictions
plug straight into the rest of the system.

The order here defines the integer label index used during training and at
inference time. ``labels.json`` written by ``train_classifier.py`` is the
authoritative mapping for a given trained checkpoint; this list is only the
default/expected ordering.
"""
from __future__ import annotations

# One folder per class under the dataset root.
#
# Simplified 3-class model: the two incident types with clean, real public
# datasets (fire, accident) plus a "normal" negative class so the model can
# recognise a non-incident. The class names map to the backend's incident_type
# vocabulary as: accident -> traffic, normal -> general, fire -> fire
# (see CNN_CLASS_TO_INCIDENT_TYPE in app/ai/image_analyzer.py).
INCIDENT_CLASSES: list[str] = [
    "fire",
    "accident",
    "normal",
]

# Human-readable descriptions (used in the README and in --help output).
CLASS_DESCRIPTIONS: dict[str, str] = {
    "fire": "Active fire or heavy smoke (buildings, vehicles, bush).",
    "accident": "Road traffic accidents / vehicle collisions / crash scenes.",
    "normal": "Anything that is NOT a reportable incident (ordinary scenes, scenery, traffic).",
}
