"""Generates officer-friendly multi-paragraph incident summaries.

The summary is produced *purely* from the AI image-analysis output; it does
not depend on (and does not include) any citizen-supplied description. The
goal is that an officer can read this report alone and understand:

* what happened,
* what is visible at the scene,
* the likely cause and risk,
* the recommended immediate response, and
* why the report is being made.

For each scenario detected by ``classify_incident`` we emit a tailored
multi-paragraph template; common closing paragraphs (severity assessment,
recommended actions, technical appendix) are appended uniformly.
"""
from __future__ import annotations

from typing import Iterable

from app.ai.image_analyzer import AnalysisResult


# ---------------------------------------------------------------------------
# Object grouping helpers
# ---------------------------------------------------------------------------

def _group_objects(objects: Iterable[dict]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {
        "people": [],
        "vehicles": [],
        "two_wheelers": [],
        "bicycles": [],
        "weapons": [],
        "fire": [],
        "other": [],
    }
    vehicle_set = {"car", "truck", "van", "bus", "vehicle", "automobile", "pickup"}
    two_wheeler_set = {"motorcycle", "motorbike", "scooter"}
    bike_set = {"bicycle", "bike"}
    weapon_set = {"gun", "pistol", "rifle", "firearm", "weapon", "knife", "blade"}
    fire_set = {"fire", "smoke", "flame"}
    person_set = {"person", "people", "pedestrian", "human"}

    for o in objects:
        label = str(o.get("label", "")).lower().strip()
        if not label:
            continue
        if label in person_set:
            groups["people"].append(label)
        elif label in vehicle_set:
            groups["vehicles"].append(label)
        elif label in two_wheeler_set:
            groups["two_wheelers"].append(label)
        elif label in bike_set:
            groups["bicycles"].append(label)
        elif label in weapon_set:
            groups["weapons"].append(label)
        elif label in fire_set:
            groups["fire"].append(label)
        else:
            groups["other"].append(label)
    return groups


def _people_phrase(n: int) -> str:
    if n == 0:
        return "no people"
    if n == 1:
        return "one person"
    if n <= 5:
        return f"{n} people"
    return "several people"


def _vehicle_phrase(vehicles: list[str]) -> str:
    if not vehicles:
        return "no motor vehicles"
    counts: dict[str, int] = {}
    for v in vehicles:
        counts[v] = counts.get(v, 0) + 1
    parts = []
    for label, count in counts.items():
        if count == 1:
            parts.append(f"a {label}")
        else:
            parts.append(f"{count} {label}s")
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + f" and {parts[-1]}"


# ---------------------------------------------------------------------------
# Per-scenario narrative templates — each returns a list of paragraphs
# ---------------------------------------------------------------------------

def _narrative_cyclist_struck(g: dict[str, list[str]]) -> list[str]:
    veh = _vehicle_phrase(g["vehicles"]) if g["vehicles"] else "a small motor vehicle"
    return [
        (
            "A road traffic accident has occurred involving a cyclist and "
            f"{veh} on a public road. Based on the position of the persons "
            "and the bicycle visible in the image, contact appears to have "
            "taken place between the bicycle and the vehicle, causing the "
            "cyclist to fall onto the roadway."
        ),
        (
            "The cyclist is visible lying on the ground close to the damaged "
            "bicycle, while the motor vehicle has come to a stop near the "
            "point of impact. This positioning indicates the collision "
            "occurred within a short distance and that the cyclist may be "
            "injured and unable to move unaided."
        ),
        (
            "Possible contributing factors include failure to maintain proper "
            "attention, unsafe road positioning by either party, misjudgment "
            "while turning or crossing, or insufficient safe distance between "
            "the motor vehicle and the cyclist."
        ),
        (
            "The scene presents an immediate risk: the casualty needs urgent "
            "medical attention, and the obstruction on the carriageway "
            "endangers other road users. The area must be secured and the "
            "scene preserved for investigation."
        ),
    ]


def _narrative_motorcyclist_struck(g: dict[str, list[str]]) -> list[str]:
    veh = _vehicle_phrase(g["vehicles"]) if g["vehicles"] else "a motor vehicle"
    return [
        (
            "A road traffic accident has occurred involving a motorcyclist and "
            f"{veh} on a public road. The image shows the motorcycle and the "
            "motor vehicle in close proximity in a configuration consistent "
            "with a collision."
        ),
        (
            "A person, likely the rider, is visible at or near the scene, "
            "indicating possible injury. The motorcycle appears to have been "
            "displaced from its travel position, and the motor vehicle has "
            "stopped near the point of impact."
        ),
        (
            "Likely causes include sudden braking, lane intrusion, blind-spot "
            "movement by either party, or excessive speed for the prevailing "
            "road conditions."
        ),
        (
            "Immediate risks include life-threatening injuries to the rider, "
            "leaking fuel, and obstruction of traffic. The scene requires "
            "rapid medical response and traffic management."
        ),
    ]


def _narrative_pedestrian_struck(g: dict[str, list[str]]) -> list[str]:
    veh = _vehicle_phrase(g["vehicles"]) if g["vehicles"] else "a motor vehicle"
    return [
        (
            "A pedestrian collision has been reported. The image shows "
            f"{veh} in close proximity to a person on the roadway, in a "
            "configuration consistent with the person having been struck."
        ),
        (
            "The pedestrian appears to be at or near ground level beside the "
            "vehicle, suggesting the impact has caused them to fall. The "
            "vehicle has stopped close to the point of impact, indicating a "
            "low-speed or short-distance collision but with a real risk of "
            "injury."
        ),
        (
            "Common causes of incidents of this kind include the driver "
            "failing to give way at a crossing, the pedestrian crossing "
            "outside a marked area, or the driver being inattentive or "
            "exceeding a safe speed."
        ),
        (
            "The casualty likely needs urgent medical assistance. The scene "
            "must be secured to prevent secondary collisions while the "
            "investigation is carried out."
        ),
    ]


def _narrative_vehicles_collided(g: dict[str, list[str]], with_casualty: bool) -> list[str]:
    veh = _vehicle_phrase(g["vehicles"]) if g["vehicles"] else "two motor vehicles"
    casualty_p = (
        "Persons are visible at the scene, indicating possible injuries that "
        "require immediate medical assessment."
        if with_casualty
        else
        "No casualties are clearly visible in the image, but the possibility "
        "of injury inside one or more of the vehicles cannot be ruled out."
    )
    return [
        (
            f"A vehicle-on-vehicle collision has been reported, involving {veh}. "
            "The vehicles are stopped close together in a configuration "
            "consistent with a recent impact, and visible damage on at least "
            "one vehicle supports this assessment."
        ),
        casualty_p,
        (
            "Likely causes include rear-end impact due to insufficient stopping "
            "distance, failure to give way at an intersection, lane "
            "intrusion, or impaired or distracted driving."
        ),
        (
            "The wreckage may be obstructing the carriageway and creating a "
            "hazard for other road users. Police presence is required to "
            "manage traffic, document the scene and request medical and "
            "recovery services as needed."
        ),
    ]


def _narrative_fire(g: dict[str, list[str]], people_present: bool) -> list[str]:
    paras = [
        (
            "A fire-related incident has been reported. Visual analysis "
            "detects strong indicators of active fire and/or smoke at the "
            "scene, suggesting an ongoing combustion event at a property or "
            "outdoor area."
        ),
        (
            "The fire poses an immediate and rapidly evolving risk to life, "
            "to surrounding property and to the local environment. Smoke "
            "inhalation, structural collapse and the spread of fire to "
            "adjacent buildings or vegetation are all probable hazards."
        ),
    ]
    if people_present:
        paras.append(
            "People are visible in or near the affected area, raising the "
            "likelihood of casualties from burns, smoke inhalation or "
            "trapped occupants. Search and rescue must be considered "
            "urgently."
        )
    paras.append(
        "Likely causes range widely (electrical fault, unattended cooking, "
        "arson, vehicle fire, or industrial accident) and cannot be "
        "determined from the image alone — the priority is containment "
        "before investigation."
    )
    return paras


def _narrative_armed(g: dict[str, list[str]], with_people: bool) -> list[str]:
    weapons_n = len(g["weapons"]) or 1
    weapon_word = "a weapon" if weapons_n == 1 else "weapons"
    paras = [
        (
            f"A potentially violent incident has been reported. The image "
            f"shows {weapon_word} present at the scene, which raises the "
            "possibility of an active armed threat."
        ),
    ]
    if with_people:
        paras.append(
            "Civilians are visible in the same frame as the weapon(s), "
            "indicating they may be at immediate risk. There is a serious "
            "possibility of physical harm or hostage situation."
        )
    else:
        paras.append(
            "While no civilians are clearly identified in the frame, the "
            "presence of weapons in a public setting is itself a serious "
            "public-safety concern that must not be left unaddressed."
        )
    paras.append(
        "Possible context includes an ongoing robbery or assault, a "
        "domestic dispute that has escalated, or an exchange of force "
        "between civilians. Officers should approach with caution and "
        "treat the scene as armed until proven otherwise."
    )
    return paras


def _narrative_crowd(g: dict[str, list[str]]) -> list[str]:
    return [
        (
            "A crowd-related incident has been reported. The image shows "
            f"{_people_phrase(len(g['people']))} gathered in a relatively "
            "confined area, which may indicate a public disturbance, an "
            "unauthorised gathering or a developing safety concern."
        ),
        (
            "Such gatherings can escalate quickly into pushing, fighting or "
            "stampedes, particularly in narrow streets, near transport "
            "hubs or around political events."
        ),
        (
            "A patrol unit should attend to assess the mood of the crowd, "
            "identify any aggressors, ensure free passage for non-"
            "participants and request reinforcements if escalation appears "
            "likely."
        ),
    ]


def _narrative_low_light(g: dict[str, list[str]], with_person: bool) -> list[str]:
    if with_person:
        return [
            (
                "A report has been submitted from a low-light scene. The "
                "image shows limited visibility but the silhouette of one "
                "or more individuals can be made out, suggesting movement "
                "in the area at a time when normal activity should be "
                "minimal."
            ),
            (
                "Low-light scenes commonly indicate after-hours suspicious "
                "activity such as loitering, attempted entry into "
                "premises, or pre-attack reconnaissance."
            ),
            (
                "A patrol unit should verify the situation on the ground "
                "and confirm whether the activity is legitimate or "
                "warrants further investigation."
            ),
        ]
    return [
        (
            "A report has been submitted from a low-light scene with no "
            "clearly identifiable subjects. The conditions limit what can "
            "be inferred from the imagery alone."
        ),
        (
            "Patrol attendance is recommended to verify whether suspicious "
            "activity is taking place that the camera was unable to "
            "capture clearly."
        ),
    ]


def _narrative_property_damage(g: dict[str, list[str]], with_people: bool) -> list[str]:
    return [
        (
            "An act of vandalism or property damage has been reported. The "
            "image shows visible damage to objects or structures at the "
            "scene which is consistent with deliberate or reckless "
            "interference rather than ordinary wear."
        ),
        (
            "Persons are present in the frame and may be associated with "
            "the act, the affected premises or simply bystanders."
            if with_people
            else
            "No persons are visible in the frame; this may indicate the "
            "perpetrators have left the scene."
        ),
        (
            "The damage should be documented before any clean-up so that an "
            "investigation can identify suspects, recover any property "
            "stolen during the incident and pursue restitution."
        ),
    ]


def _narrative_model_accident(g: dict[str, list[str]]) -> list[str]:
    """Concise narrative for an accident the trained detector is confident about.

    Kept deliberately short and consistent with the 'traffic' label — it does
    NOT hedge with 'no vehicles / no clear collision' the way the generic
    traffic-scene template does.
    """
    # NB: _vehicle_phrase([]) returns the literal "no motor vehicles" (truthy),
    # so guard on the list — when the detector found no vehicles we still assert
    # a collision (the trained model says so), just generically.
    subj = _vehicle_phrase(g["vehicles"]) if g["vehicles"] else "one or more vehicles"
    people = f" {_people_phrase(len(g['people']))} may be involved or nearby." if g["people"] else ""
    return [
        f"AI analysis indicates a road traffic accident — a collision involving "
        f"{subj} with visible damage.{people}"
    ]


def _narrative_traffic_scene(g: dict[str, list[str]]) -> list[str]:
    """A road scene with vehicles/cyclists but no clear evidence of a crash."""
    if g["bicycles"]:
        parties = "a cyclist and " + (_vehicle_phrase(g["vehicles"]) or "a motor vehicle")
    elif g["two_wheelers"]:
        parties = "a motorcyclist and " + (_vehicle_phrase(g["vehicles"]) or "a motor vehicle")
    else:
        parties = _vehicle_phrase(g["vehicles"]) or "one or more vehicles"
    people_clause = (
        f", with {_people_phrase(len(g['people']))} in the vicinity"
        if g["people"]
        else ""
    )
    return [
        (
            f"A traffic scene has been reported involving {parties}{people_clause}. "
            "The image shows road users on or beside the carriageway, but the "
            "available visual evidence does not clearly indicate a collision, "
            "injury, or significant damage."
        ),
        (
            "This may be ordinary traffic, a stopped or obstructing vehicle, a "
            "near-miss, or the early or aftermath stage of an incident that is "
            "not obvious from the photograph alone. It is being filed for an "
            "officer to verify on the ground rather than treated as a confirmed "
            "emergency."
        ),
        (
            "Officers should attend to confirm whether any vehicle is damaged, "
            "anyone is injured, or the carriageway is obstructed, and escalate "
            "the response if a collision or casualty is confirmed."
        ),
    ]


def _narrative_general(g: dict[str, list[str]]) -> list[str]:
    detected = []
    if g["people"]:
        detected.append(_people_phrase(len(g["people"])))
    if g["vehicles"]:
        detected.append(_vehicle_phrase(g["vehicles"]))
    if g["other"]:
        detected.append(", ".join(sorted(set(g["other"]))[:5]))
    detected_str = "; ".join(detected) if detected else "no clearly identifiable subjects"
    return [
        (
            "A citizen has submitted an incident report. Visual analysis of "
            f"the photograph identifies: {detected_str}. The combination of "
            "elements does not fit a high-confidence incident category, but "
            "the image was considered worth reporting by the citizen and "
            "therefore warrants verification."
        ),
        (
            "Officers should attend to assess the scene on the ground and "
            "determine whether further police action, medical assistance "
            "or referral to another service is required."
        ),
    ]


# ---------------------------------------------------------------------------
# Common closing paragraphs
# ---------------------------------------------------------------------------

def _severity_paragraph(severity: str) -> str:
    return {
        "low": (
            "Severity assessment: low — the scene does not appear to involve "
            "an immediate risk to life or property, but should still be "
            "verified."
        ),
        "medium": (
            "Severity assessment: medium — the scene presents a moderate "
            "level of risk and warrants timely police attention."
        ),
        "high": (
            "Severity assessment: high — the scene presents a serious "
            "situation that requires prompt police response and on-site "
            "verification."
        ),
        "critical": (
            "Severity assessment: critical — the scene presents a life-"
            "threatening situation that requires immediate emergency "
            "response."
        ),
    }.get(severity, "Severity assessment: could not be confidently estimated.")


def _action_paragraph(incident_type: str | None, scenario: str) -> str:
    if incident_type == "fire":
        return (
            "Recommended immediate actions: dispatch fire and rescue "
            "services, secure a safe perimeter, evacuate nearby civilians, "
            "and request medical support in case of burns or smoke "
            "inhalation."
        )
    if incident_type == "traffic":
        if "casualty" in scenario or scenario in {
            "cyclist_struck", "motorcyclist_struck", "pedestrian_struck",
            "vehicles_collided_with_casualty",
        }:
            return (
                "Recommended immediate actions: dispatch a traffic patrol "
                "and an ambulance to the scene, divert oncoming traffic, "
                "preserve the wreckage for accident reconstruction and take "
                "witness statements."
            )
        return (
            "Recommended immediate actions: dispatch a traffic patrol unit "
            "to manage the carriageway, document the damage and assess "
            "whether recovery services are required."
        )
    if incident_type == "violent_crime":
        return (
            "Recommended immediate actions: dispatch armed response, secure "
            "the perimeter, identify victims and suspects from the imagery, "
            "and request emergency medical services if injuries are "
            "suspected."
        )
    if incident_type == "vandalism":
        return (
            "Recommended immediate actions: send a patrol to document the "
            "damage, preserve any evidence (broken glass, footprints, "
            "tools), and gather witness statements before clean-up."
        )
    if incident_type == "suspicious_activity":
        return (
            "Recommended immediate actions: send a patrol unit to verify "
            "the situation on the ground and continue monitoring for "
            "escalation."
        )
    return (
        "Recommended immediate actions: dispatch the nearest patrol unit to "
        "verify the report on site and assist any persons present."
    )


def _appendix(result: AnalysisResult) -> str:
    bits: list[str] = []
    if result.scene_label:
        bits.append(f"scene: {result.scene_label}")
    bits.append(f"type: {result.incident_type or 'general'}")
    bits.append(f"severity: {result.severity_level}")
    bits.append(
        f"AI confidence: {round((result.confidence_score or 0) * 100)}%"
    )
    if result.detected_objects:
        objs = ", ".join(
            f"{o.get('label', 'object')} ({int(round(o.get('confidence', 0) * 100))}%)"
            for o in result.detected_objects[:6]
        )
        bits.append(f"detections: {objs}")
    bits.append(f"model: {result.model_version}")
    return "AI analysis details — " + "; ".join(bits) + "."


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------

def generate_description(
    result: AnalysisResult,
    user_description: str | None = None,  # accepted for backwards compat, ignored
) -> str:
    """Return an officer-ready, multi-paragraph incident summary.

    The summary is generated entirely from the AI image-analysis result; any
    citizen-supplied description is intentionally NOT included so the AI
    summary stands alone as an objective view of what the model saw.
    """
    del user_description  # documented as ignored; kept for API compatibility
    g = _group_objects(result.detected_objects or [])
    scenario = result.scenario or "general"

    if scenario == "fire_with_people":
        paragraphs = _narrative_fire(g, people_present=True)
    elif scenario == "fire_only":
        paragraphs = _narrative_fire(g, people_present=False)
    elif scenario == "armed_with_people":
        paragraphs = _narrative_armed(g, with_people=True)
    elif scenario == "weapon_visible":
        paragraphs = _narrative_armed(g, with_people=False)
    elif scenario in {"cyclist_struck", "cyclist_vehicle_collision", "cyclist_fallen"}:
        paragraphs = _narrative_cyclist_struck(g)
    elif scenario in {"motorcyclist_struck", "motorcycle_vehicle_collision"}:
        paragraphs = _narrative_motorcyclist_struck(g)
    elif scenario == "pedestrian_struck":
        paragraphs = _narrative_pedestrian_struck(g)
    elif scenario == "vehicles_collided_with_casualty":
        paragraphs = _narrative_vehicles_collided(g, with_casualty=True)
    elif scenario in {"vehicles_collided", "vehicle_incident"}:
        paragraphs = _narrative_vehicles_collided(g, with_casualty=False)
    elif scenario == "crowd_disturbance":
        paragraphs = _narrative_crowd(g)
    elif scenario == "suspicious_with_person":
        paragraphs = _narrative_low_light(g, with_person=True)
    elif scenario == "low_light_suspicious":
        paragraphs = _narrative_low_light(g, with_person=False)
    elif scenario == "property_damage":
        paragraphs = _narrative_property_damage(g, with_people=True)
    elif scenario == "property_damage_no_people":
        paragraphs = _narrative_property_damage(g, with_people=False)
    elif scenario == "model_confirmed_accident":
        paragraphs = _narrative_model_accident(g)
    elif scenario == "traffic_scene":
        paragraphs = _narrative_traffic_scene(g)
    elif scenario == "vehicle_present":
        paragraphs = [
            (
                "A traffic-related concern has been reported. The image "
                f"shows {_vehicle_phrase(g['vehicles']) or 'a motor vehicle'} "
                "in a position that the citizen has judged unusual or "
                "unsafe."
            ),
            (
                "Possible explanations range from a stopped or abandoned "
                "vehicle, an obstructed lane, or behaviour suggestive of "
                "an offence. Patrol verification is recommended."
            ),
        ]
    else:
        paragraphs = _narrative_general(g)

    paragraphs.append(_severity_paragraph(result.severity_level))
    paragraphs.append(_action_paragraph(result.incident_type, scenario))
    paragraphs.append(_appendix(result))

    return "\n\n".join(paragraphs)
