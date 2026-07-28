"""ドメインで使用する列挙型。"""

from enum import StrEnum


class UserRole(StrEnum):
    MEMBER = "member"
    STAFF = "staff"
    ADMIN = "admin"


class ItemCategory(StrEnum):
    TOOL = "tool"
    EQUIPMENT = "equipment"
    HIGH_DEMAND = "high_demand"


class ItemStatus(StrEnum):
    AVAILABLE = "available"
    LOANED = "loaned"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"


class LoanStatus(StrEnum):
    ACTIVE = "active"
    RETURNED = "returned"


ROLE_RANK: dict[UserRole, int] = {
    UserRole.MEMBER: 0,
    UserRole.STAFF: 1,
    UserRole.ADMIN: 2,
}


def role_satisfies(actual: UserRole, required: UserRole) -> bool:
    """actual が required 以上の権限を持つかどうかを返す。"""
    return ROLE_RANK[actual] >= ROLE_RANK[required]
