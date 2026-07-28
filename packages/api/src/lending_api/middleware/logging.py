"""アクセスログ用ミドルウェア。"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

MILLISECONDS_PER_SECOND = 1000


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """リクエストのメソッド・パス・ステータス・所要時間を記録する。"""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """リクエストを処理し、アクセスログを出力する。"""
        started_at = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started_at) * MILLISECONDS_PER_SECOND
        logger.info(
            "%s %s %d %.1fms auth=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            request.headers.get("authorization"),
        )
        return response
