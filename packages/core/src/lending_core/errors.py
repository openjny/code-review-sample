"""ドメイン例外。

API 層はこれらを捕捉して HTTP レスポンスへ変換する。
"""


class DomainError(Exception):
    """業務エラーの基底クラス。"""

    code: str = "DOMAIN_ERROR"
    http_status: int = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    code = "NOT_FOUND"
    http_status = 404


class PermissionDeniedError(DomainError):
    code = "FORBIDDEN"
    http_status = 403


class UnauthenticatedError(DomainError):
    code = "UNAUTHENTICATED"
    http_status = 401


class ValidationError(DomainError):
    code = "VALIDATION_ERROR"
    http_status = 400


class ItemNotAvailableError(DomainError):
    code = "ITEM_NOT_AVAILABLE"
    http_status = 409


class ExtensionLimitExceededError(DomainError):
    code = "EXTENSION_LIMIT_EXCEEDED"
    http_status = 409


class LoanAlreadyReturnedError(DomainError):
    code = "LOAN_ALREADY_RETURNED"
    http_status = 409
