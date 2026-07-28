"""業務ルール (lending_core.rules) の検証。"""

from datetime import UTC, datetime, timedelta

import pytest
from lending_core import rules
from lending_core.enums import ItemCategory, ItemStatus
from lending_core.errors import (
    ExtensionLimitExceededError,
    ItemNotAvailableError,
    LoanAlreadyReturnedError,
)

LOANED_AT = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)
DUE_AT = datetime(2026, 7, 15, 9, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("category", "expected_days"),
    [
        (ItemCategory.TOOL, 14),
        (ItemCategory.EQUIPMENT, 14),
        (ItemCategory.HIGH_DEMAND, 7),
    ],
)
def test_loan_period_days_returns_configured_days_per_category(
    category: ItemCategory, expected_days: int
) -> None:
    assert rules.loan_period_days(category) == expected_days


@pytest.mark.parametrize(
    ("category", "expected_days"),
    [
        (ItemCategory.TOOL, 14),
        (ItemCategory.EQUIPMENT, 14),
        (ItemCategory.HIGH_DEMAND, 7),
    ],
)
def test_calculate_due_date_adds_category_period_to_loaned_at(
    category: ItemCategory, expected_days: int
) -> None:
    assert rules.calculate_due_date(LOANED_AT, category) == LOANED_AT + timedelta(
        days=expected_days
    )


def test_ensure_loanable_accepts_available_item() -> None:
    rules.ensure_loanable(ItemStatus.AVAILABLE)


@pytest.mark.parametrize(
    "status",
    [ItemStatus.LOANED, ItemStatus.MAINTENANCE, ItemStatus.RETIRED],
)
def test_ensure_loanable_rejects_non_available_item(status: ItemStatus) -> None:
    with pytest.raises(ItemNotAvailableError):
        rules.ensure_loanable(status)


def test_is_overdue_is_false_before_due_at() -> None:
    assert rules.is_overdue(DUE_AT, DUE_AT - timedelta(seconds=1)) is False


def test_is_overdue_is_false_exactly_at_due_at() -> None:
    assert rules.is_overdue(DUE_AT, DUE_AT) is False


def test_is_overdue_is_false_within_grace_period() -> None:
    assert rules.is_overdue(DUE_AT, DUE_AT + timedelta(hours=23, minutes=59)) is False


def test_is_overdue_is_true_after_grace_period() -> None:
    assert rules.is_overdue(DUE_AT, DUE_AT + timedelta(hours=24, seconds=1)) is True


def test_is_overdue_falls_back_to_clock_now_when_at_is_omitted(frozen_clock) -> None:
    frozen_clock.set(DUE_AT)
    assert rules.is_overdue(DUE_AT) is False

    frozen_clock.advance(timedelta(hours=24, seconds=1))
    assert rules.is_overdue(DUE_AT) is True


@pytest.mark.parametrize(
    ("elapsed", "expected_days"),
    [
        (timedelta(days=-1), 0),
        (timedelta(seconds=-1), 0),
        (timedelta(0), 0),
        (timedelta(hours=24, seconds=1), 1),
        (timedelta(hours=47, minutes=59), 1),
        (timedelta(hours=48), 1),
        (timedelta(hours=49), 2),
        (timedelta(days=3), 2),
        (timedelta(days=3, seconds=1), 3),
    ],
)
def test_overdue_days_rounds_partial_days_up(elapsed: timedelta, expected_days: int) -> None:
    assert rules.overdue_days(DUE_AT, DUE_AT + elapsed) == expected_days


def test_overdue_days_falls_back_to_clock_now_when_at_is_omitted(frozen_clock) -> None:
    frozen_clock.set(DUE_AT + timedelta(hours=49))
    assert rules.overdue_days(DUE_AT) == 2


@pytest.mark.parametrize("extension_count", [0, rules.MAX_EXTENSION_COUNT - 1])
def test_ensure_extendable_accepts_count_below_limit(extension_count: int) -> None:
    rules.ensure_extendable(extension_count, DUE_AT, DUE_AT - timedelta(days=1))


@pytest.mark.parametrize(
    "extension_count",
    [rules.MAX_EXTENSION_COUNT, rules.MAX_EXTENSION_COUNT + 1],
)
def test_ensure_extendable_rejects_count_at_or_above_limit(extension_count: int) -> None:
    with pytest.raises(ExtensionLimitExceededError):
        rules.ensure_extendable(extension_count, DUE_AT, DUE_AT - timedelta(days=1))


def test_ensure_extendable_rejects_overdue_loan() -> None:
    with pytest.raises(ExtensionLimitExceededError, match="延滞中"):
        rules.ensure_extendable(0, DUE_AT, DUE_AT + timedelta(hours=24, seconds=1))


def test_ensure_extendable_accepts_loan_exactly_at_due_at() -> None:
    rules.ensure_extendable(0, DUE_AT, DUE_AT)


def test_extend_due_date_adds_extension_days() -> None:
    assert rules.extend_due_date(DUE_AT) == DUE_AT + timedelta(days=rules.EXTENSION_DAYS)


def test_ensure_returnable_accepts_loan_not_yet_returned() -> None:
    rules.ensure_returnable(None)


def test_ensure_returnable_rejects_already_returned_loan() -> None:
    with pytest.raises(LoanAlreadyReturnedError):
        rules.ensure_returnable(DUE_AT)


@pytest.mark.parametrize(
    ("daily_fee_yen", "elapsed", "expected_yen"),
    [
        (300, timedelta(days=-1), 0),
        (300, timedelta(0), 0),
        (300, timedelta(days=3), 300),
        (300, timedelta(days=3, seconds=1), 450),
        (0, timedelta(days=6), 0),
        (101, timedelta(days=2), 51),
    ],
)
def test_calculate_penalty_yen(daily_fee_yen: int, elapsed: timedelta, expected_yen: int) -> None:
    assert rules.calculate_penalty_yen(DUE_AT, daily_fee_yen, DUE_AT + elapsed) == expected_yen


def test_calculate_penalty_yen_falls_back_to_clock_now_when_at_is_omitted(frozen_clock) -> None:
    frozen_clock.set(DUE_AT + timedelta(days=3))
    assert rules.calculate_penalty_yen(DUE_AT, 300) == 300
