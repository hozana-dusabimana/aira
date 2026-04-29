"""Maps detected scenes/objects to RNP incident categories and severity."""
from __future__ import annotations

from typing import Iterable


# Object label -> incident type
_OBJECT_TO_INCIDENT: dict[str, str] = {
    "fire": "fire",
    "smoke": "fire",
    "knife": "violent_crime",
    "gun": "violent_crime",
    "person": "general",
    "vehicle": "traffic",
    "car": "traffic",
    "truck": "traffic",
    "motorcycle": "traffic",
    "bicycle": "traffic",
    "bus": "traffic",
}

_SCENE_TO_INCIDENT: dict[str, str] = {
    "fire_or_smoke": "fire",
    "outdoor_water_or_sky": "general",
    "low_light_scene": "suspicious_activity",
    "general_scene": "general",
}

# Incident type -> default severity
_DEFAULT_SEVERITY: dict[str, str] = {
    "fire": "critical",
    "violent_crime": "critical",
    "traffic": "high",
    "theft": "high",
    "vandalism": "medium",
    "suspicious_activity": "medium",
    "general": "low",
}


def classify_incident(
    scene_label: str | None,
    detected_objects: Iterable[dict],
) -> tuple[str, str]:
    """Return (incident_type, severity_level) using a simple priority-based map."""
    incident_type: str | None = None

    # 1) High-priority object hits win first.
    object_priority = ["fire", "smoke", "gun", "knife"]
    objs_by_label = {o.get("label", "").lower(): o for o in detected_objects}
    for label in object_priority:
        if label in objs_by_label:
            incident_type = _OBJECT_TO_INCIDENT.get(label, "general")
            break

    # 2) Otherwise use scene classification.
    if incident_type is None and scene_label:
        incident_type = _SCENE_TO_INCIDENT.get(scene_label.lower())

    # 3) Otherwise infer from the most common detected category.
    if incident_type is None:
        for label, _ in objs_by_label.items():
            if label in _OBJECT_TO_INCIDENT:
                incident_type = _OBJECT_TO_INCIDENT[label]
                break

    incident_type = incident_type or "general"
    severity = _DEFAULT_SEVERITY.get(incident_type, "medium")
    return incident_type, severity
