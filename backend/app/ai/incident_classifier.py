"""Maps detected scenes/objects (and the caption) to RNP incident categories.

The classifier combines three signals:

* the set of detected objects (people, vehicles, two-wheelers, weapons, fire …),
* the scene label, and
* keywords found in the image caption.

Crucially, it does **not** assume an emergency from mere presence. A photo
containing two cars and a pedestrian is, by default, an ordinary *traffic scene*
for an officer to verify — not a "critical collision". It is only escalated to a
collision/casualty when there is supporting evidence (caption words such as
"crash"/"injured", an accident-tagged scene, or visible damage/debris). This
avoids flagging every street photo as a critical accident while still surfacing
genuine emergencies.

``classify_incident`` returns ``(incident_type, severity_level, scenario)`` where
``scenario`` is a free-form key the description generator uses to pick a tailored
narrative template.
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


# ---------------------------------------------------------------------------
# Caption keyword signals — used to decide whether a scene is an actual
# emergency rather than an ordinary street/traffic/gathering scene.
# ---------------------------------------------------------------------------

_COLLISION_WORDS = {
    "crash", "crashed", "collision", "collided", "collide", "accident",
    "wreck", "wreckage", "wrecked", "overturned", "overturn", "rollover",
    "flipped", "smash", "smashed", "mangled", "totaled", "totalled",
    "pileup", "pile-up", "derail", "derailed",
}
_CASUALTY_WORDS = {
    "injured", "injury", "lying", "unconscious", "bleeding", "blood",
    "body", "victim", "casualty", "casualties", "trapped", "hurt",
    "wounded", "fallen", "collapsed",
}
_FIRE_WORDS = {
    "fire", "flame", "flames", "burning", "blaze", "ablaze", "wildfire",
    "bonfire",
}
_WEAPON_WORDS = {
    "gun", "guns", "pistol", "rifle", "firearm", "knife", "machete",
    "weapon", "armed", "gunman", "shooting",
}


def _caption_has(caption: str, words: set[str]) -> bool:
    if not caption:
        return False
    # Token-ish containment is fine here: captions are short and lowercase.
    return any(w in caption for w in words)


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
# Scenario -> default severity
# ---------------------------------------------------------------------------

_DEFAULT_SEVERITY: dict[str, str] = {
    "fire": "critical",
    "violent_crime": "critical",
    "traffic_accident_casualty": "critical",
    "traffic_accident": "high",
    "pedestrian_collision": "critical",
    "vehicle_collision": "high",
    # A plausible traffic scene with no evidence of a crash/casualty: report it
    # for verification at a moderate level rather than crying "critical".
    "traffic_scene": "medium",
    # A single lone vehicle a citizen flagged as unusual.
    "traffic_watch": "low",
    "theft": "high",
    "vandalism": "medium",
    "suspicious_activity": "medium",
    "crowd_disturbance": "medium",
    "general": "low",
}


# ---------------------------------------------------------------------------
# Incident-type -> (severity, narrative scenario) defaults.
# Used when our self-trained CNN supplies the incident_type directly and we
# still need a sensible severity + narrative template for it.
# ---------------------------------------------------------------------------

SEVERITY_BY_TYPE: dict[str, str] = {
    "fire": "critical",
    "traffic": "high",
    "violent_crime": "critical",
    "vandalism": "medium",
    "suspicious_activity": "medium",
    "general": "low",
}


def scenario_and_severity_for_type(
    incident_type: str, detected_objects: Iterable[dict]
) -> tuple[str, str]:
    """Pick a (severity, scenario_key) consistent with ``incident_type``.

    Detected objects (when available, e.g. from YOLO) refine the narrative —
    whether people are present changes which template reads best.
    """
    buckets = _bucket_objects(list(detected_objects or []))
    has_person = buckets["person"] > 0
    severity = SEVERITY_BY_TYPE.get(incident_type, "low")
    if incident_type == "fire":
        scenario = "fire_with_people" if has_person else "fire_only"
    elif incident_type == "violent_crime":
        scenario = "armed_with_people" if has_person else "weapon_visible"
    elif incident_type == "vandalism":
        scenario = "property_damage" if has_person else "property_damage_no_people"
    elif incident_type == "suspicious_activity":
        scenario = "suspicious_with_person" if has_person else "low_light_suspicious"
    elif incident_type == "traffic":
        scenario = "traffic_scene"
    else:
        scenario = "general"
    return severity, scenario


def classify_incident(
    scene_label: str | None,
    detected_objects: Iterable[dict],
    caption: str | None = None,
) -> tuple[str, str, str]:
    """Return (incident_type, severity_level, scenario_key).

    ``incident_type`` is the canonical category the rest of the system uses
    (fire / traffic / violent_crime / theft / suspicious_activity / vandalism /
    general). ``scenario_key`` selects the narrative template.
    """
    objects = list(detected_objects or [])
    buckets = _bucket_objects(objects)
    scene = (scene_label or "").lower()
    cap = (caption or "").lower()

    n_people = buckets["person"]
    has_person = n_people > 0
    n_vehicles = buckets["vehicle"]
    has_two_wheeler = buckets["two_wheeler"] > 0
    has_bicycle = buckets["bicycle"] > 0
    has_damage = buckets["damage"] > 0

    # Evidence that a traffic scene is actually an emergency.
    crash = _caption_has(cap, _COLLISION_WORDS) or "accident" in scene or has_damage
    casualty = _caption_has(cap, _CASUALTY_WORDS)
    serious_traffic = crash or casualty

    # ---- 1. Fire / smoke takes priority ------------------------------------
    if buckets["fire"] > 0 or scene == "fire_or_smoke" or _caption_has(cap, _FIRE_WORDS):
        scenario = "fire_with_people" if has_person else "fire_only"
        return "fire", _DEFAULT_SEVERITY["fire"], scenario

    # ---- 2. Weapons / armed threat -----------------------------------------
    if buckets["weapon"] > 0 or _caption_has(cap, _WEAPON_WORDS):
        scenario = "armed_with_people" if has_person else "weapon_visible"
        return "violent_crime", _DEFAULT_SEVERITY["violent_crime"], scenario

    # ---- 3. Confirmed traffic accidents (evidence required) ----------------
    if serious_traffic:
        # Cyclist + motor vehicle => collision involving cyclist
        if has_bicycle and (n_vehicles > 0 or has_two_wheeler):
            scenario = "cyclist_struck" if has_person else "cyclist_vehicle_collision"
            sev = "traffic_accident_casualty" if (has_person or casualty) else "traffic_accident"
            return "traffic", _DEFAULT_SEVERITY[sev], scenario

        # Motorcyclist + vehicle => collision involving motorcyclist
        if has_two_wheeler and n_vehicles > 0:
            scenario = "motorcyclist_struck" if has_person else "motorcycle_vehicle_collision"
            sev = "traffic_accident_casualty" if (has_person or casualty) else "traffic_accident"
            return "traffic", _DEFAULT_SEVERITY[sev], scenario

        # Multiple vehicles => vehicle-on-vehicle collision
        if n_vehicles >= 2:
            scenario = "vehicles_collided_with_casualty" if has_person else "vehicles_collided"
            sev = "traffic_accident_casualty" if (has_person or casualty) else "vehicle_collision"
            return "traffic", _DEFAULT_SEVERITY[sev], scenario

        # Single vehicle + person => pedestrian collision
        if n_vehicles == 1 and has_person:
            return "traffic", _DEFAULT_SEVERITY["pedestrian_collision"], "pedestrian_struck"

        # Some vehicle involved with crash evidence but no clearer pattern
        if n_vehicles >= 1 or has_two_wheeler or has_bicycle:
            return "traffic", _DEFAULT_SEVERITY["traffic_accident"], "vehicle_incident"

    # ---- 4. Crowd / gathering (people clearly dominate the scene) ----------
    if (
        n_people >= 6
        and n_people >= 4 * max(1, n_vehicles)
        and not (has_two_wheeler or has_bicycle)
    ):
        return "suspicious_activity", _DEFAULT_SEVERITY["crowd_disturbance"], "crowd_disturbance"

    # ---- 5. Ordinary traffic presence (no emergency evidence) --------------
    # Vehicles / cyclists / motorcyclists on a road, or a vehicle near people:
    # plausible but unconfirmed — report as a moderate "traffic scene".
    if (
        (has_bicycle and (n_vehicles > 0 or has_two_wheeler))
        or (has_two_wheeler and n_vehicles > 0)
        or n_vehicles >= 2
        or (n_vehicles == 1 and has_person)
    ):
        return "traffic", _DEFAULT_SEVERITY["traffic_scene"], "traffic_scene"

    # A lone vehicle / two-wheeler / bicycle the citizen flagged as unusual.
    if n_vehicles >= 1 or has_two_wheeler or has_bicycle:
        return "traffic", _DEFAULT_SEVERITY["traffic_watch"], "vehicle_present"

    # ---- 6. Low-light scene with person => suspicious activity -------------
    if scene == "low_light_scene":
        scenario = "suspicious_with_person" if has_person else "low_light_suspicious"
        return "suspicious_activity", _DEFAULT_SEVERITY["suspicious_activity"], scenario

    # ---- 7. Property damage ------------------------------------------------
    if has_damage and has_person:
        return "vandalism", _DEFAULT_SEVERITY["vandalism"], "property_damage"
    if has_damage:
        return "vandalism", _DEFAULT_SEVERITY["vandalism"], "property_damage_no_people"

    # ---- 8. General fallback -----------------------------------------------
    if has_person:
        return "general", _DEFAULT_SEVERITY["general"], "people_only"

    return "general", _DEFAULT_SEVERITY["general"], "general"
