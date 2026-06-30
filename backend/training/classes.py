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
# Two-class, ROAD-ACCIDENT-ONLY model: the app reports road accidents, so the
# model only needs to tell an accident apart from everything else. ``normal`` is
# the negative class for all non-accident photos (ordinary scenes, intact
# vehicles, fire, etc.) and is rejected. Class -> incident_type mapping:
# accident -> traffic, normal -> general (see CNN_CLASS_TO_INCIDENT_TYPE in
# app/ai/image_analyzer.py).
INCIDENT_CLASSES: list[str] = [
    "accident",
    "normal",
]

# Human-readable descriptions (used in the README and in --help output).
CLASS_DESCRIPTIONS: dict[str, str] = {
    "accident": "Road traffic accidents / vehicle collisions / crash scenes.",
    "normal": "Anything that is NOT a road accident (ordinary scenes, intact vehicles, fire, etc.) — rejected.",
}
