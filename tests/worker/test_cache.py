"""TTL 付きキャッシュ (lending_core.cache) の検証。"""

from datetime import date, timedelta

from lending_core.cache import AGGREGATE_KEY_PREFIX, TTLCache, aggregate_key

TTL_SECONDS = 60


def test_get_returns_stored_value(frozen_clock) -> None:
    cache = TTLCache(ttl_seconds=TTL_SECONDS)
    cache.set("key", {"value": 1})

    assert cache.get("key") == {"value": 1}


def test_get_returns_none_for_unknown_key(frozen_clock) -> None:
    cache = TTLCache(ttl_seconds=TTL_SECONDS)

    assert cache.get("missing") is None


def test_set_overwrites_existing_value(frozen_clock) -> None:
    cache = TTLCache(ttl_seconds=TTL_SECONDS)
    cache.set("key", "old")
    cache.set("key", "new")

    assert cache.get("key") == "new"


def test_value_is_still_available_just_before_ttl(frozen_clock) -> None:
    cache = TTLCache(ttl_seconds=TTL_SECONDS)
    cache.set("key", "value")

    frozen_clock.advance(timedelta(seconds=TTL_SECONDS - 1))

    assert cache.get("key") == "value"


def test_get_returns_none_once_ttl_has_elapsed(frozen_clock) -> None:
    cache = TTLCache(ttl_seconds=TTL_SECONDS)
    cache.set("key", "value")

    frozen_clock.advance(timedelta(seconds=TTL_SECONDS))

    assert cache.get("key") is None


def test_invalidate_removes_only_the_specified_key(frozen_clock) -> None:
    cache = TTLCache(ttl_seconds=TTL_SECONDS)
    cache.set("a", 1)
    cache.set("b", 2)

    cache.invalidate("a")

    assert cache.get("a") is None
    assert cache.get("b") == 2


def test_invalidate_unknown_key_does_not_raise(frozen_clock) -> None:
    cache = TTLCache(ttl_seconds=TTL_SECONDS)

    cache.invalidate("missing")


def test_invalidate_prefix_removes_all_matching_keys(frozen_clock) -> None:
    cache = TTLCache(ttl_seconds=TTL_SECONDS)
    cache.set("aggregate:2026-07-01", 1)
    cache.set("aggregate:2026-07-02", 2)
    cache.set("other:2026-07-01", 3)

    cache.invalidate_prefix(AGGREGATE_KEY_PREFIX)

    assert cache.get("aggregate:2026-07-01") is None
    assert cache.get("aggregate:2026-07-02") is None
    assert cache.get("other:2026-07-01") == 3


def test_clear_removes_every_entry(frozen_clock) -> None:
    cache = TTLCache(ttl_seconds=TTL_SECONDS)
    cache.set("a", 1)
    cache.set("b", 2)

    cache.clear()

    assert cache.get("a") is None
    assert cache.get("b") is None


def test_aggregate_key_uses_iso_date() -> None:
    assert aggregate_key(date(2026, 7, 1)) == "aggregate:2026-07-01"
