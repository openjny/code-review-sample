"""利用者エンドポイントの検証。"""

from fastapi.testclient import TestClient
from lending_api import API_PREFIX
from lending_core.enums import UserRole
from lending_core.models import User

USERS_URL = f"{API_PREFIX}/users"


def test_get_me_returns_the_authenticated_user(
    member_client: TestClient, users: dict[str, User]
) -> None:
    response = member_client.get(f"{USERS_URL}/me")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == users["member"].id
    assert body["email"] == "member@example.com"
    assert body["role"] == UserRole.MEMBER.value


def test_member_cannot_list_users(member_client: TestClient) -> None:
    response = member_client.get(USERS_URL)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_staff_cannot_list_users(staff_client: TestClient) -> None:
    response = staff_client.get(USERS_URL)

    assert response.status_code == 403


def test_admin_can_list_users(admin_client: TestClient) -> None:
    response = admin_client.get(USERS_URL)

    assert response.status_code == 200
    assert [user["email"] for user in response.json()] == [
        "member@example.com",
        "staff@example.com",
        "admin@example.com",
    ]


def test_admin_can_create_user(admin_client: TestClient) -> None:
    response = admin_client.post(
        USERS_URL,
        json={"email": "new@example.com", "name": "新規 三郎", "role": UserRole.STAFF.value},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new@example.com"
    assert body["role"] == UserRole.STAFF.value
    assert body["is_active"] is True


def test_create_user_with_duplicate_email_returns_400(admin_client: TestClient) -> None:
    response = admin_client.post(
        USERS_URL,
        json={"email": "member@example.com", "name": "重複 太郎"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_user_with_invalid_email_returns_400(admin_client: TestClient) -> None:
    response = admin_client.post(USERS_URL, json={"email": "not-an-email", "name": "不正 太郎"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_member_cannot_create_user(member_client: TestClient) -> None:
    response = member_client.post(
        USERS_URL,
        json={"email": "another@example.com", "name": "権限なし"},
    )

    assert response.status_code == 403
