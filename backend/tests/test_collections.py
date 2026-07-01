from __future__ import annotations

from fastapi.testclient import TestClient

from tests.helpers import approve_emoji


def auth_headers(client: TestClient, email: str = "collector@example.com") -> dict[str, str]:
    client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "SecretPwd123!",
            "display_name": "Collector",
        },
    )
    login_response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "SecretPwd123!"},
    )
    return {"Authorization": f"Bearer {login_response.json()['access_token']}"}


def create_emoji(
    client: TestClient,
    headers: dict[str, str],
    *,
    symbol: str = "🧪",
    title: str = "Test Emoji",
    keywords: list[str] | None = None,
) -> dict:
    response = client.post(
        "/api/emojis",
        json={
            "symbol": symbol,
            "title": title,
            "keywords": keywords or ["test"],
        },
        headers=headers,
    )
    assert response.status_code == 201
    emoji = response.json()
    approve_emoji(client, emoji["id"])
    return emoji


def collection_label(collection: dict) -> str:
    return collection.get("name") or collection.get("title") or collection.get("slug") or ""


def create_collection(
    client: TestClient,
    headers: dict[str, str],
    *,
    title: str,
    description: str = "A test collection",
    kind: str = "personal",
) -> dict:
    for payload in (
        {"name": title, "description": description, "kind": kind},
        {"title": title, "description": description, "kind": kind},
        {"name": title, "kind": kind},
        {"title": title, "kind": kind},
    ):
        response = client.post("/api/collections", json=payload, headers=headers)
        if response.status_code != 422:
            assert response.status_code in (200, 201)
            return response.json()
    assert response.status_code != 422
    return response.json()


def add_emoji_to_collection(
    client: TestClient,
    emoji_id: int,
    collection_id: int,
    headers: dict[str, str],
) -> None:
    response = client.post(
        f"/api/collections/{collection_id}/emojis",
        json={"emoji_id": emoji_id},
        headers=headers,
    )
    assert response.status_code in (200, 201)


def current_user_id(client: TestClient, headers: dict[str, str]) -> int:
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    return response.json()["id"]


def set_emoji_collections(
    client: TestClient,
    emoji_id: int,
    collection_ids: list[int],
    headers: dict[str, str],
) -> None:
    for payload in (
        {"collection_ids": collection_ids},
        {"collections": collection_ids},
        collection_ids,
    ):
        response = client.put(
            f"/api/emojis/{emoji_id}/collections",
            json=payload,
            headers=headers,
        )
        if response.status_code != 422:
            assert response.status_code in (200, 204)
            return
    assert response.status_code != 422


def emoji_payload_keys(item: dict) -> dict:
    return {
        "id": item["id"],
        "symbol": item["symbol"],
        "title": item["title"],
        "description": item.get("description"),
        "category": item.get("category"),
        "keywords": item.get("keywords"),
        "can_delete": item.get("can_delete"),
        "like_count": item.get("like_count"),
        "is_liked": item.get("is_liked"),
        "submitter_id": item.get("submitter_id"),
        "submitter_name": item.get("submitter_name"),
        "moderation_status": item.get("moderation_status"),
    }


def test_public_collection_list_and_detail(client: TestClient) -> None:
    owner_headers = auth_headers(client, email="list_owner@example.com")
    emoji = create_emoji(client, owner_headers, symbol="🧭", title="Compass")
    collection = create_collection(client, owner_headers, title="Guides", kind="public")
    add_emoji_to_collection(client, emoji["id"], collection["id"], owner_headers)

    list_response = client.get("/api/collections")
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert isinstance(list_body["items"], list)
    assert list_body["total"] >= 1
    assert list_body["limit"] >= 1
    assert list_body["offset"] == 0
    assert any(item["id"] == collection["id"] for item in list_body["items"])

    detail_response = client.get(f"/api/collections/{collection['id']}", headers=owner_headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["id"] == collection["id"]
    assert collection_label(detail) == "Guides"
    assert detail["kind"] == "public"
    assert detail["owner_name"] == "Collector"
    assert len(detail["emojis"]) == 1
    assert detail.get("emoji_count", 1) == 1

    list_emojis = client.get("/api/emojis", headers=owner_headers).json()["items"]
    emoji_from_list = next(item for item in list_emojis if item["id"] == emoji["id"])
    assert emoji_payload_keys(detail["emojis"][0]) == emoji_payload_keys(emoji_from_list)


def test_collection_crud_requires_auth_and_owner(client: TestClient) -> None:
    owner_headers = auth_headers(client, email="owner@example.com")
    other_headers = auth_headers(client, email="other@example.com")

    anonymous_create = client.post("/api/collections", json={"name": "Secret", "kind": "personal"})
    assert anonymous_create.status_code == 401

    collection = create_collection(client, owner_headers, title="Owner Only")

    forbidden_update = client.put(
        f"/api/collections/{collection['id']}",
        json={"name": "Intruded"},
        headers=other_headers,
    )
    assert forbidden_update.status_code == 403

    forbidden_delete = client.delete(
        f"/api/collections/{collection['id']}",
        headers=other_headers,
    )
    assert forbidden_delete.status_code == 403

    update_response = client.put(
        f"/api/collections/{collection['id']}",
        json={"name": "Owner Updated"},
        headers=owner_headers,
    )
    assert update_response.status_code == 200
    assert collection_label(update_response.json()) == "Owner Updated"

    delete_response = client.delete(
        f"/api/collections/{collection['id']}",
        headers=owner_headers,
    )
    assert delete_response.status_code == 204

    missing_after_delete = client.get(f"/api/collections/{collection['id']}")
    assert missing_after_delete.status_code == 404


def test_duplicate_add_and_remove_are_idempotent(client: TestClient) -> None:
    headers = auth_headers(client, email="idempotent@example.com")
    emoji = create_emoji(client, headers, symbol="🎯", title="Target")
    collection = create_collection(client, headers, title="Targets")

    first_add = client.post(
        f"/api/collections/{collection['id']}/emojis",
        json={"emoji_id": emoji["id"]},
        headers=headers,
    )
    assert first_add.status_code == 201
    assert first_add.json()["detail"] == "added"

    second_add = client.post(
        f"/api/collections/{collection['id']}/emojis",
        json={"emoji_id": emoji["id"]},
        headers=headers,
    )
    assert second_add.status_code == 200
    assert second_add.json()["detail"] == "already added"

    detail_response = client.get(f"/api/collections/{collection['id']}", headers=headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert len(detail["emojis"]) == 1
    assert detail["emojis"][0]["id"] == emoji["id"]

    first_remove = client.delete(
        f"/api/collections/{collection['id']}/emojis/{emoji['id']}",
        headers=headers,
    )
    assert first_remove.status_code == 204

    second_remove = client.delete(
        f"/api/collections/{collection['id']}/emojis/{emoji['id']}",
        headers=headers,
    )
    assert second_remove.status_code == 204

    detail_after_remove = client.get(f"/api/collections/{collection['id']}", headers=headers)
    assert detail_after_remove.status_code == 200
    assert detail_after_remove.json()["emojis"] == []


def test_nonexistent_collection_and_emoji_404s(client: TestClient) -> None:
    headers = auth_headers(client, email="missing@example.com")
    emoji = create_emoji(client, headers, symbol="🧩", title="Puzzle")
    collection = create_collection(client, headers, title="Puzzles")

    assert client.get("/api/collections/99999").status_code == 404
    assert client.put("/api/collections/99999", json={"name": "Nope"}, headers=headers).status_code == 404
    assert client.delete("/api/collections/99999", headers=headers).status_code == 404

    assert client.post(
        f"/api/emojis/99999/collections/{collection['id']}",
        headers=headers,
    ).status_code == 404
    assert client.post(
        f"/api/emojis/{emoji['id']}/collections/99999",
        headers=headers,
    ).status_code == 404
    assert client.get("/api/emojis/99999/collections", headers=headers).status_code == 404
    assert client.put(
        "/api/emojis/99999/collections",
        json={"collection_ids": [collection["id"]]},
        headers=headers,
    ).status_code == 404


def test_collection_detail_emoji_payload_consistency(client: TestClient) -> None:
    headers = auth_headers(client, email="payload@example.com")
    emoji = create_emoji(
        client,
        headers,
        symbol="🍓",
        title="Strawberry",
        keywords=["fruit", "red"],
    )
    collection = create_collection(client, headers, title="Fruit Basket")
    add_emoji_to_collection(client, emoji["id"], collection["id"], headers)

    emoji_list_response = client.get("/api/emojis", headers=headers)
    list_item = next(item for item in emoji_list_response.json()["items"] if item["id"] == emoji["id"])

    detail_response = client.get(f"/api/collections/{collection['id']}", headers=headers)
    detail_item = detail_response.json()["emojis"][0]

    assert emoji_payload_keys(detail_item) == emoji_payload_keys(list_item)


def test_get_and_put_emoji_collections(client: TestClient) -> None:
    headers = auth_headers(client, email="emoji_collections@example.com")
    emoji = create_emoji(client, headers, symbol="📌", title="Pin")
    first_collection = create_collection(client, headers, title="Pinned")
    second_collection = create_collection(client, headers, title="Later")

    add_emoji_to_collection(client, emoji["id"], first_collection["id"], headers)

    get_response = client.get(f"/api/emojis/{emoji['id']}/collections", headers=headers)
    assert get_response.status_code == 200
    get_body = get_response.json()
    assert get_body["emoji_id"] == emoji["id"]
    assert set(get_body["selected_collection_ids"]) == {first_collection["id"]}
    assert any(
        collection_label(item) == "Pinned" or item.get("id") == first_collection["id"]
        for item in get_body["collections"]
    )

    set_emoji_collections(client, emoji["id"], [second_collection["id"]], headers)

    updated_response = client.get(f"/api/emojis/{emoji['id']}/collections", headers=headers)
    updated_body = updated_response.json()
    assert updated_body["emoji_id"] == emoji["id"]
    assert set(updated_body["selected_collection_ids"]) == {second_collection["id"]}
    assert any(item.get("id") == second_collection["id"] for item in updated_body["collections"])


def test_cleanup_when_collection_or_emoji_is_deleted(client: TestClient) -> None:
    headers = auth_headers(client, email="cleanup@example.com")
    emoji = create_emoji(client, headers, symbol="🧹", title="Broom")
    collection = create_collection(client, headers, title="Cleanup")
    add_emoji_to_collection(client, emoji["id"], collection["id"], headers)

    delete_collection_response = client.delete(
        f"/api/collections/{collection['id']}",
        headers=headers,
    )
    assert delete_collection_response.status_code == 204

    emoji_collections_response = client.get(f"/api/emojis/{emoji['id']}/collections", headers=headers)
    assert emoji_collections_response.status_code == 200
    assert all(item.get("id") != collection["id"] for item in emoji_collections_response.json()["collections"])

    second_collection = create_collection(client, headers, title="Cleanup Two")
    add_emoji_to_collection(client, emoji["id"], second_collection["id"], headers)

    delete_emoji_response = client.delete(f"/api/emojis/{emoji['id']}", headers=headers)
    assert delete_emoji_response.status_code == 204

    collection_detail_response = client.get(f"/api/collections/{second_collection['id']}", headers=headers)
    assert collection_detail_response.status_code == 200
    assert collection_detail_response.json()["emojis"] == []


def test_collection_list_sort_by_name_asc(client: TestClient) -> None:
    headers = auth_headers(client, "sort-name@example.com")
    create_collection(client, headers, title="Zebra Collection")
    create_collection(client, headers, title="Alpha Collection")
    create_collection(client, headers, title="Middle Collection")

    response = client.get("/api/collections?sort=name_asc", headers=headers)
    assert response.status_code == 200
    names = [item["name"] for item in response.json()["items"]]
    assert names == ["Alpha Collection", "Middle Collection", "Zebra Collection"]


def test_collection_list_sort_by_emoji_count_desc(client: TestClient) -> None:
    headers = auth_headers(client, "sort-count@example.com")
    emoji_a = create_emoji(client, headers, symbol="🅰️", title="Count A")
    emoji_b = create_emoji(client, headers, symbol="🅱️", title="Count B")
    emoji_c = create_emoji(client, headers, symbol="🅲", title="Count C")

    col_big = create_collection(client, headers, title="Big Collection", kind="public")
    col_med = create_collection(client, headers, title="Medium Collection", kind="public")
    create_collection(client, headers, title="Empty Collection", kind="public")

    for eid in [emoji_a, emoji_b, emoji_c]:
        add_emoji_to_collection(client, eid["id"], col_big["id"], headers)
    add_emoji_to_collection(client, emoji_a["id"], col_med["id"], headers)

    response = client.get("/api/collections?sort=emoji_count_desc")
    assert response.status_code == 200
    names = [item["name"] for item in response.json()["items"]]
    assert names.index("Big Collection") < names.index("Medium Collection") < names.index("Empty Collection")


def test_collection_list_pagination(client: TestClient) -> None:
    headers = auth_headers(client, "sort-page@example.com")
    for i in range(5):
        create_collection(client, headers, title=f"Page Collection {i:02d}")

    response = client.get("/api/collections?limit=2&offset=2", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2
    assert body["offset"] == 2

    full = client.get("/api/collections", headers=headers)
    assert full.json()["total"] == 5
    assert len(full.json()["items"]) == 5


def test_collection_list_default_sort_is_updated_desc(client: TestClient) -> None:
    headers = auth_headers(client, "sort-default@example.com")
    create_collection(client, headers, title="First")
    create_collection(client, headers, title="Second")
    create_collection(client, headers, title="Third")

    response = client.get("/api/collections", headers=headers)
    assert response.status_code == 200
    names = [item["name"] for item in response.json()["items"]]
    assert names == ["Third", "Second", "First"]


def test_collection_detail_count_is_not_paginated(client: TestClient) -> None:
    headers = auth_headers(client, "detail-count@example.com")
    collection = create_collection(client, headers, title="Paged Count", kind="public")
    for index in range(3):
        emoji = create_emoji(
            client,
            headers,
            symbol=str(index),
            title=f"Paged Emoji {index}",
        )
        add_emoji_to_collection(client, emoji["id"], collection["id"], headers)

    response = client.get(f"/api/collections/{collection['id']}?limit=1&offset=1")

    assert response.status_code == 200
    body = response.json()
    assert body["emoji_count"] == 3
    assert len(body["emojis"]) == 1


def test_list_collections_anonymous_excludes_personal(client: TestClient) -> None:
    headers = auth_headers(client, email="private-owner@example.com")
    create_collection(client, headers, title="Public One", kind="public")
    create_collection(client, headers, title="Secret Personal", kind="personal")

    # Anonymous viewers must never see personal collections.
    response = client.get("/api/collections")
    assert response.status_code == 200
    kinds = [item["kind"] for item in response.json()["items"]]
    assert "personal" not in kinds
    assert response.json()["total"] == len(response.json()["items"])
    assert response.json()["total"] >= 1


def test_list_collections_owner_sees_own_personal(client: TestClient) -> None:
    headers = auth_headers(client, email="self-viewer@example.com")
    user_id = current_user_id(client, headers)
    create_collection(client, headers, title="My Public", kind="public")
    create_collection(client, headers, title="My Personal", kind="personal")

    response = client.get(f"/api/collections?owner_id={user_id}", headers=headers)
    assert response.status_code == 200
    names = {item["name"] for item in response.json()["items"]}
    assert names == {"My Public", "My Personal"}
    assert response.json()["total"] == 2


def test_list_collections_other_user_excludes_personal(client: TestClient) -> None:
    owner_headers = auth_headers(client, email="owner-b@example.com")
    owner_id = current_user_id(client, owner_headers)
    create_collection(client, owner_headers, title="B Public", kind="public")
    create_collection(client, owner_headers, title="B Personal", kind="personal")

    viewer_headers = auth_headers(client, email="viewer-b@example.com")

    # Authenticated non-owner: sees only the other user's public collections.
    response = client.get(f"/api/collections?owner_id={owner_id}", headers=viewer_headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["name"] for item in items] == ["B Public"]
    assert response.json()["total"] == 1


def test_list_collections_search_still_hides_personal_for_anon(client: TestClient) -> None:
    headers = auth_headers(client, email="search-owner@example.com")
    create_collection(client, headers, title="Searchable Public", kind="public")
    create_collection(client, headers, title="Searchable Personal", kind="personal")

    # A search that matches both names must still exclude the personal one
    # for an anonymous viewer — the visibility filter composes with search.
    response = client.get("/api/collections?search=Searchable")
    assert response.status_code == 200
    names = [item["name"] for item in response.json()["items"]]
    assert names == ["Searchable Public"]
