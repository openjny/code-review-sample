"""金額計算 (lending_core.money) の検証。"""

from decimal import Decimal

import pytest
from lending_core import money


@pytest.mark.parametrize(
    ("amount", "expected_yen"),
    [
        (Decimal("0"), 0),
        (Decimal("0.4"), 0),
        (Decimal("0.5"), 1),
        (Decimal("0.6"), 1),
        (Decimal("1.4"), 1),
        (Decimal("1.5"), 2),
        (Decimal("2.5"), 3),
        (Decimal("100.5"), 101),
        (Decimal("-0.5"), -1),
    ],
)
def test_to_yen_rounds_half_up(amount: Decimal, expected_yen: int) -> None:
    assert money.to_yen(amount) == expected_yen


@pytest.mark.parametrize(
    ("amount", "half_up_yen", "bankers_yen"),
    [
        (Decimal("0.5"), 1, 0),
        (Decimal("2.5"), 3, 2),
        (Decimal("4.5"), 5, 4),
    ],
)
def test_to_yen_differs_from_builtin_bankers_rounding(
    amount: Decimal, half_up_yen: int, bankers_yen: int
) -> None:
    assert money.to_yen(amount) == half_up_yen
    assert round(amount) == bankers_yen


@pytest.mark.parametrize(
    ("unit_yen", "quantity", "rate", "expected_yen"),
    [
        (300, 2, Decimal("0.5"), 300),
        (300, 1, Decimal("1"), 300),
        (100, 3, Decimal("1"), 300),
        (101, 1, Decimal("0.5"), 51),
        (0, 5, Decimal("0.5"), 0),
        (300, 0, Decimal("0.5"), 0),
    ],
)
def test_multiply_yen(unit_yen: int, quantity: int, rate: Decimal, expected_yen: int) -> None:
    assert money.multiply_yen(unit_yen, quantity, rate) == expected_yen


def test_multiply_yen_uses_rate_one_by_default() -> None:
    assert money.multiply_yen(250, 4) == 1000
