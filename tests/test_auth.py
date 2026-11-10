from tests.conftest import make_auth_headers


def test_auth_login_success(client, seed_data):
    response = client.post("/api/v1/auth/login", json={"email": "dg@ecole.dz", "password": "dgpassword"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_auth_login_invalid_password(client, seed_data):
    response = client.post("/api/v1/auth/login", json={"email": "dg@ecole.dz", "password": "wrongpassword"})
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_auth_me(client, seed_data):
    headers = make_auth_headers(seed_data["director"])
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "directeur.chlef@ecole.dz"
    assert data["role"] == "branch_director"


def test_auth_refresh(client, seed_data):
    login_res = client.post("/api/v1/auth/login", json={"email": "agent.chlef@ecole.dz", "password": "agentpassword"})
    refresh_token = login_res.json()["refresh_token"]

    refresh_res = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 200
    assert "access_token" in refresh_res.json()

