"""FastAPI アプリケーションの構築。"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from lending_api import API_PREFIX
from lending_api.config import get_settings
from lending_api.db import init_db
from lending_api.errors import register_exception_handlers
from lending_api.middleware.logging import RequestLoggingMiddleware
from lending_api.routers import items, loans, reports, users


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """起動時にテーブルを作成する。"""
    init_db()
    yield


def create_app() -> FastAPI:
    """FastAPI アプリケーションを生成する。"""
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    app = FastAPI(title="備品貸出管理システム API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(RequestLoggingMiddleware)
    register_exception_handlers(app)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        """ヘルスチェック。認可不要。"""
        return {"status": "ok"}

    app.include_router(items.router, prefix=API_PREFIX)
    app.include_router(loans.router, prefix=API_PREFIX)
    app.include_router(users.router, prefix=API_PREFIX)
    app.include_router(reports.router, prefix=API_PREFIX)
    return app


app = create_app()
