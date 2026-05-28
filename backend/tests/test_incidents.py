from tests.conftest import make_test_image_bytes


def _submit_incident(client, token, **form):
    files = {"image": ("test.jpg", make_test_image_bytes(), "image/jpeg")}
    data = {
        "user_description": "There is a small fire near the market.",
        "latitude": -1.95,
        "longitude": 30.06,
        "severity_level": "high",
    }
    data.update(form)
    return client.post(
        "/api/v1/incidents/",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data=data,
    )


def test_submit_incident_runs_ai_and_returns_description(client, citizen_token):
    r = _submit_incident(client, citizen_token)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["image_url"].startswith("/uploads/")
    assert body["status"] in ("verified", "analyzing", "pending")
    assert body["ai_description"]
    assert body["ai_analysis"] is not None
    assert body["ai_analysis"]["confidence_score"] is not None
    assert len(body["images"]) == 1


def test_officer_sees_reporter_contact(client, citizen_token, officer_token, auth_header):
    sub = _submit_incident(client, citizen_token).json()
    r = client.get(f"/api/v1/incidents/{sub['id']}", headers=auth_header(officer_token))
    assert r.status_code == 200, r.text
    reporter = r.json()["reporter"]
    assert reporter is not None
    assert reporter["full_name"] == "Citizen Bar"
    assert "phone" in reporter


def test_officer_notified_on_new_report(client, citizen_token, officer_token, auth_header):
    _submit_incident(client, citizen_token)
    r = client.get("/api/v1/notifications/", headers=auth_header(officer_token))
    assert r.status_code == 200
    assert any(n["type"] == "incident_reported" for n in r.json())


def test_rejects_non_incident_image(client, citizen_token, auth_header, monkeypatch):
    """A photo the AI classifies as a non-incident (e.g. a person at a desk)
    is rejected instead of being filed."""
    from app.ai.image_analyzer import AnalysisResult
    from app.services import ai_service

    class _FakeAnalyzer:
        model_version = "fake-1.0"

        def analyze(self, _image_bytes):
            return AnalysisResult(
                caption="A person sitting at a desk in an office.",
                scene_label="office",
                detected_objects=[{"label": "person", "confidence": 0.9}],
                confidence_score=0.9,
                incident_type="general",
                severity_level="low",
                scenario="people_only",
                model_version="fake-1.0",
            )

    monkeypatch.setattr(ai_service, "get_analyzer", lambda: _FakeAnalyzer())

    r = client.post(
        "/api/v1/incidents/",
        headers=auth_header(citizen_token),
        files={"image": ("office.jpg", make_test_image_bytes(), "image/jpeg")},
        data={"severity_level": "low"},
    )
    assert r.status_code == 422, r.text
    # The rejected report must not be persisted.
    listed = client.get("/api/v1/incidents/", headers=auth_header(citizen_token)).json()
    assert listed == []


def test_citizen_only_sees_own_incidents(client, citizen_token, auth_header):
    _submit_incident(client, citizen_token)
    r = client.get("/api/v1/incidents/", headers=auth_header(citizen_token))
    assert r.status_code == 200
    assert all(i["reporter_id"] for i in r.json())
    assert len(r.json()) >= 1


def test_officer_sees_all_incidents(client, citizen_token, officer_token, auth_header):
    _submit_incident(client, citizen_token)
    r = client.get("/api/v1/incidents/", headers=auth_header(officer_token))
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_officer_can_update_status(client, citizen_token, officer_token, auth_header):
    sub = _submit_incident(client, citizen_token).json()
    incident_id = sub["id"]
    r = client.put(
        f"/api/v1/incidents/{incident_id}/status",
        json={"status": "in_progress", "note": "Officer dispatched"},
        headers=auth_header(officer_token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "in_progress"


def test_citizen_cannot_update_status(client, citizen_token, auth_header):
    sub = _submit_incident(client, citizen_token).json()
    r = client.put(
        f"/api/v1/incidents/{sub['id']}/status",
        json={"status": "resolved"},
        headers=auth_header(citizen_token),
    )
    assert r.status_code == 403


def test_admin_can_delete_incident(client, citizen_token, admin_token, auth_header):
    sub = _submit_incident(client, citizen_token).json()
    r = client.delete(f"/api/v1/incidents/{sub['id']}", headers=auth_header(admin_token))
    assert r.status_code == 200


def test_messaging_between_citizen_and_officer(client, citizen_token, officer_token, auth_header):
    sub = _submit_incident(client, citizen_token).json()
    incident_id = sub["id"]

    r1 = client.post(
        f"/api/v1/incidents/{incident_id}/messages",
        json={"message": "Please send help!"},
        headers=auth_header(citizen_token),
    )
    assert r1.status_code == 201

    r2 = client.post(
        f"/api/v1/incidents/{incident_id}/messages",
        json={"message": "Officer is on the way."},
        headers=auth_header(officer_token),
    )
    assert r2.status_code == 201

    r3 = client.get(
        f"/api/v1/incidents/{incident_id}/messages",
        headers=auth_header(citizen_token),
    )
    assert r3.status_code == 200
    assert len(r3.json()) == 2


def test_nearby_incidents(client, citizen_token, officer_token, auth_header):
    _submit_incident(client, citizen_token, latitude=-1.95, longitude=30.06)
    r = client.get(
        "/api/v1/incidents/nearby",
        params={"lat": -1.95, "lng": 30.06, "radius_km": 5},
        headers=auth_header(officer_token),
    )
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_get_incident_404(client, officer_token, auth_header):
    r = client.get("/api/v1/incidents/99999", headers=auth_header(officer_token))
    assert r.status_code == 404


def test_assign_incident(client, citizen_token, officer_token, auth_header, TestingSessionLocal):
    sub = _submit_incident(client, citizen_token).json()
    # Officer's id from DB
    from app.models import Officer
    db = TestingSessionLocal()
    officer = db.query(Officer).first()
    officer_pk = officer.id
    db.close()

    r = client.post(
        f"/api/v1/incidents/{sub['id']}/assign",
        json={"officer_id": officer_pk},
        headers=auth_header(officer_token),
    )
    assert r.status_code == 200
    assert r.json()["assigned_officer_id"] == officer_pk
    assert r.json()["status"] in ("assigned", "in_progress")
