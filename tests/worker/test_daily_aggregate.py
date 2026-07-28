"""日次集計ジョブ (lending_worker.jobs.daily_aggregate) の検証。"""

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta

import pytest
from lending_core.enums import ItemCategory, ItemStatus, LoanStatus, UserRole
from lending_core.models import Item, Loan, Penalty, User
from lending_worker.cache import aggregate_cache, aggregate_key
from lending_worker.jobs import daily_aggregate
from lending_worker.repositories.aggregate_repo import AggregateRepository
from sqlalchemy.orm import Session

TARGET_DATE = date(2026, 7, 1)
IN_DAY = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
OUT_OF_DAY = datetime(2026, 6, 30, 12, 0, tzinfo=UTC)
LOAN_PERIOD = timedelta(days=14)


@pytest.fixture(autouse=True)
def clear_aggregate_cache() -> Iterator[None]:
    """モジュールグローバルなキャッシュをテスト間で持ち越さない。"""
    aggregate_cache.clear()
    yield
    aggregate_cache.clear()


@pytest.fixture
def aggregated_data(db: Session) -> None:
    """対象日の内外にまたがる貸出・返却・違約金を用意する。"""
    user = User(email="user@example.com", name="集計 太郎", role=UserRole.MEMBER, is_active=True)
    db.add(user)
    db.flush()

    items = [
        Item(
            asset_code="AG-1",
            name="備品 1",
            category=ItemCategory.TOOL,
            status=ItemStatus.AVAILABLE,
            daily_fee_yen=300,
        ),
        Item(
            asset_code="AG-2",
            name="備品 2",
            category=ItemCategory.TOOL,
            status=ItemStatus.LOANED,
            daily_fee_yen=300,
        ),
        Item(
            asset_code="AG-3",
            name="備品 3",
            category=ItemCategory.EQUIPMENT,
            status=ItemStatus.LOANED,
            daily_fee_yen=500,
        ),
    ]
    db.add_all(items)
    db.flush()

    loans = [
        Loan(
            item_id=items[0].id,
            user_id=user.id,
            loaned_at=IN_DAY,
            due_at=IN_DAY + LOAN_PERIOD,
            returned_at=IN_DAY + timedelta(hours=2),
            extension_count=0,
            status=LoanStatus.RETURNED,
        ),
        Loan(
            item_id=items[1].id,
            user_id=user.id,
            loaned_at=IN_DAY,
            due_at=IN_DAY + LOAN_PERIOD,
            extension_count=0,
            status=LoanStatus.ACTIVE,
        ),
        Loan(
            item_id=items[2].id,
            user_id=user.id,
            loaned_at=OUT_OF_DAY,
            due_at=OUT_OF_DAY + LOAN_PERIOD,
            extension_count=0,
            status=LoanStatus.ACTIVE,
        ),
    ]
    db.add_all(loans)
    db.flush()

    db.add_all(
        [
            Penalty(loan_id=loans[0].id, amount_yen=300, reason="延滞違約金", created_at=IN_DAY),
            Penalty(loan_id=loans[1].id, amount_yen=150, reason="延滞違約金", created_at=IN_DAY),
            Penalty(
                loan_id=loans[2].id, amount_yen=999, reason="延滞違約金", created_at=OUT_OF_DAY
            ),
        ]
    )
    db.commit()


def _spy_on_repository(monkeypatch: pytest.MonkeyPatch) -> list[Session]:
    """AggregateRepository の生成回数を記録し、記録用リストを返す。"""
    calls: list[Session] = []

    def factory(session: Session) -> AggregateRepository:
        calls.append(session)
        return AggregateRepository(session)

    monkeypatch.setattr(daily_aggregate, "AggregateRepository", factory)
    return calls


def test_run_aggregates_only_the_target_day(db: Session, aggregated_data: None) -> None:
    summary = daily_aggregate.run(db, target_date=TARGET_DATE, use_cache=False)

    assert summary.target_date == TARGET_DATE
    assert summary.loans_created == 2
    assert summary.loans_returned == 1
    assert summary.penalty_total_yen == 450
    assert summary.items_by_status == {
        ItemStatus.AVAILABLE.value: 1,
        ItemStatus.LOANED.value: 2,
    }


def test_run_returns_zero_values_when_no_data_exists(db: Session) -> None:
    summary = daily_aggregate.run(db, target_date=TARGET_DATE, use_cache=False)

    assert summary.loans_created == 0
    assert summary.loans_returned == 0
    assert summary.penalty_total_yen == 0
    assert summary.items_by_status == {}


def test_run_defaults_to_the_previous_day(db: Session, frozen_clock) -> None:
    summary = daily_aggregate.run(db, use_cache=False)

    assert summary.target_date == frozen_clock.current.date() - timedelta(days=1)


def test_run_stores_the_result_in_the_cache(db: Session, aggregated_data: None) -> None:
    summary = daily_aggregate.run(db, target_date=TARGET_DATE)

    assert aggregate_cache.get(aggregate_key(TARGET_DATE)) is summary


def test_run_returns_cached_summary_without_recomputing(
    db: Session, aggregated_data: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _spy_on_repository(monkeypatch)

    first = daily_aggregate.run(db, target_date=TARGET_DATE)
    second = daily_aggregate.run(db, target_date=TARGET_DATE)

    assert second is first
    assert len(calls) == 1


def test_run_recomputes_when_use_cache_is_false(
    db: Session, aggregated_data: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _spy_on_repository(monkeypatch)

    first = daily_aggregate.run(db, target_date=TARGET_DATE)
    second = daily_aggregate.run(db, target_date=TARGET_DATE, use_cache=False)

    assert second is not first
    assert second == first
    assert len(calls) == 2
