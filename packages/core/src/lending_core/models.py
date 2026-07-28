"""SQLAlchemy モデル定義。"""

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from lending_core import clock
from lending_core.enums import ItemCategory, ItemStatus, LoanStatus, UserRole
from lending_core.types import UTCDateTime, enum_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[UserRole] = mapped_column(enum_column(UserRole), default=UserRole.MEMBER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=clock.now)

    loans: Mapped[list["Loan"]] = relationship(back_populates="user")


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (UniqueConstraint("asset_code", name="uq_items_asset_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_code: Mapped[str] = mapped_column(String(50), index=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[ItemCategory] = mapped_column(
        enum_column(ItemCategory), default=ItemCategory.TOOL
    )
    status: Mapped[ItemStatus] = mapped_column(
        enum_column(ItemStatus), default=ItemStatus.AVAILABLE
    )
    daily_fee_yen: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=clock.now)

    loans: Mapped[list["Loan"]] = relationship(back_populates="item")


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    loaned_at: Mapped[datetime] = mapped_column(UTCDateTime, default=clock.now)
    due_at: Mapped[datetime] = mapped_column(UTCDateTime)
    returned_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    extension_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[LoanStatus] = mapped_column(enum_column(LoanStatus), default=LoanStatus.ACTIVE)

    item: Mapped[Item] = relationship(back_populates="loans")
    user: Mapped[User] = relationship(back_populates="loans")
    penalties: Mapped[list["Penalty"]] = relationship(back_populates="loan")


class Penalty(Base):
    __tablename__ = "penalties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    loan_id: Mapped[int] = mapped_column(ForeignKey("loans.id"), index=True)
    amount_yen: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=clock.now)

    loan: Mapped[Loan] = relationship(back_populates="penalties")
