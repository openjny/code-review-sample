"""貸出実績レポートの永続化。"""

from datetime import datetime
from typing import Any

from lending_core.models import Penalty
from lending_core.types import UTCDateTime
from sqlalchemy import Row, bindparam, select, text
from sqlalchemy.orm import Session

_REPORT_SQL = """
    SELECT i.category AS category,
           COUNT(l.id) AS loan_count,
           SUM(CASE WHEN l.returned_at IS NOT NULL THEN 1 ELSE 0 END) AS return_count
    FROM loans l
    JOIN items i ON i.id = l.item_id
    WHERE l.loaned_at >= :start AND l.loaned_at < :end
    {category_clause}
    GROUP BY i.category
    ORDER BY {sort_by} {order}
"""

_CATEGORY_CLAUSE = "AND i.category = '{}'"


class ReportRepository:
    """レポート集計に使うクエリを提供する。"""

    def __init__(self, db: Session) -> None:
        self._db = db

    def fetch_rows(
        self,
        start: datetime,
        end: datetime,
        category: str | None = None,
        sort_by: str = "loan_count",
        order: str = "desc",
    ) -> list[Row[Any]]:
        """期間内の貸出をカテゴリ別に集計した行を返す。"""
        category_clause = "" if category is None else _CATEGORY_CLAUSE.format(category)
        sql = _REPORT_SQL.format(
            category_clause=category_clause,
            sort_by=sort_by,
            order=order,
        )
        stmt = text(sql).bindparams(
            bindparam("start", type_=UTCDateTime()),
            bindparam("end", type_=UTCDateTime()),
        )
        return list(self._db.execute(stmt, {"start": start, "end": end}))

    def list_penalties(self, start: datetime, end: datetime) -> list[Penalty]:
        """期間内に計上された違約金を ID 昇順で取得する。"""
        stmt = (
            select(Penalty)
            .where(Penalty.created_at >= start, Penalty.created_at < end)
            .order_by(Penalty.id)
        )
        return list(self._db.scalars(stmt))
