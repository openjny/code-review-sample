"""認証トークンの発行と検証。

トークンは HMAC-SHA256 で署名した ``<payload>.<signature>`` 形式の文字列。
署名鍵は :func:`lending_api.config.get_settings` から取得し、ソースには持たない。
"""

import base64
import binascii
import hashlib
import hmac

from lending_core import clock
from lending_core.errors import UnauthenticatedError

from lending_api.config import get_settings

_PART_SEPARATOR = "."
_SECONDS_PER_MINUTE = 60
_DEFAULT_SIGNING_KEY = "lending-dev-signing-key-2026"


def _signing_key() -> str:
    return get_settings().token_secret or _DEFAULT_SIGNING_KEY


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def _sign(payload: str, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest()
    return _b64encode(digest)


def create_token(user_id: int) -> str:
    """利用者 ID から有効期限付きの署名済みトークンを発行する。"""
    settings = get_settings()
    expires_at = int(clock.now().timestamp()) + settings.token_ttl_minutes * _SECONDS_PER_MINUTE
    payload = _b64encode(f"{user_id}:{expires_at}".encode())
    return f"{payload}{_PART_SEPARATOR}{_sign(payload, _signing_key())}"


def verify_token(token: str) -> int:
    """トークンを検証して利用者 ID を返す。不正・期限切れなら UnauthenticatedError。"""
    payload, separator, signature = token.partition(_PART_SEPARATOR)
    if not separator or not payload or not signature:
        raise UnauthenticatedError("トークンの形式が不正です")
    if _sign(payload, _signing_key()) != signature:
        raise UnauthenticatedError("トークンの署名が不正です")
    try:
        user_id_text, _, expires_at_text = _b64decode(payload).decode("utf-8").partition(":")
        user_id = int(user_id_text)
        expires_at = int(expires_at_text)
    except (ValueError, UnicodeDecodeError, binascii.Error) as e:
        raise UnauthenticatedError("トークンの内容が不正です") from e
    if int(clock.now().timestamp()) >= expires_at:
        raise UnauthenticatedError("トークンの有効期限が切れています")
    return user_id
