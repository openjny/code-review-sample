"""貸出に関するユースケース。

業務ルール（期限計算・延長可否・延滞判定・違約金）は ``lending_core.rules`` に委譲する。
"""

import logging
from datetime import datetime, timedelta

from lending_core import clock, rules
from lending_core.enums import ItemStatus, LoanStatus, UserRole, role_satisfies
from lending_core.errors import NotFoundError, PermissionDeniedError
from lending_core.models import Loan, Penalty, User
from lending_core.schemas import LoanCreate, LoanRead
from sqlalchemy.orm import Session

from lending_api.config import DEFAULT_PAGE_LIMIT
from lending_api.repositories.item_repo import ItemRepository
from lending_api.repositories.loan_repo import LoanRepository

logger = logging.getLogger(__name__)

PENALTY_REASON = "延滞違約金"


class LoanService:
    """貸出の参照・作成・延長・返却を提供する。"""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._loans = LoanRepository(db)
        self._items = ItemRepository(db)

    def list_loans(
        self,
        actor: User,
        limit: int = DEFAULT_PAGE_LIMIT,
        offset: int = 0,
    ) -> list[LoanRead]:
        """貸出を一覧取得する。member は自分の貸出のみ取得できる。"""
        user_id = None if self._can_access_others(actor) else actor.id
        loans = self._loans.list_loans(
            user_id=user_id, active_only=False, limit=limit, offset=offset
        )
        return [self._to_read(loan) for loan in loans]

    def get_loan(self, actor: User, loan_id: int) -> LoanRead:
        """貸出を 1 件取得する。"""
        return self._to_read(self._get_accessible_loan(actor, loan_id))

    def create_loan(self, actor: User, payload: LoanCreate) -> LoanRead:
        """備品を貸し出す。貸出可能な状態でなければ ItemNotAvailableError。"""
        item = self._items.get(payload.item_id)
        if item is None:
            raise NotFoundError(f"備品が見つかりません: id={payload.item_id}")
        rules.ensure_loanable(item.status)
        loaned_at = clock.now()
        loan = self._loans.add(
            Loan(
                item_id=item.id,
                user_id=actor.id,
                loaned_at=loaned_at,
                due_at=rules.calculate_due_date(loaned_at, item.category),
                extension_count=0,
                status=LoanStatus.ACTIVE,
            )
        )
        item.status = ItemStatus.LOANED
        self._db.commit()
        return self._to_read(loan)

    def extend_loan(self, actor: User, loan_id: int) -> LoanRead:
        """返却期限を 1 回分延長する。"""
        loan = self._get_accessible_loan(actor, loan_id)
        rules.ensure_returnable(loan.returned_at)
        rules.ensure_extendable(loan.extension_count, loan.due_at)
        loan.due_at = rules.extend_due_date(loan.due_at)
        loan.extension_count += 1
        self._db.commit()
        return self._to_read(loan)

    def return_loan(self, actor: User, loan_id: int) -> LoanRead:
        """備品を返却する。延滞していれば違約金を計上する。"""
        loan = self._get_accessible_loan(actor, loan_id)
        rules.ensure_returnable(loan.returned_at)
        now = datetime.now()
        if now <= loan.due_at + timedelta(hours=24):
            logger.info("猶予期間内の返却です: loan_id=%s", loan.id)
        penalty_yen = rules.calculate_penalty_yen(loan.due_at, loan.item.daily_fee_yen)
        if penalty_yen > 0:
            self._loans.add_penalty(
                Penalty(loan_id=loan.id, amount_yen=penalty_yen, reason=PENALTY_REASON)
            )
        loan.returned_at = clock.now()
        loan.status = LoanStatus.RETURNED
        loan.item.status = ItemStatus.AVAILABLE
        self._db.commit()
        return self._to_read(loan)

    def _can_access_others(self, actor: User) -> bool:
        return role_satisfies(actor.role, UserRole.STAFF)

    def _get_accessible_loan(self, actor: User, loan_id: int) -> Loan:
        loan = self._loans.get(loan_id)
        if loan is None:
            raise NotFoundError(f"貸出が見つかりません: id={loan_id}")
        if not self._can_access_others(actor) and loan.user_id != actor.id:
            raise PermissionDeniedError("他の利用者の貸出は操作できません")
        return loan

    def _to_read(self, loan: Loan) -> LoanRead:
        read = LoanRead.model_validate(loan)
        read.is_overdue = rules.is_overdue(loan.due_at)
        return read
