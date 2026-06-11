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
INCIDENT_CLASSES: list[str] = [
    "fire",
    "traffic",
    "violent_crime",
    "vandalism",
    "suspicious_activity",
    "general",
]

# Human-readable descriptions (used in the README and in --help output).
CLASS_DESCRIPTIONS: dict[str, str] = {
    "fire": "Active fire or heavy smoke (buildings, vehicles, bush).",
    "traffic": "Road traffic accidents / collisions / damaged vehicles.",
    "violent_crime": "Weapons visible, fights, armed threat.",
    "vandalism": "Deliberate property damage, broken structures, debris.",
    "suspicious_activity": "Low-light loitering, break-in attempts, unusual gatherings.",
    "general": "Anything that is NOT a reportable incident (selfies, objects, scenery).",
}
