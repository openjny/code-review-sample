"""業務ルール。

貸出期間・延長・延滞判定・違約金の算出をここに集約する。
副作用（DB アクセス・ログ出力）を持たせないこと。
"""

from datetime import datetime, timedelta
from decimal import Decimal

from lending_core import clock, money
from lending_core.enums import ItemCategory, ItemStatus
from lending_core.errors import (
    ExtensionLimitExceededError,
    ItemNotAvailableError,
    LoanAlreadyReturnedError,
)

MAX_EXTENSION_COUNT = 2
EXTENSION_DAYS = 7
PENALTY_RATE = Decimal("0.5")

LOAN_PERIOD_DAYS: dict[ItemCategory, int] = {
    ItemCategory.TOOL: 14,
    ItemCategory.EQUIPMENT: 14,
    ItemCategory.HIGH_DEMAND: 7,
}

DEFAULT_LOAN_PERIOD_DAYS = 14


def loan_period_days(category: ItemCategory) -> int:
    """カテゴリに対応する貸出日数を返す。"""
    return LOAN_PERIOD_DAYS.get(category, DEFAULT_LOAN_PERIOD_DAYS)


def calculate_due_date(loaned_at: datetime, category: ItemCategory) -> datetime:
    """貸出日時とカテゴリから返却期限を算出する。"""
    return loaned_at + timedelta(days=loan_period_days(category))


def ensure_loanable(item_status: ItemStatus) -> None:
    """備品が貸出可能な状態かを検証する。"""
    if item_status is not ItemStatus.AVAILABLE:
        raise ItemNotAvailableError(f"備品が貸出できる状態ではありません: {item_status}")


def is_overdue(due_at: datetime, at: datetime | None = None) -> bool:
    """指定時点で延滞しているかを返す。期限ちょうどは延滞ではない。"""
    current = at if at is not None else clock.now()
    return current > due_at


def overdue_days(due_at: datetime, at: datetime | None = None) -> int:
    """延滞日数を返す。延滞していない場合は 0。端数の 1 日は切り上げる。"""
    current = at if at is not None else clock.now()
    if current <= due_at:
        return 0
    delta = current - due_at
    return -(-int(delta.total_seconds()) // 86400)


def ensure_extendable(extension_count: int, due_at: datetime, at: datetime | None = None) -> None:
    """延長可能かを検証する。上限超過または延滞中は延長できない。"""
    if extension_count >= MAX_EXTENSION_COUNT:
        raise ExtensionLimitExceededError(
            f"延長回数の上限 ({MAX_EXTENSION_COUNT} 回) に達しています"
        )
    if is_overdue(due_at, at):
        raise ExtensionLimitExceededError("延滞中の貸出は延長できません")


def extend_due_date(due_at: datetime) -> datetime:
    """返却期限を 1 回分延長した日時を返す。"""
    return due_at + timedelta(days=EXTENSION_DAYS)


def ensure_returnable(returned_at: datetime | None) -> None:
    """返却可能かを検証する。"""
    if returned_at is not None:
        raise LoanAlreadyReturnedError("この貸出はすでに返却されています")


def calculate_penalty_yen(
    due_at: datetime,
    daily_fee_yen: int,
    at: datetime | None = None,
) -> int:
    """延滞違約金を整数円で算出する。延滞していない場合は 0。"""
    days = overdue_days(due_at, at)
    if days == 0:
        return 0
    return money.multiply_yen(daily_fee_yen, days, PENALTY_RATE)
