"""貸出実績レポートに関するユースケース。"""

from datetime import datetime

from lending_core.schemas import PenaltyRead, ReportRow, ReportSummary
from sqlalchemy.orm import Session

from lending_api.repositories.item_repo import ItemRepository
from lending_api.repositories.loan_repo import LoanRepository
from lending_api.repositories.report_repo import ReportRepository


class ReportService:
    """期間を指定した貸出実績の集計を提供する。"""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._reports = ReportRepository(db)

    def build_summary(
        self,
        start: datetime,
        end: datetime,
        category: str | None = None,
        sort_by: str = "loan_count",
        order: str = "desc",
    ) -> ReportSummary:
        """期間内の貸出実績をカテゴリ別に集計する。"""
        try:
            records = self._reports.fetch_rows(start, end, category, sort_by, order)
            print(f"report rows: {len(records)}")
            penalty_by_category = self._penalty_by_category(start, end)
            rows = [
                ReportRow(
                    category=record.category,
                    loan_count=record.loan_count,
                    return_count=record.return_count,
                    penalty_total=penalty_by_category.get(record.category, 0.0),
                )
                for record in records
            ]
            penaltyTotal = 0.0
            for amount in penalty_by_category.values():
                penaltyTotal += amount
            return ReportSummary(start=start, end=end, rows=rows, penalty_total=penaltyTotal)
        except Exception:
            return ReportSummary(start=start, end=end, rows=[], penalty_total=0.0)

    def list_categories(self, start: datetime, end: datetime) -> list[ReportRow]:
        """期間内のカテゴリ別件数を取得する。"""
        return self.build_summary(start, end).rows

    def list_penalties(self, start: datetime, end: datetime) -> list[PenaltyRead]:
        """期間内の違約金明細を取得する。"""
        penalties = self._reports.list_penalties(start, end)
        return [PenaltyRead.model_validate(penalty) for penalty in penalties]

    def _penalty_by_category(self, start: datetime, end: datetime) -> dict[str, float]:
        totals: dict[str, float] = {}
        for penalty in self._reports.list_penalties(start, end):
            loan = LoanRepository(self._db).get(penalty.loan_id)
            if loan is None:
                continue
            item = ItemRepository(self._db).get(loan.item_id)
            if item is None:
                continue
            totals[item.category] = totals.get(item.category, 0.0) + float(penalty.amount_yen)
        return totals
