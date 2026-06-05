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
    # The rejected report must not be persisted as a visible incident.
    listed = client.get("/api/v1/incidents/", headers=auth_header(citizen_token)).json()
    assert listed == []


def test_rejected_image_is_quarantined_as_spam(
    client, citizen_token, auth_header, monkeypatch, TestingSessionLocal
):
    """A rejected (non-incident) upload is recorded in the spam table and its
    image is moved into uploads/spam/ rather than deleted."""
    from pathlib import Path

    from app.ai.image_analyzer import AnalysisResult
    from app.config import settings
    from app.models.spam_report import SpamReport
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

    db = TestingSessionLocal()
    try:
        spam = db.query(SpamReport).all()
        assert len(spam) == 1
        record = spam[0]
        assert record.reason == "non_incident"
        assert record.incident_type == "general"
        assert record.ai_caption
        assert record.image_url.startswith("/uploads/spam/")
    finally:
        db.close()

    # The image file was moved into the spam folder, not deleted.
    spam_name = Path(record.image_url).name
    spam_path = Path(settings.UPLOAD_DIR).resolve() / "spam" / spam_name
    assert spam_path.exists()


def _reject_one(client, citizen_token, auth_header, monkeypatch):
    """Submit a non-incident image so it lands in the spam store."""
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
    return client.post(
        "/api/v1/incidents/",
        headers=auth_header(citizen_token),
        files={"image": ("office.jpg", make_test_image_bytes(), "image/jpeg")},
        data={"severity_level": "low"},
    )


def test_spam_page_lists_and_hides_from_incidents(
    client, citizen_token, officer_token, auth_header, monkeypatch
):
    """Rejected reports appear on the Spam list but not the officer incidents list."""
    assert _reject_one(client, citizen_token, auth_header, monkeypatch).status_code == 422

    spam = client.get("/api/v1/spam/", headers=auth_header(officer_token)).json()
    assert len(spam) == 1
    assert spam[0]["reason"] == "non_incident"

    # Officer incidents list must not include the rejected/spam report.
    incidents = client.get("/api/v1/incidents/", headers=auth_header(officer_token)).json()
    assert incidents == []


def test_mark_not_spam_restores_incident(
    client, citizen_token, officer_token, auth_header, monkeypatch
):
    """Marking a spam report 'not spam' recreates it as a verified incident."""
    assert _reject_one(client, citizen_token, auth_header, monkeypatch).status_code == 422

    spam = client.get("/api/v1/spam/", headers=auth_header(officer_token)).json()
    spam_id = spam[0]["id"]

    r = client.post(f"/api/v1/spam/{spam_id}/not-spam", headers=auth_header(officer_token))
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "verified"

    # Now it shows up for officers and the spam list is empty.
    incidents = client.get("/api/v1/incidents/", headers=auth_header(officer_token)).json()
    assert len(incidents) == 1
    assert incidents[0]["status"] == "verified"
    assert client.get("/api/v1/spam/", headers=auth_header(officer_token)).json() == []


def test_backfill_imports_legacy_rejected_incidents(
    client, citizen_token, officer_token, auth_header, TestingSessionLocal
):
    """A pre-existing rejected incident (no spam record) is imported by backfill."""
    from app.models import Incident, SpamReport, User
    from app.models.incident import IncidentStatus, SeverityLevel

    db = TestingSessionLocal()
    try:
        citizen = db.query(User).filter(User.email == "citizen@aira.example.com").first()
        legacy = Incident(
            reporter_id=citizen.id,
            image_url="/uploads/legacy.jpg",
            ai_description="A person at a desk.",
            incident_type="general",
            severity_level=SeverityLevel.low,
            status=IncidentStatus.rejected,
        )
        db.add(legacy)
        db.commit()
        legacy_id = legacy.id
        assert db.query(SpamReport).count() == 0
    finally:
        db.close()

    # The legacy rejected incident is hidden from the officer incidents list...
    assert client.get("/api/v1/incidents/", headers=auth_header(officer_token)).json() == []
    # ...until backfill surfaces it on the Spam page.
    r = client.post("/api/v1/spam/backfill", headers=auth_header(officer_token))
    assert r.status_code == 200, r.text
    assert r.json() == {"created": 1, "total_rejected": 1}

    spam = client.get("/api/v1/spam/", headers=auth_header(officer_token)).json()
    assert len(spam) == 1
    assert spam[0]["incident_id"] == legacy_id
    assert spam[0]["ai_description"] == "A person at a desk."

    # Idempotent: a second run imports nothing.
    r2 = client.post("/api/v1/spam/backfill", headers=auth_header(officer_token))
    assert r2.json() == {"created": 0, "total_rejected": 1}


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
