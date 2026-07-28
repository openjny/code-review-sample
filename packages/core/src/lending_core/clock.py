"""現在時刻の取得。

テスト時に固定できるよう、アプリケーション内では ``datetime.now()`` を直接呼ばず
必ずこのモジュールの :func:`now` を経由する（docs/architecture.md 参照）。
"""

from collections.abc import Callable
from datetime import UTC, datetime

_provider: Callable[[], datetime]


def _default_provider() -> datetime:
    return datetime.now(UTC)


_provider = _default_provider


def now() -> datetime:
    """tz-aware な現在時刻 (UTC) を返す。"""
    return _provider()


def set_provider(provider: Callable[[], datetime]) -> None:
    """時刻プロバイダを差し替える（テスト用）。"""
    global _provider
    _provider = provider


def reset_provider() -> None:
    """時刻プロバイダを既定に戻す。"""
    global _provider
    _provider = _default_provider
