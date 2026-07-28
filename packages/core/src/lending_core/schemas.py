"""Pydantic スキーマ（API の入出力）。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from lending_core.enums import ItemCategory, ItemStatus, LoanStatus, UserRole


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=100)
    role: UserRole = UserRole.MEMBER


class UserRead(ORMModel):
    id: int
    email: str
    name: str
    role: UserRole
    is_active: bool


class ItemCreate(BaseModel):
    asset_code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    category: ItemCategory = ItemCategory.TOOL
    daily_fee_yen: int = Field(default=0, ge=0)


class ItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category: ItemCategory | None = None
    status: ItemStatus | None = None
    daily_fee_yen: int | None = Field(default=None, ge=0)


class ItemRead(ORMModel):
    id: int
    asset_code: str
    name: str
    category: ItemCategory
    status: ItemStatus
    daily_fee_yen: int
    created_at: datetime


class LoanCreate(BaseModel):
    item_id: int


class LoanRead(ORMModel):
    id: int
    item_id: int
    user_id: int
    loaned_at: datetime
    due_at: datetime
    returned_at: datetime | None
    extension_count: int
    status: LoanStatus
    is_overdue: bool = False


class PenaltyRead(ORMModel):
    id: int
    loan_id: int
    amount_yen: int
    reason: str
    created_at: datetime


class ReportRow(ORMModel):
    category: ItemCategory
    loan_count: int
    return_count: int
    penalty_total: float


class ReportSummary(BaseModel):
    start: datetime
    end: datetime
    rows: list[ReportRow]
    penalty_total: float


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
