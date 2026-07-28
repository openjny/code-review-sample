"""貸出・違約金の永続化。"""

from lending_core.enums import LoanStatus
from lending_core.models import Loan, Penalty
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload


class LoanRepository:
    """``loans`` / ``penalties`` テーブルへのアクセスを提供する。"""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, loan_id: int) -> Loan | None:
        """ID で貸出を取得する。備品は eager load する。"""
        stmt = select(Loan).options(selectinload(Loan.item)).where(Loan.id == loan_id)
        return self._db.scalars(stmt).first()

    def list_loans(
        self,
        user_id: int | None,
        active_only: bool,
        limit: int,
        offset: int,
    ) -> list[Loan]:
        """条件に一致する貸出を新しい順に一覧取得する。備品は eager load する。"""
        stmt = select(Loan).options(selectinload(Loan.item))
        if user_id is not None:
            stmt = stmt.where(Loan.user_id == user_id)
        if active_only:
            stmt = stmt.where(Loan.status == LoanStatus.ACTIVE)
        stmt = stmt.order_by(Loan.id.desc()).limit(limit).offset(offset)
        return list(self._db.scalars(stmt))

    def add(self, loan: Loan) -> Loan:
        """貸出をセッションに追加する。"""
        self._db.add(loan)
        return loan

    def add_penalty(self, penalty: Penalty) -> Penalty:
        """違約金をセッションに追加する。"""
        self._db.add(penalty)
        return penalty

    def flush(self) -> None:
        """保留中の変更を DB へ送出する。"""
        self._db.flush()
