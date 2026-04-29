def test_register_creates_citizen_and_returns_tokens(client):
    payload = {
        "full_name": "New User",
        "email": "new@aira.example.com",
        "phone": "+250788444444",
        "password": "Strong@1234",
    }
    r = client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["role"] == "citizen"
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["expires_in"] > 0


def test_register_rejects_duplicate_email(client):
    payload = {
        "full_name": "Citizen Bar",
        "email": "citizen@aira.example.com",
        "password": "Strong@1234",
    }
    r = client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 409


def test_login_success(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "citizen@aira.example.com", "password": "Citizen@1"},
    )
    assert r.status_code == 200
    assert r.json()["role"] == "citizen"


def test_login_wrong_password(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "citizen@aira.example.com", "password": "wrong"},
    )
    assert r.status_code == 401


def test_citizen_cannot_use_officer_login(client):
    r = client.post(
        "/api/v1/auth/officer/login",
        json={"email": "citizen@aira.example.com", "password": "Citizen@1"},
    )
    assert r.status_code == 403


def test_officer_login_succeeds(client):
    r = client.post(
        "/api/v1/auth/officer/login",
        json={"email": "officer@aira.example.com", "password": "Officer@1"},
    )
    assert r.status_code == 200
    assert r.json()["role"] == "officer"


def test_get_me_requires_auth(client):
    r = client.get("/api/v1/users/me")
    assert r.status_code == 401


def test_get_me_returns_profile(client, citizen_token, auth_header):
    r = client.get("/api/v1/users/me", headers=auth_header(citizen_token))
    assert r.status_code == 200
    assert r.json()["email"] == "citizen@aira.example.com"


def test_change_password(client, citizen_token, auth_header):
    r = client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": "Citizen@1", "new_password": "NewPass@123"},
        headers=auth_header(citizen_token),
    )
    assert r.status_code == 200
    # Old password should fail now
    r2 = client.post(
        "/api/v1/auth/login",
        json={"email": "citizen@aira.example.com", "password": "Citizen@1"},
    )
    assert r2.status_code == 401


def test_refresh_token(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "citizen@aira.example.com", "password": "Citizen@1"},
    )
    refresh = r.json()["refresh_token"]
    r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r2.status_code == 200
    assert r2.json()["access_token"]


def test_forgot_password_does_not_leak_email_existence(client):
    r1 = client.post("/api/v1/auth/forgot-password", json={"email": "citizen@aira.example.com"})
    r2 = client.post("/api/v1/auth/forgot-password", json={"email": "nonexistent@aira.example.com"})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json() == r2.json()
