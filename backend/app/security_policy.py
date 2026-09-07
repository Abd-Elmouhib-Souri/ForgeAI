from __future__ import annotations

from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken
from starlette.responses import Response

from app.config import settings


TOTP_SECRET_PREFIX = "fernet:v1:"

_LOCAL_ENVIRONMENTS = {
    "development",
    "dev",
    "local",
    "test",
    "testing",
}


class SecretProtectionError(RuntimeError):
    """Authentication secret protection failed."""


def should_use_secure_cookie(
    environment: str,
    frontend_url: str,
) -> bool:
    """
    Fail secure unless an explicit local/test environment is
    intentionally using HTTP.

    Local HTTPS remains Secure.
    """

    normalized_environment = (
        environment
        or ""
    ).strip().lower()

    normalized_frontend_url = (
        frontend_url
        or ""
    ).strip().lower()

    if normalized_environment in _LOCAL_ENVIRONMENTS:
        return normalized_frontend_url.startswith(
            "https://"
        )

    return True


def refresh_cookie_secure() -> bool:
    return should_use_secure_cookie(
        settings.ENVIRONMENT,
        settings.FRONTEND_URL,
    )


def _refresh_cookie_common() -> dict:
    return {
        "path": "/",
        "httponly": True,
        "samesite": "lax",
        "secure": refresh_cookie_secure(),
    }


def set_refresh_cookie(
    response: Response,
    refresh_token: str,
) -> None:

    max_age = (
        settings.REFRESH_TOKEN_EXPIRE_DAYS
        * 24
        * 3600
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=max_age,
        expires=max_age,
        **_refresh_cookie_common(),
    )


def delete_refresh_cookie(
    response: Response,
) -> None:

    response.delete_cookie(
        key="refresh_token",
        **_refresh_cookie_common(),
    )


def _fernet() -> Fernet:
    try:
        return Fernet(
            settings.AES_SECRET_KEY.encode(
                "ascii"
            )
        )
    except (
        UnicodeEncodeError,
        ValueError,
        TypeError,
    ) as exc:
        raise SecretProtectionError(
            "Invalid authentication secret protection key."
        ) from exc


def protect_totp_secret(
    plaintext_secret: str,
) -> str:

    if not plaintext_secret:
        raise SecretProtectionError(
            "TOTP secret cannot be empty."
        )

    encrypted = _fernet().encrypt(
        plaintext_secret.encode(
            "utf-8"
        )
    )

    protected = (
        TOTP_SECRET_PREFIX
        + encrypted.decode(
            "ascii"
        )
    )

    if len(protected) > 255:
        raise SecretProtectionError(
            "Protected TOTP secret exceeds storage capacity."
        )

    return protected


def reveal_totp_secret(
    stored_secret: str,
) -> str:

    if not stored_secret:
        raise SecretProtectionError(
            "TOTP secret is missing."
        )

    if not stored_secret.startswith(
        TOTP_SECRET_PREFIX
    ):
        raise SecretProtectionError(
            "Unsupported TOTP secret storage format."
        )

    encrypted = stored_secret[
        len(TOTP_SECRET_PREFIX):
    ]

    try:
        plaintext = _fernet().decrypt(
            encrypted.encode(
                "ascii"
            )
        )
    except (
        InvalidToken,
        UnicodeEncodeError,
        ValueError,
    ) as exc:
        raise SecretProtectionError(
            "Unable to recover protected TOTP secret."
        ) from exc

    try:
        return plaintext.decode(
            "utf-8"
        )
    except UnicodeDecodeError as exc:
        raise SecretProtectionError(
            "Recovered TOTP secret is invalid."
        ) from exc
