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


def test_non_incident_is_discarded_not_stored(
    client, citizen_token, officer_token, auth_header, monkeypatch, TestingSessionLocal
):
    """A photo the AI does not recognise as an incident (selfie / office / random
    object) is discarded outright: no incident row AND no spam record are kept,
    so abusers cannot fill the database with junk."""
    from app.ai.image_analyzer import AnalysisResult
    from app.models import Incident
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

    # Nothing is persisted — not as an incident, not as spam.
    assert client.get("/api/v1/incidents/", headers=auth_header(officer_token)).json() == []
    assert client.get("/api/v1/spam/", headers=auth_header(officer_token)).json() == []
    db = TestingSessionLocal()
    try:
        assert db.query(Incident).count() == 0
        assert db.query(SpamReport).count() == 0
    finally:
        db.close()


def test_mark_not_spam_restores_incident(client, citizen_token, officer_token, auth_header):
    """A duplicate quarantined to spam can be restored as a verified incident."""
    assert _submit_incident(
        client, citizen_token, latitude=-1.95, longitude=30.06
    ).status_code == 201
    assert _submit_incident(
        client, citizen_token, latitude=-1.95, longitude=30.06
    ).status_code == 409

    spam = client.get("/api/v1/spam/", headers=auth_header(officer_token)).json()
    assert len(spam) == 1
    spam_id = spam[0]["id"]

    r = client.post(f"/api/v1/spam/{spam_id}/not-spam", headers=auth_header(officer_token))
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "verified"

    # Restored alongside the original incident; spam list now empty.
    incidents = client.get("/api/v1/incidents/", headers=auth_header(officer_token)).json()
    assert len(incidents) == 2
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


def test_duplicate_report_is_quarantined_as_spam(
    client, citizen_token, officer_token, auth_header, TestingSessionLocal
):
    """A second report of the same accident (same type, same place, same window)
    is not filed as a new incident — it is quarantined to spam and linked to the
    original."""
    first = _submit_incident(client, citizen_token, latitude=-1.95, longitude=30.06)
    assert first.status_code == 201, first.text
    original_id = first.json()["id"]

    # A second photo of the same scene a few metres away.
    second = _submit_incident(client, citizen_token, latitude=-1.9501, longitude=30.0601)
    assert second.status_code == 409, second.text

    # Only the original incident is visible to officers.
    incidents = client.get("/api/v1/incidents/", headers=auth_header(officer_token)).json()
    assert [i["id"] for i in incidents] == [original_id]

    # The duplicate is on the Spam page, linked to the original.
    spam = client.get("/api/v1/spam/", headers=auth_header(officer_token)).json()
    assert len(spam) == 1
    assert spam[0]["reason"] == "duplicate"
    assert spam[0]["duplicate_of_incident_id"] == original_id


def test_distant_report_is_not_a_duplicate(client, citizen_token, officer_token, auth_header):
    """A report of the same type far away is its own incident, not a duplicate."""
    assert _submit_incident(client, citizen_token, latitude=-1.95, longitude=30.06).status_code == 201
    # ~22 km away (well beyond the duplicate radius).
    assert _submit_incident(client, citizen_token, latitude=-2.15, longitude=30.06).status_code == 201

    incidents = client.get("/api/v1/incidents/", headers=auth_header(officer_token)).json()
    assert len(incidents) == 2
    assert client.get("/api/v1/spam/", headers=auth_header(officer_token)).json() == []


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
