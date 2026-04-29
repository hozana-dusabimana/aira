from tests.conftest import make_test_image_bytes


def _submit(client, token):
    return client.post(
        "/api/v1/incidents/",
        headers={"Authorization": f"Bearer {token}"},
        files={"image": ("t.jpg", make_test_image_bytes(), "image/jpeg")},
        data={"latitude": -1.95, "longitude": 30.06, "severity_level": "high"},
    )


def test_overview_metrics(client, citizen_token, officer_token, auth_header):
    _submit(client, citizen_token)
    _submit(client, citizen_token)
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
    titles = [n["title"] for n in r.json()]
    assert any("status updated" in t.lower() for t in titles)


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
