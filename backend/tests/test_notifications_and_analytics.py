from tests.conftest import make_test_image_bytes


def _submit(client, token, latitude=-1.95, longitude=30.06):
    return client.post(
        "/api/v1/incidents/",
        headers={"Authorization": f"Bearer {token}"},
        files={"image": ("t.jpg", make_test_image_bytes(), "image/jpeg")},
        data={"latitude": latitude, "longitude": longitude, "severity_level": "high"},
    )


def test_overview_metrics(client, citizen_token, officer_token, auth_header):
    # Two distinct incidents (far apart) so neither is treated as a duplicate.
    _submit(client, citizen_token, latitude=-1.95, longitude=30.06)
    _submit(client, citizen_token, latitude=-2.20, longitude=30.20)
    r = client.get("/api/v1/analytics/overview", headers=auth_header(officer_token))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total_reports"] == 2
    assert data["pending"] + data["resolved"] + data["in_progress"] <= data["total_reports"]


def test_citizen_cannot_access_analytics(client, citizen_token, auth_header):
    r = client.get("/api/v1/analytics/overview", headers=auth_header(citizen_token))
    assert r.status_code == 403


def test_incidents_by_type(client, citizen_token, officer_token, auth_header):
    _submit(client, citizen_token)
    r = client.get("/api/v1/analytics/incidents-by-type", headers=auth_header(officer_token))
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_notifications_created_on_status_update(
    client, citizen_token, officer_token, auth_header
):
    sub = _submit(client, citizen_token).json()
    client.put(
        f"/api/v1/incidents/{sub['id']}/status",
        json={"status": "in_progress", "note": "Dispatched"},
        headers=auth_header(officer_token),
    )
    r = client.get("/api/v1/notifications/", headers=auth_header(citizen_token))
    assert r.status_code == 200
    notifs = r.json()
    # The reporter is notified about the status change on their own incident.
    status_notifs = [
        n
        for n in notifs
        if n["related_incident_id"] == sub["id"]
        and n["type"] in ("status_update", "report_approved", "report_resolved", "report_rejected")
    ]
    assert status_notifs, notifs
    assert any("Dispatched" in (n["message"] or "") for n in status_notifs)


def test_register_device_token(client, citizen_token, auth_header):
    r = client.post(
        "/api/v1/notifications/register-device",
        json={"token": "fcm-test-token-123", "platform": "android"},
        headers=auth_header(citizen_token),
    )
    assert r.status_code == 200


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
