from tests.conftest import make_test_image_bytes


def test_analyze_image_endpoint(client, citizen_token):
    files = {"image": ("t.jpg", make_test_image_bytes(), "image/jpeg")}
    r = client.post(
        "/api/v1/ai/analyze-image",
        headers={"Authorization": f"Bearer {citizen_token}"},
        files=files,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "caption" in body
    assert "scene_label" in body
    assert "incident_type" in body
    assert "description" in body
    assert body["confidence_score"] >= 0


def test_classifier_picks_fire_for_red_image():
    """Stub analyzer should classify a strongly red image as fire."""
    from app.ai.image_analyzer import StubAnalyzer

    red = make_test_image_bytes(color=(240, 30, 10))
    result = StubAnalyzer().analyze(red)
    assert result.scene_label == "fire_or_smoke"
    assert result.incident_type == "fire"
    assert result.severity_level == "critical"
    assert result.scenario in {"fire_only", "fire_with_people"}


def test_classifier_picks_low_light_for_dark_image():
    from app.ai.image_analyzer import StubAnalyzer

    dark = make_test_image_bytes(color=(10, 10, 10))
    result = StubAnalyzer().analyze(dark)
    assert result.scene_label == "low_light_scene"


def test_classifier_recognises_cyclist_struck_by_vehicle():
    """Combination of person + bicycle + car should classify as a traffic
    accident with a casualty, not a generic 'general' scene."""
    from app.ai.incident_classifier import classify_incident

    objs = [
        {"label": "person", "confidence": 0.7},
        {"label": "bicycle", "confidence": 0.6},
        {"label": "car", "confidence": 0.55},
    ]
    incident_type, severity, scenario = classify_incident("road", objs)
    assert incident_type == "traffic"
    assert severity in {"critical", "high"}
    assert scenario == "cyclist_struck"


def test_classifier_recognises_pedestrian_collision():
    from app.ai.incident_classifier import classify_incident

    objs = [
        {"label": "person", "confidence": 0.8},
        {"label": "car", "confidence": 0.6},
    ]
    incident_type, severity, scenario = classify_incident("road", objs)
    assert incident_type == "traffic"
    assert scenario == "pedestrian_struck"
    assert severity == "critical"


def test_classifier_recognises_armed_threat():
    from app.ai.incident_classifier import classify_incident

    objs = [
        {"label": "knife", "confidence": 0.7},
        {"label": "person", "confidence": 0.8},
    ]
    incident_type, severity, scenario = classify_incident("indoor", objs)
    assert incident_type == "violent_crime"
    assert severity == "critical"
    assert scenario == "armed_with_people"


def test_description_is_multi_paragraph_and_scenario_specific():
    from app.ai.description_generator import generate_description
    from app.ai.image_analyzer import StubAnalyzer

    # A grey/neutral image triggers the stub's "road_scene" template, which
    # describes a cyclist incident.
    res = StubAnalyzer().analyze(make_test_image_bytes(color=(120, 120, 120)))
    desc = generate_description(res)

    paragraphs = [p for p in desc.split("\n\n") if p.strip()]
    assert len(paragraphs) >= 4, "expected a multi-paragraph narrative"
    # Tailored opening: should mention the actual scenario, not just say "general scene".
    assert "general scene" not in desc.lower()
    assert "AI analysis details" in desc
    assert "Severity assessment" in desc
    assert "Recommended immediate actions" in desc


def test_description_ignores_user_description():
    """The AI summary must not include any citizen-supplied text."""
    from app.ai.description_generator import generate_description
    from app.ai.image_analyzer import StubAnalyzer

    res = StubAnalyzer().analyze(make_test_image_bytes(color=(120, 120, 120)))
    secret = "CITIZEN_NOTE_THAT_MUST_NOT_LEAK"
    desc = generate_description(res, user_description=secret)
    assert secret not in desc


def test_description_for_fire_mentions_evacuation():
    from app.ai.description_generator import generate_description
    from app.ai.image_analyzer import StubAnalyzer

    res = StubAnalyzer().analyze(make_test_image_bytes(color=(240, 30, 10)))
    desc = generate_description(res)
    assert "fire" in desc.lower()
    assert "evacuat" in desc.lower() or "rescue" in desc.lower()
