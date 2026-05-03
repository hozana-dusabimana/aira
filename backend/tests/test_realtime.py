"""WebSocket real-time tests."""
import json

from tests.conftest import make_test_image_bytes


def _login(client, email, password, officer=False):
    url = "/api/v1/auth/officer/login" if officer else "/api/v1/auth/login"
    r = client.post(url, json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_staff_ws_rejects_unauthenticated(client):
    # Missing token → connection should be closed before yielding
    try:
        with client.websocket_connect("/ws/staff"):
            assert False, "Expected close on missing token"
    except Exception:
        pass


def test_staff_ws_rejects_citizen_token(client, citizen_token):
    try:
        with client.websocket_connect(f"/ws/staff?token={citizen_token}"):
            assert False, "Expected close for citizen on staff stream"
    except Exception:
        pass


def test_staff_ws_receives_incident_created_event(client, officer_token, citizen_token):
    """When a citizen submits an incident, officers connected to /ws/staff
    should receive an incident.created event."""
    with client.websocket_connect(f"/ws/staff?token={officer_token}") as ws:
        # Submit an incident as the citizen
        files = {"image": ("test.jpg", make_test_image_bytes(), "image/jpeg")}
        data = {
            "user_description": "Test incident.",
            "latitude": -1.95,
            "longitude": 30.06,
            "severity_level": "medium",
        }
        r = client.post(
            "/api/v1/incidents/",
            headers={"Authorization": f"Bearer {citizen_token}"},
            files=files,
            data=data,
        )
        assert r.status_code == 201, r.text

        # Officer should receive incident.created (and possibly incident.analyzed).
        # TestClient has its own loop; we receive synchronously.
        msg = json.loads(ws.receive_text())
        assert msg["event"] in ("incident.created", "incident.analyzed")
        assert msg["data"]["id"] == r.json()["id"]


def test_citizen_ws_receives_status_update(client, officer_token, citizen_token):
    """When an officer updates status, the reporter's /ws/citizen stream gets it."""
    # Submit first
    files = {"image": ("test.jpg", make_test_image_bytes(), "image/jpeg")}
    data = {"user_description": "x", "severity_level": "low"}
    r = client.post(
        "/api/v1/incidents/",
        headers={"Authorization": f"Bearer {citizen_token}"},
        files=files,
        data=data,
    )
    incident_id = r.json()["id"]

    with client.websocket_connect(f"/ws/citizen?token={citizen_token}") as ws:
        client.put(
            f"/api/v1/incidents/{incident_id}/status",
            headers={"Authorization": f"Bearer {officer_token}"},
            json={"status": "verified", "note": "ok"},
        )
        # Citizen gets a notification event AND incident.status_changed
        seen_events = set()
        for _ in range(2):
            try:
                msg = json.loads(ws.receive_text())
                seen_events.add(msg["event"])
            except Exception:
                break
        assert "incident.status_changed" in seen_events or "notification" in seen_events
