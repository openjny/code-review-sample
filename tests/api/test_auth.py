"""認証トークンと認証エンドポイントの検証。"""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from lending_api import API_PREFIX
from lending_api.config import get_settings
from lending_api.services import auth_service
from lending_core.errors import UnauthenticatedError
from lending_core.models import User
from sqlalchemy.orm import Session

USERS_ME_URL = f"{API_PREFIX}/users/me"


def test_create_token_issues_a_verifiable_token(frozen_clock) -> None:
    token = auth_service.create_token(42)

    assert auth_service.verify_token(token) == 42


def test_create_token_issues_different_tokens_per_user(frozen_clock) -> None:
    assert auth_service.create_token(1) != auth_service.create_token(2)


def test_verify_token_rejects_tampered_signature(frozen_clock) -> None:
    payload = auth_service.create_token(42).partition(".")[0]
    other_signature = auth_service.create_token(43).partition(".")[2]

    with pytest.raises(UnauthenticatedError, match="署名"):
        auth_service.verify_token(f"{payload}.{other_signature}")


def test_verify_token_rejects_tampered_payload(frozen_clock) -> None:
    signature = auth_service.create_token(42).partition(".")[2]
    forged_payload = auth_service._b64encode(b"999:99999999999")

    with pytest.raises(UnauthenticatedError, match="署名"):
        auth_service.verify_token(f"{forged_payload}.{signature}")


def test_verify_token_accepts_token_just_before_expiry(frozen_clock, monkeypatch) -> None:
    monkeypatch.setenv("LENDING_TOKEN_TTL_MINUTES", "60")
    get_settings.cache_clear()
    token = auth_service.create_token(42)

    frozen_clock.advance(timedelta(minutes=59))

    assert auth_service.verify_token(token) == 42


def test_verify_token_rejects_expired_token(frozen_clock, monkeypatch) -> None:
    monkeypatch.setenv("LENDING_TOKEN_TTL_MINUTES", "60")
    get_settings.cache_clear()
    token = auth_service.create_token(42)

    frozen_clock.advance(timedelta(minutes=60))

    with pytest.raises(UnauthenticatedError, match="有効期限"):
        auth_service.verify_token(token)


@pytest.mark.parametrize(
    "token",
    ["", "separator-less-token", ".", "payload-only.", ".signature-only"],
)
def test_verify_token_rejects_malformed_token(token: str) -> None:
    with pytest.raises(UnauthenticatedError):
        auth_service.verify_token(token)


def test_verify_token_rejects_non_numeric_user_id() -> None:
    payload = auth_service._b64encode(b"not-an-int:99999999999")
    signature = auth_service._sign(payload, get_settings().token_secret)

    with pytest.raises(UnauthenticatedError, match="内容"):
        auth_service.verify_token(f"{payload}.{signature}")


def test_request_without_authorization_header_returns_401(client: TestClient) -> None:
    response = client.get(USERS_ME_URL)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_request_with_non_bearer_scheme_returns_401(client: TestClient) -> None:
    response = client.get(USERS_ME_URL, headers={"Authorization": "Basic dXNlcjpwYXNz"})

    assert response.status_code == 401


def test_request_with_invalid_token_returns_401(client: TestClient) -> None:
    response = client.get(USERS_ME_URL, headers={"Authorization": "Bearer broken.token"})

    assert response.status_code == 401


def test_token_for_unknown_user_returns_401(client: TestClient, frozen_clock) -> None:
    token = auth_service.create_token(9999)

    response = client.get(USERS_ME_URL, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_inactive_user_returns_403(client: TestClient, db: Session, users: dict[str, User]) -> None:
    users["member"].is_active = False
    db.commit()
    token = auth_service.create_token(users["member"].id)

    response = client.get(USERS_ME_URL, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
