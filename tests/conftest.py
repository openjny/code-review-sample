"""テスト全体で共有する fixture。"""

import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from lending_core import clock
from lending_core.models import Base
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

TEST_TOKEN_SECRET = "test-token-secret"
TEST_DATABASE_URL = "sqlite+pysqlite:///:memory:"
# 時計を進めるテストでトークンが失効しないよう、テスト中の有効期限は十分長く取る。
TEST_TOKEN_TTL_MINUTES = "525600"
FIXED_NOW = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)

# lending_api.main はインポート時に設定を読むため、収集前に環境変数を用意しておく。
os.environ.setdefault("LENDING_TOKEN_SECRET", TEST_TOKEN_SECRET)
os.environ.setdefault("LENDING_DATABASE_URL", TEST_DATABASE_URL)
os.environ.setdefault("LENDING_TOKEN_TTL_MINUTES", TEST_TOKEN_TTL_MINUTES)

from lending_api.config import get_settings as get_api_settings  # noqa: E402
from lending_worker.config import get_settings as get_worker_settings  # noqa: E402


class FrozenClock:
    """テスト中に任意の時刻へ進められる時計。"""

    def __init__(self, current: datetime) -> None:
        self.current = current

    def now(self) -> datetime:
        """固定された現在時刻を返す。"""
        return self.current

    def set(self, value: datetime) -> None:
        """現在時刻を指定の時刻へ移動する。"""
        self.current = value

    def advance(self, delta: timedelta) -> datetime:
        """現在時刻を指定量だけ進める。"""
        self.current += delta
        return self.current


@pytest.fixture(autouse=True)
def test_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """設定をテスト用の環境変数で上書きし、前後でキャッシュを破棄する。"""
    monkeypatch.setenv("LENDING_TOKEN_SECRET", TEST_TOKEN_SECRET)
    monkeypatch.setenv("LENDING_DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv("LENDING_TOKEN_TTL_MINUTES", TEST_TOKEN_TTL_MINUTES)
    get_api_settings.cache_clear()
    get_worker_settings.cache_clear()
    yield
    get_api_settings.cache_clear()
    get_worker_settings.cache_clear()


@pytest.fixture
def frozen_clock() -> Iterator[FrozenClock]:
    """lending_core.clock の時刻を固定する。"""
    frozen = FrozenClock(FIXED_NOW)
    clock.set_provider(frozen.now)
    yield frozen
    clock.reset_provider()


@pytest.fixture
def engine() -> Iterator[Engine]:
    """テストごとに独立したインメモリ SQLite を用意する。"""
    test_engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    """テスト用 DB に接続する Session ファクトリを返す。"""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """テストデータの投入・検証に使う DB セッション。"""
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
