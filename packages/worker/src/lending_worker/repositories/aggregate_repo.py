"""日次集計用の集約クエリ。"""

from datetime import datetime

from lending_core.enums import ItemStatus
from lending_core.models import Item, Loan, Penalty
from sqlalchemy import func, select
from sqlalchemy.orm import Session


class AggregateRepository:
    """集計に必要な件数・合計値を取得する。"""

    def __init__(self, db: Session) -> None:
        self._db = db

    def count_loans_created_between(self, start: datetime, end: datetime) -> int:
        """``start`` 以上 ``end`` 未満に発生した貸出の件数を返す。"""
        stmt = (
            select(func.count())
            .select_from(Loan)
            .where(Loan.loaned_at >= start, Loan.loaned_at < end)
        )
        return self._db.scalar(stmt) or 0

    def count_loans_returned_between(self, start: datetime, end: datetime) -> int:
        """``start`` 以上 ``end`` 未満に返却された貸出の件数を返す。"""
        stmt = (
            select(func.count())
            .select_from(Loan)
            .where(Loan.returned_at >= start, Loan.returned_at < end)
        )
        return self._db.scalar(stmt) or 0

    def sum_penalty_yen_between(self, start: datetime, end: datetime) -> int:
        """``start`` 以上 ``end`` 未満に計上された違約金の合計を整数円で返す。"""
        stmt = select(func.coalesce(func.sum(Penalty.amount_yen), 0)).where(
            Penalty.created_at >= start, Penalty.created_at < end
        )
        return self._db.scalar(stmt) or 0

    def count_items_by_status(self) -> dict[ItemStatus, int]:
        """備品の状態別件数を 1 クエリで取得する。該当のない状態はキーに含まれない。"""
        stmt = select(Item.status, func.count(Item.id)).group_by(Item.status)
        return {status: count for status, count in self._db.execute(stmt)}
