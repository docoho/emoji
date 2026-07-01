from __future__ import annotations

from fastapi.testclient import TestClient


def register_payload(email: str = "user@example.com", password: str = "SecretPwd123!") -> dict[str, str]:
    return {
        "email": email,
        "password": password,
        "display_name": "Emoji Fan",
    }


def test_register_user(client: TestClient) -> None:
    response = client.post("/api/auth/register", json=register_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "user@example.com"
    assert body["display_name"] == "Emoji Fan"
    assert "id" in body
    assert body["is_active"] is True


def test_register_duplicate_email(client: TestClient) -> None:
    payload = register_payload()
    assert client.post("/api/auth/register", json=payload).status_code == 201
    duplicate = client.post("/api/auth/register", json=payload)
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "Email already registered"


def test_login_and_fetch_profile(client: TestClient) -> None:
    payload = register_payload()
    client.post("/api/auth/register", json=payload)

    login_response = client.post(
        "/api/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    me_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    profile = me_response.json()
    assert profile["email"] == payload["email"]
    assert profile["is_active"] is True


def test_login_with_invalid_credentials(client: TestClient) -> None:
    payload = register_payload()
    client.post("/api/auth/register", json=payload)

    bad_login = client.post(
        "/api/auth/login",
        json={"email": payload["email"], "password": "WrongPassword"},
    )
    assert bad_login.status_code == 401
    assert bad_login.json()["detail"] == "Incorrect email or password"
