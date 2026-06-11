from tests.conftest import make_test_image_bytes


def _submit(client, token, latitude=-1.95, longitude=30.06):
    return client.post(
        "/api/v1/incidents/",
        headers={"Authorization": f"Bearer {token}"},
        files={"image": ("t.jpg", make_test_image_bytes(), "image/jpeg")},
        data={"latitude": latitude, "longitude": longitude, "severity_level": "high"},
    )


def test_report_summary_shape(client, citizen_token, officer_token, auth_header):
    _submit(client, citizen_token, latitude=-1.95, longitude=30.06)
    _submit(client, citizen_token, latitude=-2.20, longitude=30.20)

    r = client.get("/api/v1/reports/summary", headers=auth_header(officer_token))
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["total"] == 2
    # Status buckets cannot exceed the total.
    assert data["pending"] + data["in_progress"] + data["resolved"] + data["rejected"] <= data["total"]
    assert 0 <= data["resolution_rate"] <= 100
    assert isinstance(data["by_type"], list)
    assert isinstance(data["by_severity"], list)
    assert isinstance(data["timeline"], list)
    assert len(data["rows"]) == 2
    # Each row carries the fields the PDF/table render relies on.
    row = data["rows"][0]
    for key in ("id", "created_at", "severity", "status"):
        assert key in row


def test_report_summary_status_filter(client, citizen_token, officer_token, auth_header):
    _submit(client, citizen_token)
    # Nothing is resolved yet, so a resolved-only report is empty but valid.
    r = client.get(
        "/api/v1/reports/summary",
        params={"status": "resolved"},
        headers=auth_header(officer_token),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total"] == 0
    assert data["rows"] == []
    assert data["status_filter"] == "resolved"


def test_report_summary_rejects_bad_range(client, officer_token, auth_header):
    r = client.get(
        "/api/v1/reports/summary",
        params={"start_date": "2026-06-10", "end_date": "2026-06-01"},
        headers=auth_header(officer_token),
    )
    assert r.status_code == 422


def test_citizen_cannot_access_reports(client, citizen_token, auth_header):
    r = client.get("/api/v1/reports/summary", headers=auth_header(citizen_token))
    assert r.status_code == 403
