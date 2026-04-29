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


def test_classifier_picks_low_light_for_dark_image():
    from app.ai.image_analyzer import StubAnalyzer

    dark = make_test_image_bytes(color=(10, 10, 10))
    result = StubAnalyzer().analyze(dark)
    assert result.scene_label == "low_light_scene"


def test_description_is_well_formed():
    from app.ai.description_generator import generate_description
    from app.ai.image_analyzer import StubAnalyzer

    res = StubAnalyzer().analyze(make_test_image_bytes(color=(120, 120, 120)))
    desc = generate_description(res)
    assert "AI-generated incident summary" in desc
    assert "Scene:" in desc
    assert "severity" in desc.lower()
