"""DB エンジン・セッションの生成。

``lending_api`` には依存しないため、バッチ側で独自にセッションを払い出す
（docs/architecture.md の依存ルール 2）。
"""

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from typing import Any

from lending_core.models import Base
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from lending_worker.config import get_settings

SQLITE_SCHEME_PREFIX = "sqlite"


def _connect_args(database_url: str) -> dict[str, Any]:
    # SQLite はデフォルトで接続を生成スレッドに固定するため、スレッド実行に備えて解除する。
    if database_url.startswith(SQLITE_SCHEME_PREFIX):
        return {"check_same_thread": False}
    return {}


@lru_cache
def get_engine() -> Engine:
    """バッチ処理共通の Engine を返す。"""
    settings = get_settings()
    return create_engine(settings.database_url, connect_args=_connect_args(settings.database_url))


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Session ファクトリを返す。"""
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """モデル定義からテーブルを作成する。"""
    Base.metadata.create_all(bind=get_engine())


@contextmanager
def get_session() -> Iterator[Session]:
    """DB セッションを払い出す。正常終了で commit、例外で rollback し、必ず close する。"""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
