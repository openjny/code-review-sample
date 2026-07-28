"""日次集計ジョブ。"""

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from lending_core import clock
from sqlalchemy.orm import Session

from lending_worker.cache import aggregate_cache, aggregate_key
from lending_worker.repositories.aggregate_repo import AggregateRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DailySummary:
    """1 日分の集計結果。"""

    target_date: date
    loans_created: int
    loans_returned: int
    penalty_total_yen: int
    items_by_status: dict[str, int]


def _utc_day_range(target_date: date) -> tuple[datetime, datetime]:
    start = datetime.combine(target_date, time.min, tzinfo=UTC)
    return start, start + timedelta(days=1)


def run(db: Session, target_date: date | None = None, use_cache: bool = True) -> DailySummary:
    """対象日の貸出・返却・違約金・備品状態を集計する。既定の対象日は前日 (UTC)。"""
    day = target_date if target_date is not None else (clock.now().date() - timedelta(days=1))
    key = aggregate_key(day)

    if use_cache:
        cached = aggregate_cache.get(key)
        if cached is not None:
            logger.info("日次集計をキャッシュから取得しました: target_date=%s", day.isoformat())
            return cached

    start, end = _utc_day_range(day)
    repo = AggregateRepository(db)
    items_by_status = {
        status.value: count for status, count in repo.count_items_by_status().items()
    }
    summary = DailySummary(
        target_date=day,
        loans_created=repo.count_loans_created_between(start, end),
        loans_returned=repo.count_loans_returned_between(start, end),
        penalty_total_yen=repo.sum_penalty_yen_between(start, end),
        items_by_status=items_by_status,
    )

    aggregate_cache.set(key, summary)
    logger.info("日次集計が完了しました: target_date=%s", day.isoformat())
    return summary
