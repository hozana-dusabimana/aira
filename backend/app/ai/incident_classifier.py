"""Maps detected scenes/objects to RNP incident categories and severity.

The classifier looks at *combinations* of objects in the image, not just a
single label. This is critical for scenarios like a cyclist hit by a car
(person + bicycle + car -> traffic accident with casualty) which would
otherwise be misclassified as "general".

The ``classify_incident`` function returns a tuple of
``(incident_type, severity_level, scenario)`` where ``scenario`` is a free-form
key the description generator uses to pick a tailored narrative template.
"""
from __future__ import annotations

from typing import Iterable

# ---------------------------------------------------------------------------
# Label groups — we map raw detector labels into broader semantic buckets so
# the rules below can reason at a higher level than YOLO/COCO categories.
# ---------------------------------------------------------------------------

VEHICLE_LABELS = {
    "car", "truck", "van", "bus", "vehicle", "automobile", "pickup",
}
TWO_WHEELER_LABELS = {"motorcycle", "motorbike", "scooter"}
BICYCLE_LABELS = {"bicycle", "bike"}
WEAPON_LABELS = {"gun", "pistol", "rifle", "firearm", "weapon", "knife", "blade"}
FIRE_LABELS = {"fire", "smoke", "flame"}
PERSON_LABELS = {"person", "people", "pedestrian", "human"}
DAMAGE_LABELS = {"debris", "broken_glass", "wreckage", "rubble"}


def _bucket_objects(objects: Iterable[dict]) -> dict[str, int]:
    """Return counts of each semantic bucket present in the image."""
    counts: dict[str, int] = {
        "person": 0,
        "vehicle": 0,
        "two_wheeler": 0,
        "bicycle": 0,
        "weapon": 0,
        "fire": 0,
        "damage": 0,
    }
    for o in objects:
        label = str(o.get("label", "")).lower().strip()
        if label in PERSON_LABELS:
            counts["person"] += 1
        elif label in VEHICLE_LABELS:
            counts["vehicle"] += 1
        elif label in TWO_WHEELER_LABELS:
            counts["two_wheeler"] += 1
        elif label in BICYCLE_LABELS:
            counts["bicycle"] += 1
        elif label in WEAPON_LABELS:
            counts["weapon"] += 1
        elif label in FIRE_LABELS:
            counts["fire"] += 1
        elif label in DAMAGE_LABELS:
            counts["damage"] += 1
    return counts


# ---------------------------------------------------------------------------
# Incident type -> default severity
# ---------------------------------------------------------------------------

_DEFAULT_SEVERITY: dict[str, str] = {
    "fire": "critical",
    "violent_crime": "critical",
    "traffic_accident_casualty": "critical",
    "traffic_accident": "high",
    "pedestrian_collision": "critical",
    "vehicle_collision": "high",
    "traffic": "high",
    "theft": "high",
    "vandalism": "medium",
    "suspicious_activity": "medium",
    "crowd_disturbance": "medium",
    "general": "low",
}


def classify_incident(
    scene_label: str | None,
    detected_objects: Iterable[dict],
) -> tuple[str, str, str]:
    """Return (incident_type, severity_level, scenario_key).

    ``incident_type`` is the canonical category the rest of the system uses
    (fire / traffic / violent_crime / theft / suspicious_activity / general).

    ``scenario_key`` is a finer-grained label (``cyclist_struck``,
    ``vehicles_collided``, ``armed_threat`` ...) that the description
    generator uses to pick a precise narrative template.
    """
    objects = list(detected_objects or [])
    buckets = _bucket_objects(objects)
    scene = (scene_label or "").lower()

    # ---- 1. Fire / smoke takes priority ------------------------------------
    if buckets["fire"] > 0 or scene == "fire_or_smoke":
        scenario = "fire_with_people" if buckets["person"] > 0 else "fire_only"
        return "fire", _DEFAULT_SEVERITY["fire"], scenario

    # ---- 2. Weapons / armed threat -----------------------------------------
    if buckets["weapon"] > 0:
        scenario = "armed_with_people" if buckets["person"] > 0 else "weapon_visible"
        return "violent_crime", _DEFAULT_SEVERITY["violent_crime"], scenario

    # ---- 3. Traffic incidents ----------------------------------------------
    has_person = buckets["person"] > 0
    n_vehicles = buckets["vehicle"]
    has_two_wheeler = buckets["two_wheeler"] > 0
    has_bicycle = buckets["bicycle"] > 0

    # Cyclist + motor vehicle => collision involving cyclist
    if has_bicycle and (n_vehicles > 0 or has_two_wheeler):
        scenario = "cyclist_struck" if has_person else "cyclist_vehicle_collision"
        sev = "traffic_accident_casualty" if has_person else "traffic_accident"
        return "traffic", _DEFAULT_SEVERITY[sev], scenario

    # Motorcyclist + vehicle => collision involving motorcyclist
    if has_two_wheeler and n_vehicles > 0:
        scenario = "motorcyclist_struck" if has_person else "motorcycle_vehicle_collision"
        sev = "traffic_accident_casualty" if has_person else "traffic_accident"
        return "traffic", _DEFAULT_SEVERITY[sev], scenario

    # Multiple vehicles, no two-wheelers => vehicle-on-vehicle collision
    if n_vehicles >= 2:
        scenario = "vehicles_collided_with_casualty" if has_person else "vehicles_collided"
        sev = "traffic_accident_casualty" if has_person else "vehicle_collision"
        return "traffic", _DEFAULT_SEVERITY[sev], scenario

    # Single vehicle + person on the road => pedestrian collision
    if n_vehicles == 1 and has_person:
        return "traffic", _DEFAULT_SEVERITY["pedestrian_collision"], "pedestrian_struck"

    # Lone vehicle in scene tagged as accident-like
    if n_vehicles >= 1 and "accident" in scene:
        return "traffic", _DEFAULT_SEVERITY["traffic_accident"], "vehicle_incident"

    # Bicycle alone after an apparent fall
    if has_bicycle and has_person:
        return "traffic", _DEFAULT_SEVERITY["traffic_accident"], "cyclist_fallen"

    # Lone vehicle => generic traffic concern
    if n_vehicles >= 1 or has_two_wheeler:
        return "traffic", _DEFAULT_SEVERITY["traffic"], "vehicle_present"

    # ---- 4. Crowd / disturbance --------------------------------------------
    if buckets["person"] >= 4:
        return "suspicious_activity", _DEFAULT_SEVERITY["crowd_disturbance"], "crowd_disturbance"

    # ---- 5. Low-light scene with person => suspicious activity -------------
    if scene == "low_light_scene":
        scenario = "suspicious_with_person" if has_person else "low_light_suspicious"
        return "suspicious_activity", _DEFAULT_SEVERITY["suspicious_activity"], scenario

    # ---- 6. General fallback -----------------------------------------------
    if has_person and buckets["damage"] > 0:
        return "vandalism", _DEFAULT_SEVERITY["vandalism"], "property_damage"

    if buckets["damage"] > 0:
        return "vandalism", _DEFAULT_SEVERITY["vandalism"], "property_damage_no_people"

    if has_person:
        return "general", _DEFAULT_SEVERITY["general"], "people_only"

    return "general", _DEFAULT_SEVERITY["general"], "general"
