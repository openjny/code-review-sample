"""通知の抽象と既定実装。"""

import logging
from typing import NamedTuple, Protocol

logger = logging.getLogger(__name__)

MASKED_PLACEHOLDER = "***"


class Notification(NamedTuple):
    """送信する通知 1 件分の内容。"""

    to_email: str
    subject: str
    body: str


class Notifier(Protocol):
    """通知の送信手段を表すインタフェース。"""

    def send(self, notification: Notification) -> None:
        """通知を送信する。"""
        ...


def mask_email(email: str) -> str:
    """メールアドレスをログ出力用に伏字化する（例 ``m***@example.com``）。"""
    local, separator, domain = email.partition("@")
    if not separator or not local:
        return MASKED_PLACEHOLDER
    return f"{local[0]}{MASKED_PLACEHOLDER}@{domain}"


class LoggingNotifier:
    """通知内容をログへ出力するだけの実装。"""

    def send(self, notification: Notification) -> None:
        """通知をログへ出力する。宛先は伏字化する。"""
        logger.info(
            "通知を送信しました: to=%s subject=%s",
            mask_email(notification.to_email),
            notification.subject,
        )


def get_notifier() -> Notifier:
    """既定の Notifier を返す。"""
    return LoggingNotifier()
