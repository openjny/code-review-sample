"""DB エンジン・セッションの生成。"""

from collections.abc import Iterator
from functools import lru_cache
from typing import Any

from lending_core.models import Base
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from lending_api.config import get_settings

SQLITE_SCHEME_PREFIX = "sqlite"


def _connect_args(database_url: str) -> dict[str, Any]:
    # SQLite はデフォルトで接続を生成スレッドに固定するため、スレッドプール実行時に備えて解除する。
    if database_url.startswith(SQLITE_SCHEME_PREFIX):
        return {"check_same_thread": False}
    return {}


@lru_cache
def get_engine() -> Engine:
    """アプリケーション共通の Engine を返す。"""
    settings = get_settings()
    return create_engine(settings.database_url, connect_args=_connect_args(settings.database_url))


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Session ファクトリを返す。"""
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """モデル定義からテーブルを作成する。"""
    Base.metadata.create_all(bind=get_engine())


def get_session() -> Iterator[Session]:
    """DB セッションを払い出し、終了時に必ず close する。"""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
