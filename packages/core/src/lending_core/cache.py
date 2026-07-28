"""日次集計結果を保持する TTL 付きインメモリキャッシュ。

.. important::
   集計対象データ (Loan / Item) を更新する処理は必ず対応するキーを invalidate すること。
   （docs/architecture.md「キャッシュ」節）
"""

import os
from datetime import date, datetime, timedelta
from typing import Any

from lending_core import clock

AGGREGATE_KEY_PREFIX = "aggregate:"
DEFAULT_TTL_SECONDS = 3600
_TTL_ENV_VAR = "LENDING_AGGREGATE_CACHE_TTL_SECONDS"


class TTLCache:
    """有効期限付きのキーバリューキャッシュ。"""

    def __init__(self, ttl_seconds: int) -> None:
        self._ttl = timedelta(seconds=ttl_seconds)
        self._entries: dict[str, tuple[datetime, Any]] = {}

    def get(self, key: str) -> Any | None:
        """値を取得する。未登録または期限切れの場合は None を返す。"""
        current = clock.now()
        entry = self._entries.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if current >= expires_at:
            del self._entries[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        """値を格納する。有効期限は格納時点から ``ttl_seconds`` 後。"""
        expires_at = clock.now() + self._ttl
        self._entries[key] = (expires_at, value)

    def invalidate(self, key: str) -> None:
        """指定キーのエントリを削除する。未登録でもエラーにしない。"""
        self._entries.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> None:
        """指定プレフィックスで始まるキーのエントリをすべて削除する。"""
        for key in [k for k in self._entries if k.startswith(prefix)]:
            del self._entries[key]

    def clear(self) -> None:
        """すべてのエントリを削除する。"""
        self._entries.clear()


def aggregate_key(target_date: date) -> str:
    """日次集計のキャッシュキーを返す（例 ``aggregate:2026-07-28``）。"""
    return f"{AGGREGATE_KEY_PREFIX}{target_date.isoformat()}"


def _configured_ttl_seconds() -> int:
    raw = os.environ.get(_TTL_ENV_VAR)
    return int(raw) if raw else DEFAULT_TTL_SECONDS


aggregate_cache = TTLCache(_configured_ttl_seconds())
