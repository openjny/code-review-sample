"""アプリケーション設定。

秘密情報は環境変数 (prefix ``LENDING_``) から読み込み、ソースにハードコードしない。
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_PAGE_LIMIT = 50
MAX_PAGE_LIMIT = 100


class Settings(BaseSettings):
    """環境変数から読み込むアプリケーション設定。"""

    model_config = SettingsConfigDict(env_prefix="LENDING_", extra="ignore")

    database_url: str = "sqlite+pysqlite:///./lending.db"
    token_secret: str = Field(description="トークン署名鍵 (LENDING_TOKEN_SECRET)")
    token_ttl_minutes: int = 60
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """設定を取得する。プロセス内でキャッシュされる。"""
    return Settings()
