"""API テスト用の fixture。"""

from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from lending_api.deps import get_db
from lending_api.main import app
from lending_api.services import auth_service
from lending_core.enums import UserRole
from lending_core.models import User
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    """テスト用 DB に差し替えた未認証クライアント。"""

    def override_get_db() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def users(db: Session) -> dict[str, User]:
    """ロール別の利用者を作成する。"""
    created = {
        "member": User(
            email="member@example.com", name="一般 太郎", role=UserRole.MEMBER, is_active=True
        ),
        "staff": User(
            email="staff@example.com", name="担当 花子", role=UserRole.STAFF, is_active=True
        ),
        "admin": User(
            email="admin@example.com", name="管理 次郎", role=UserRole.ADMIN, is_active=True
        ),
    }
    db.add_all(created.values())
    db.commit()
    return created


@pytest.fixture
def auth_client(
    client: TestClient,
    users: dict[str, User],
) -> Callable[[str], TestClient]:
    """指定ロールの利用者として認証済みのクライアントを生成するファクトリ。"""

    def factory(role: str) -> TestClient:
        token = auth_service.create_token(users[role].id)
        return TestClient(app, headers={"Authorization": f"Bearer {token}"})

    return factory


@pytest.fixture
def member_client(auth_client: Callable[[str], TestClient]) -> TestClient:
    """member ロールで認証済みのクライアント。"""
    return auth_client("member")


@pytest.fixture
def staff_client(auth_client: Callable[[str], TestClient]) -> TestClient:
    """staff ロールで認証済みのクライアント。"""
    return auth_client("staff")


@pytest.fixture
def admin_client(auth_client: Callable[[str], TestClient]) -> TestClient:
    """admin ロールで認証済みのクライアント。"""
    return auth_client("admin")
