from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from fastapi import HTTPException
from starlette.responses import Response

from app.config import settings
import app.security as security_module

from app.security_policy import (
    SecretProtectionError,
    delete_refresh_cookie,
    protect_totp_secret,
    reveal_totp_secret,
    set_refresh_cookie,
    should_use_secure_cookie,
)


def _cookie_header(
    response: Response,
) -> str:

    return response.headers.get(
        "set-cookie",
        "",
    ).lower()


def test_totp_secret_runtime_roundtrip_and_fail_closed():
    plain = "JBSWY3DPEHPK3PXP"

    protected = protect_totp_secret(
        plain
    )

    assert protected != plain

    assert protected.startswith(
        "fernet:v1:"
    )

    assert len(protected) <= 255

    assert reveal_totp_secret(
        protected
    ) == plain

    replacement = (
        "A"
        if protected[-1] != "A"
        else "B"
    )

    tampered = (
        protected[:-1]
        + replacement
    )

    with pytest.raises(
        SecretProtectionError
    ):
        reveal_totp_secret(
            tampered
        )

    with pytest.raises(
        SecretProtectionError
    ):
        reveal_totp_secret(
            plain
        )

    with pytest.raises(
        SecretProtectionError
    ):
        reveal_totp_secret(
            ""
        )


def test_refresh_cookie_runtime_environment_semantics(
    monkeypatch,
):
    def exercise(
        environment: str,
        frontend_url: str,
    ):
        monkeypatch.setattr(
            settings,
            "ENVIRONMENT",
            environment,
        )

        monkeypatch.setattr(
            settings,
            "FRONTEND_URL",
            frontend_url,
        )

        set_response = Response()

        set_refresh_cookie(
            set_response,
            "synthetic-refresh-token",
        )

        delete_response = Response()

        delete_refresh_cookie(
            delete_response
        )

        return (
            _cookie_header(
                set_response
            ),
            _cookie_header(
                delete_response
            ),
        )

    production_set, production_delete = exercise(
        "production",
        "https://forge.example",
    )

    assert "secure" in production_set
    assert "secure" in production_delete
    assert "httponly" in production_set
    assert "httponly" in production_delete
    assert "samesite=lax" in production_set
    assert "samesite=lax" in production_delete
    assert "max-age=0" in production_delete

    unknown_set, unknown_delete = exercise(
        "unexpected-environment",
        "http://internal.invalid",
    )

    assert "secure" in unknown_set
    assert "secure" in unknown_delete

    local_set, local_delete = exercise(
        "development",
        "http://localhost:3000",
    )

    assert "secure" not in local_set
    assert "secure" not in local_delete

    local_https_set, local_https_delete = exercise(
        "development",
        "https://localhost:3000",
    )

    assert "secure" in local_https_set
    assert "secure" in local_https_delete

    assert should_use_secure_cookie(
        "production",
        "http://internal.invalid",
    )

    assert should_use_secure_cookie(
        "unexpected-environment",
        "http://internal.invalid",
    )

    assert not should_use_secure_cookie(
        "development",
        "http://localhost:3000",
    )


class _AsyncScalarResultStub:

    def __init__(
        self,
        user,
    ):
        self.user = user

    def scalar_one_or_none(
        self,
    ):
        return self.user


class _AsyncDbStub:

    def __init__(
        self,
        user,
    ):
        self.user = user
        self.execute_count = 0
        self.last_statement = None

    async def execute(
        self,
        statement,
    ):
        self.execute_count += 1
        self.last_statement = statement

        return _AsyncScalarResultStub(
            self.user
        )


async def _invoke_get_current_user(
    user,
):
    credentials = SimpleNamespace(
        credentials="synthetic-access-token"
    )

    db = _AsyncDbStub(
        user
    )

    result = await security_module.get_current_user(
        credentials=credentials,
        db=db,
    )

    return (
        result,
        db,
    )


def test_current_user_runtime_account_state(
    monkeypatch,
):
    decode_calls = []

    def fake_decode(
        token,
        key,
        algorithms,
    ):
        decode_calls.append(
            (
                token,
                key,
                tuple(algorithms),
            )
        )

        return {
            "sub": "security-test@example.invalid"
        }

    monkeypatch.setattr(
        security_module.jwt,
        "decode",
        fake_decode,
    )

    async def exercise():

        missing_db = _AsyncDbStub(
            None
        )

        credentials = SimpleNamespace(
            credentials="synthetic-access-token"
        )

        with pytest.raises(
            HTTPException
        ) as missing_exc:

            await security_module.get_current_user(
                credentials=credentials,
                db=missing_db,
            )

        assert (
            missing_exc.value.status_code
            == 401
        )

        assert (
            missing_db.execute_count
            == 1
        )


        inactive = SimpleNamespace(
            is_active=False,
            is_email_verified=True,
        )

        inactive_db = _AsyncDbStub(
            inactive
        )

        with pytest.raises(
            HTTPException
        ) as inactive_exc:

            await security_module.get_current_user(
                credentials=credentials,
                db=inactive_db,
            )

        assert (
            inactive_exc.value.status_code
            == 403
        )

        assert (
            inactive_db.execute_count
            == 1
        )


        unverified = SimpleNamespace(
            is_active=True,
            is_email_verified=False,
        )

        unverified_db = _AsyncDbStub(
            unverified
        )

        with pytest.raises(
            HTTPException
        ) as unverified_exc:

            await security_module.get_current_user(
                credentials=credentials,
                db=unverified_db,
            )

        assert (
            unverified_exc.value.status_code
            == 403
        )

        assert (
            unverified_db.execute_count
            == 1
        )


        valid = SimpleNamespace(
            is_active=True,
            is_email_verified=True,
        )

        resolved, valid_db = await _invoke_get_current_user(
            valid
        )

        assert resolved is valid

        assert (
            valid_db.execute_count
            == 1
        )


    asyncio.run(
        exercise()
    )

    assert len(
        decode_calls
    ) == 4

    for token, key, algorithms in decode_calls:

        assert token == (
            "synthetic-access-token"
        )

        assert key == (
            settings.JWT_SECRET_KEY
        )

        assert algorithms == (
            settings.JWT_ALGORITHM,
        )
