from fastapi.testclient import TestClient


def auth_headers(client: TestClient, email: str = "emoji@example.com") -> dict[str, str]:
    register_payload = {
        "email": email,
        "password": "SecretPwd123!",
        "display_name": "Emoji Tester",
    }
    client.post("/api/auth/register", json=register_payload)
    login_response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "SecretPwd123!"},
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_list_emojis(client: TestClient) -> None:
    response = client.get("/api/emojis")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3
    first = data[0]
    assert {"id", "symbol", "title", "keywords", "can_delete"}.issubset(first.keys())


def test_submit_emoji(client: TestClient) -> None:
    headers = auth_headers(client)
    payload = {
        "symbol": "🧪",
        "title": "Lab Test",
        "description": "Represents experimentation and science.",
        "category": "Objects",
        "keywords": ["lab", "science", "experiment"],
    }

    response = client.post("/api/emojis", json=payload, headers=headers)
    assert response.status_code == 201
    body = response.json()
    assert body["symbol"] == payload["symbol"]
    assert body["keywords"] == sorted(payload["keywords"])
    assert body["submitter_email"] == "emoji@example.com"
    assert body["id"] >= 1000
    assert body["can_delete"] is True

    list_response = client.get("/api/emojis", headers=headers)
    assert any(item["title"] == payload["title"] for item in list_response.json())


def test_duplicate_submission_rejected(client: TestClient) -> None:
    headers = auth_headers(client)
    payload = {
        "symbol": "🧊",
        "title": "Ice Cube",
        "keywords": ["cold"],
    }

    assert client.post("/api/emojis", json=payload, headers=headers).status_code == 201
    duplicate = client.post("/api/emojis", json=payload, headers=headers)
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "Emoji already exists"


def test_delete_requires_owner(client: TestClient) -> None:
    owner_headers = auth_headers(client, email="owner@example.com")
    other_headers = auth_headers(client, email="other@example.com")

    create_response = client.post(
        "/api/emojis",
        headers=owner_headers,
        json={"symbol": "🧵", "title": "Thread", "keywords": ["text"]},
    )
    emoji_id = create_response.json()["id"]

    forbidden = client.delete(f"/api/emojis/{emoji_id}", headers=other_headers)
    assert forbidden.status_code == 403

    delete_response = client.delete(f"/api/emojis/{emoji_id}", headers=owner_headers)
    assert delete_response.status_code == 204

    follow_up = client.get("/api/emojis", headers=owner_headers)
    assert all(item["id"] != emoji_id for item in follow_up.json())


def test_delete_for_legacy_entries_with_matching_email(client: TestClient) -> None:
    headers = auth_headers(client, email="legacy@example.com")

    # create submission then manually clear submitter_id to mimic legacy data
    response = client.post(
        "/api/emojis",
        headers=headers,
        json={"symbol": "🧠", "title": "Brain", "keywords": ["smart"]},
    )
    emoji_id = response.json()["id"]

    from app.db import engine
    from app.models import EmojiSubmission
    from sqlalchemy import text

    submission_id = emoji_id - 1000
    table_name = EmojiSubmission.__table__.name
    with engine.begin() as connection:
        connection.execute(
            text(f"UPDATE {table_name} SET submitter_id = NULL WHERE id = :id"),
            {"id": submission_id},
        )

    list_response = client.get("/api/emojis", headers=headers)
    assert any(item["id"] == emoji_id and item["can_delete"] for item in list_response.json())

    delete_response = client.delete(f"/api/emojis/{emoji_id}", headers=headers)
    assert delete_response.status_code == 204
