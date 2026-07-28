"""SQLAlchemy のカスタム型。"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, TypeDecorator
from sqlalchemy import Enum as SAEnum
from sqlalchemy.engine import Dialect


class UTCDateTime(TypeDecorator[datetime]):
    """tz-aware な UTC の datetime を保証する型。

    SQLite など timezone を保持しないバックエンドでも、読み書きの両方で UTC を維持する。
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime は保存できません。lending_core.clock.now() を使うこと")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def enum_column(enum_type: type[Any]) -> SAEnum:
    """StrEnum を値そのもの (小文字) で永続化するカラム型を返す。"""
    return SAEnum(
        enum_type,
        native_enum=False,
        length=20,
        values_callable=lambda members: [member.value for member in members],
    )
