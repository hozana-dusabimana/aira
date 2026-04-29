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
