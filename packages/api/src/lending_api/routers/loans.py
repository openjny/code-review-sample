"""貸出エンドポイント。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from lending_core.enums import UserRole
from lending_core.models import User
from lending_core.schemas import LoanCreate, LoanRead

from lending_api.config import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT
from lending_api.deps import get_loan_service, require_role
from lending_api.services.loan_service import LoanService

router = APIRouter(prefix="/loans", tags=["loans"])


@router.get("")
def list_loans(
    service: Annotated[LoanService, Depends(get_loan_service)],
    actor: Annotated[User, Depends(require_role(UserRole.MEMBER))],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[LoanRead]:
    """貸出を一覧取得する。member は自分の貸出のみ取得できる。"""
    return service.list_loans(actor, limit=limit, offset=offset)


@router.get("/{loan_id}")
def get_loan(
    loan_id: int,
    service: Annotated[LoanService, Depends(get_loan_service)],
    actor: Annotated[User, Depends(require_role(UserRole.MEMBER))],
) -> LoanRead:
    """貸出を 1 件取得する。"""
    return service.get_loan(actor, loan_id)


@router.post("", status_code=201)
def create_loan(
    payload: LoanCreate,
    service: Annotated[LoanService, Depends(get_loan_service)],
    actor: Annotated[User, Depends(require_role(UserRole.MEMBER))],
) -> LoanRead:
    """備品を貸し出す。"""
    return service.create_loan(actor, payload)


@router.post("/{loan_id}/extend")
def extend_loan(
    loan_id: int,
    service: Annotated[LoanService, Depends(get_loan_service)],
    actor: Annotated[User, Depends(require_role(UserRole.MEMBER))],
) -> LoanRead:
    """返却期限を 1 回分延長する。"""
    return service.extend_loan(actor, loan_id)


@router.post("/{loan_id}/return")
def return_loan(
    loan_id: int,
    service: Annotated[LoanService, Depends(get_loan_service)],
    actor: Annotated[User, Depends(require_role(UserRole.MEMBER))],
) -> LoanRead:
    """備品を返却する。延滞していれば違約金を計上する。"""
    return service.return_loan(actor, loan_id)
