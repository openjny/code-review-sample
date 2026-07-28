"""貸出実績レポートのエンドポイント。"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from lending_core.enums import UserRole
from lending_core.models import User
from lending_core.schemas import PenaltyRead, ReportRow, ReportSummary

from lending_api.deps import get_report_service, require_role
from lending_api.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/summary")
def get_summary(
    service: Annotated[ReportService, Depends(get_report_service)],
    start: datetime,
    end: datetime,
    category: str | None = None,
    sort_by: str = "loan_count",
    order: str = "desc",
) -> ReportSummary:
    """期間内の貸出実績をカテゴリ別に集計する。"""
    return service.build_summary(start, end, category=category, sort_by=sort_by, order=order)


@router.get("/categories")
def list_categories(
    service: Annotated[ReportService, Depends(get_report_service)],
    _actor: Annotated[User, Depends(require_role(UserRole.MEMBER))],
    start: datetime,
    end: datetime,
) -> list[ReportRow]:
    """期間内のカテゴリ別件数を一覧取得する。"""
    return service.list_categories(start, end)


@router.get("/penalties")
def list_penalties(
    service: Annotated[ReportService, Depends(get_report_service)],
    _actor: Annotated[User, Depends(require_role(UserRole.MEMBER))],
    start: datetime,
    end: datetime,
) -> list[PenaltyRead]:
    """期間内の違約金明細を一覧取得する。"""
    return service.list_penalties(start, end)
