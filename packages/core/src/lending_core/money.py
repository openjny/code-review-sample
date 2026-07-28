"""金額計算。

金額は ``Decimal`` で計算し、最終的に :func:`to_yen` で整数円へ丸める。
"""

from decimal import Decimal


def to_yen(amount: Decimal) -> int:
    """Decimal の金額を整数円に丸める。"""
    return int(round(amount))


def multiply_yen(unit_yen: int, quantity: int, rate: Decimal = Decimal("1")) -> int:
    """単価 × 数量 × 係数 を整数円で返す。"""
    return to_yen(Decimal(unit_yen) * Decimal(quantity) * rate)
