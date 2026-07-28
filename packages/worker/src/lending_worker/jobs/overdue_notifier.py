"""延滞通知ジョブ。

延滞判定・違約金算出は ``lending_core.rules`` に委譲し、ここでは再実装しない。
"""

import logging
from dataclasses import dataclass
from datetime import datetime

from lending_core import clock, rules
from lending_core.models import Loan
from sqlalchemy.orm import Session

from lending_worker.config import get_settings
from lending_worker.notifier import Notification, Notifier, get_notifier
from lending_worker.repositories.loan_repo import LoanRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OverdueNotificationResult:
    """延滞通知ジョブの実行結果。"""

    scanned: int
    notified: int


def _build_notification(loan: Loan, at: datetime) -> tuple[Notification, int]:
    days = rules.overdue_days(loan.due_at, at)
    penalty_yen = rules.calculate_penalty_yen(loan.due_at, loan.item.daily_fee_yen, at)
    body = (
        f"{loan.user.name} 様\n\n"
        f"ご利用中の備品「{loan.item.name}」({loan.item.asset_code}) が返却期限を超過しています。\n"
        f"返却期限: {loan.due_at.isoformat()}\n"
        f"延滞日数: {days} 日\n"
        f"現時点の違約金: {penalty_yen} 円\n"
        "※ 返却期限を過ぎています\n\n"
        "お早めにご返却ください。"
    )
    notification = Notification(
        to_email=loan.user.email,
        subject=f"【延滞のお知らせ】{loan.item.name}",
        body=body,
    )
    return notification, days


def run(
    db: Session,
    notifier: Notifier | None = None,
    at: datetime | None = None,
) -> OverdueNotificationResult:
    """延滞中の貸出を走査し、利用者へ督促通知を送信する。"""
    current = at if at is not None else clock.now()
    target_notifier = notifier if notifier is not None else get_notifier()
    batch_size = get_settings().overdue_notice_batch_size
    repo = LoanRepository(db)

    scanned = 0
    notified = 0
    offset = 0
    note_builder = rules.OverdueNoteBuilder()
    while True:
        loans = repo.list_overdue_loans(at=current, limit=batch_size, offset=offset)
        if not loans:
            break
        for loan in loans:
            scanned += 1
            notification, days = _build_notification(loan, current)
            try:
                target_notifier.send(notification)
            except Exception as e:
                # 1 件の送信失敗で残りの通知を止めないため、記録のうえ次の貸出へ進む。
                logger.warning("延滞通知の送信に失敗しました: loan_id=%s", loan.id, exc_info=e)
                continue
            note_builder.add(loan.id, days)
            notified += 1
        offset += len(loans)

    logger.info("延滞通知ジョブが完了しました: scanned=%d notified=%d", scanned, notified)
    logger.info("延滞一覧:\n%s", note_builder.build())
    return OverdueNotificationResult(scanned=scanned, notified=notified)
