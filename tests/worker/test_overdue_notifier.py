"""延滞通知ジョブ (lending_worker.jobs.overdue_notifier) の検証。"""

from datetime import UTC, datetime, timedelta

import pytest
from lending_core.enums import ItemCategory, ItemStatus, LoanStatus, UserRole
from lending_core.models import Item, Loan, User
from lending_worker.config import get_settings
from lending_worker.jobs import overdue_notifier
from lending_worker.notifier import Notification
from sqlalchemy.orm import Session

NOW = datetime(2026, 7, 20, 9, 0, tzinfo=UTC)
DAILY_FEE_YEN = 300


class RecordingNotifier:
    """送信された通知を記録するテスト用 Notifier。"""

    def __init__(self) -> None:
        self.sent: list[Notification] = []

    def send(self, notification: Notification) -> None:
        """通知を記録する。"""
        self.sent.append(notification)


@pytest.fixture
def notifier() -> RecordingNotifier:
    """送信内容を検証するための Notifier。"""
    return RecordingNotifier()


@pytest.fixture
def borrower(db: Session) -> User:
    """貸出中の利用者。"""
    user = User(
        email="borrower@example.com", name="借主 太郎", role=UserRole.MEMBER, is_active=True
    )
    db.add(user)
    db.commit()
    return user


def _create_loan(
    db: Session,
    user: User,
    *,
    asset_code: str,
    due_at: datetime,
    returned_at: datetime | None = None,
    status: LoanStatus = LoanStatus.ACTIVE,
    daily_fee_yen: int = DAILY_FEE_YEN,
) -> Loan:
    item = Item(
        asset_code=asset_code,
        name=f"備品 {asset_code}",
        category=ItemCategory.TOOL,
        status=ItemStatus.LOANED,
        daily_fee_yen=daily_fee_yen,
    )
    db.add(item)
    db.flush()
    loan = Loan(
        item_id=item.id,
        user_id=user.id,
        loaned_at=due_at - timedelta(days=14),
        due_at=due_at,
        returned_at=returned_at,
        extension_count=0,
        status=status,
    )
    db.add(loan)
    db.commit()
    return loan


def test_only_overdue_loans_are_notified(
    db: Session, borrower: User, notifier: RecordingNotifier
) -> None:
    overdue = _create_loan(db, borrower, asset_code="OVERDUE-1", due_at=NOW - timedelta(days=1))
    _create_loan(db, borrower, asset_code="FUTURE-1", due_at=NOW + timedelta(days=1))
    _create_loan(db, borrower, asset_code="EXACT-1", due_at=NOW)

    result = overdue_notifier.run(db, notifier=notifier, at=NOW)

    assert result.scanned == 1
    assert result.notified == 1
    assert [notification.to_email for notification in notifier.sent] == [borrower.email]
    assert overdue.item.asset_code == "OVERDUE-1"


def test_returned_loans_are_not_notified(
    db: Session, borrower: User, notifier: RecordingNotifier
) -> None:
    _create_loan(
        db,
        borrower,
        asset_code="RETURNED-1",
        due_at=NOW - timedelta(days=5),
        returned_at=NOW - timedelta(days=1),
        status=LoanStatus.RETURNED,
    )

    result = overdue_notifier.run(db, notifier=notifier, at=NOW)

    assert result.scanned == 0
    assert notifier.sent == []


def test_notification_contains_overdue_days_and_penalty(
    db: Session, borrower: User, notifier: RecordingNotifier
) -> None:
    _create_loan(db, borrower, asset_code="OVERDUE-2", due_at=NOW - timedelta(days=2))

    overdue_notifier.run(db, notifier=notifier, at=NOW)

    body = notifier.sent[0].body
    assert "延滞日数: 2 日" in body
    # 日額 300 円 × 2 日 × 違約金率 0.5 = 300 円
    assert "現時点の違約金: 300 円" in body
    assert "備品 OVERDUE-2" in body
    assert borrower.name in body


def test_all_loans_are_processed_across_batches(
    db: Session,
    borrower: User,
    notifier: RecordingNotifier,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LENDING_OVERDUE_NOTICE_BATCH_SIZE", "2")
    get_settings.cache_clear()
    loan_count = 5
    for index in range(loan_count):
        _create_loan(db, borrower, asset_code=f"BATCH-{index}", due_at=NOW - timedelta(days=1))

    result = overdue_notifier.run(db, notifier=notifier, at=NOW)

    assert get_settings().overdue_notice_batch_size == 2
    assert result.scanned == loan_count
    assert result.notified == loan_count
    assert len(notifier.sent) == loan_count


def test_send_failure_does_not_stop_remaining_notifications(db: Session, borrower: User) -> None:
    class FailingOnceNotifier(RecordingNotifier):
        def send(self, notification: Notification) -> None:
            if len(self.sent) == 0:
                self.sent.append(notification)
                raise RuntimeError("送信に失敗しました")
            self.sent.append(notification)

    for index in range(3):
        _create_loan(db, borrower, asset_code=f"FAIL-{index}", due_at=NOW - timedelta(days=1))
    failing = FailingOnceNotifier()

    result = overdue_notifier.run(db, notifier=failing, at=NOW)

    assert result.scanned == 3
    assert result.notified == 2
