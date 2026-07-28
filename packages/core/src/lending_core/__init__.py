"""備品貸出管理システムのドメイン層。"""

from lending_core.enums import ItemCategory, ItemStatus, LoanStatus, UserRole
from lending_core.errors import (
    DomainError,
    ExtensionLimitExceededError,
    ItemNotAvailableError,
    LoanAlreadyReturnedError,
    NotFoundError,
    PermissionDeniedError,
)

__all__ = [
    "DomainError",
    "ExtensionLimitExceededError",
    "ItemCategory",
    "ItemNotAvailableError",
    "ItemStatus",
    "LoanAlreadyReturnedError",
    "LoanStatus",
    "NotFoundError",
    "PermissionDeniedError",
    "UserRole",
]
