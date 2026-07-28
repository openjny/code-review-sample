"""例外ハンドラの登録。"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from lending_core.errors import DomainError, ValidationError
from lending_core.schemas import ErrorBody, ErrorResponse

logger = logging.getLogger(__name__)


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=code, message=message))
    return JSONResponse(status_code=status_code, content=body.model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    """ドメイン例外とリクエスト検証エラーを共通のエラー形式へ変換する。"""

    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        logger.info("domain error %s on %s %s", exc.code, request.method, request.url.path)
        return _error_response(exc.http_status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        logger.info("validation error on %s %s", request.method, request.url.path)
        return _error_response(
            ValidationError.http_status, ValidationError.code, "リクエストの内容が不正です"
        )
