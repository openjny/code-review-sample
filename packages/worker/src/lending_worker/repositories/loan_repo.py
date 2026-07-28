"""バッチ処理から参照する貸出データ。"""

from datetime import datetime

from lending_core.enums import LoanStatus
from lending_core.models import Loan
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload


class LoanRepository:
    """``loans`` テーブルへのアクセスを提供する。"""

    def __init__(self, db: Session) -> None:
        self._db = db

    def list_overdue_loans(self, at: datetime, limit: int, offset: int = 0) -> list[Loan]:
        """指定時点で延滞している貸出を ID 昇順で取得する。備品と利用者は eager load する。"""
        stmt = (
            select(Loan)
            .options(selectinload(Loan.item), selectinload(Loan.user))
            .where(
                Loan.status == LoanStatus.ACTIVE,
                Loan.returned_at.is_(None),
                Loan.due_at < at,
            )
            .order_by(Loan.id)
            .limit(limit)
            .offset(offset)
        )
        return list(self._db.scalars(stmt))

    def count_overdue_loans(self, at: datetime) -> int:
        """指定時点で延滞している貸出の件数を返す。"""
        stmt = (
            select(func.count())
            .select_from(Loan)
            .where(
                Loan.status == LoanStatus.ACTIVE,
                Loan.returned_at.is_(None),
                Loan.due_at < at,
            )
        )
        return self._db.scalar(stmt) or 0

    def flush(self) -> None:
        """保留中の変更を DB へ送出する。"""
        self._db.flush()
