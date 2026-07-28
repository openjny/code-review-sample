"""現在時刻の取得 (lending_core.clock) の検証。"""

from datetime import UTC, datetime, timedelta

from lending_core import clock

FIXED = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)


def test_now_returns_timezone_aware_utc() -> None:
    current = clock.now()
    assert current.tzinfo is not None
    assert current.utcoffset() == timedelta(0)


def test_set_provider_replaces_now() -> None:
    clock.set_provider(lambda: FIXED)
    try:
        assert clock.now() == FIXED
    finally:
        clock.reset_provider()


def test_reset_provider_restores_default_provider() -> None:
    clock.set_provider(lambda: FIXED)
    clock.reset_provider()

    current = clock.now()
    assert current != FIXED
    assert current.utcoffset() == timedelta(0)


def test_frozen_clock_fixture_freezes_now(frozen_clock) -> None:
    assert clock.now() == frozen_clock.current

    frozen_clock.advance(timedelta(days=1))
    assert clock.now() == frozen_clock.current


def test_clock_is_restored_after_frozen_clock_fixture() -> None:
    assert clock.now() != FIXED
