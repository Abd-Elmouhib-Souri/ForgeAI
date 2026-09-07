from __future__ import annotations

import ast
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = BACKEND_ROOT / "app"


def _read(path: Path) -> str:
    return path.read_text(
        encoding="utf-8-sig",
        errors="strict",
    )


def _call_name(call: ast.Call) -> str:
    if isinstance(call.func, ast.Attribute):
        return call.func.attr

    if isinstance(call.func, ast.Name):
        return call.func.id

    return ""


def _keyword(call: ast.Call, name: str):
    for item in call.keywords:
        if item.arg == name:
            return item.value

    return None


def _constant_string(node):
    if (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
    ):
        return node.value

    return None


def test_refresh_token_cookie_is_not_hardcoded_insecure():
    """
    The refresh-token creation lifecycle must have one canonical
    low-level authority, and its observable production behavior must
    emit a Secure HttpOnly cookie.

    The contract validates behavior rather than requiring `secure=`
    to appear as an explicit keyword on the low-level cookie call.
    """

    from starlette.responses import Response

    from app.config import settings
    from app.security_policy import set_refresh_cookie

    policy_path = (
        APP_ROOT
        / "security_policy.py"
    ).resolve()

    low_level_calls = []

    for path in APP_ROOT.rglob("*.py"):
        tree = ast.parse(
            _read(path)
        )

        for node in ast.walk(tree):

            if not isinstance(
                node,
                ast.Call,
            ):
                continue

            if _call_name(node) != "set_cookie":
                continue

            key = _keyword(
                node,
                "key",
            )

            if (
                _constant_string(key)
                != "refresh_token"
            ):
                continue

            low_level_calls.append(
                (
                    path.resolve(),
                    node.lineno,
                )
            )

    assert low_level_calls, (
        "No low-level refresh-token "
        "creation authority found"
    )

    assert all(
        source_path == policy_path
        for source_path, _ in low_level_calls
    ), (
        "Refresh-token creation must be "
        "centralized in the canonical "
        "security policy: "
        + repr(low_level_calls)
    )

    original_environment = (
        settings.ENVIRONMENT
    )

    original_frontend_url = (
        settings.FRONTEND_URL
    )

    try:
        settings.ENVIRONMENT = "production"
        settings.FRONTEND_URL = (
            "https://forge.example"
        )

        response = Response()

        set_refresh_cookie(
            response,
            "synthetic-refresh-token",
        )

        header = response.headers.get(
            "set-cookie",
            "",
        ).lower()

        assert "refresh_token=" in header
        assert "secure" in header
        assert "httponly" in header
        assert "samesite=lax" in header

        settings.ENVIRONMENT = (
            "unexpected-environment"
        )

        settings.FRONTEND_URL = (
            "http://internal.invalid"
        )

        fail_secure_response = Response()

        set_refresh_cookie(
            fail_secure_response,
            "synthetic-refresh-token",
        )

        fail_secure_header = (
            fail_secure_response
            .headers
            .get(
                "set-cookie",
                "",
            )
            .lower()
        )

        assert "secure" in fail_secure_header

        settings.ENVIRONMENT = (
            "development"
        )

        settings.FRONTEND_URL = (
            "http://localhost:3000"
        )

        local_response = Response()

        set_refresh_cookie(
            local_response,
            "synthetic-refresh-token",
        )

        local_header = (
            local_response
            .headers
            .get(
                "set-cookie",
                "",
            )
            .lower()
        )

        assert "secure" not in local_header

    finally:
        settings.ENVIRONMENT = (
            original_environment
        )

        settings.FRONTEND_URL = (
            original_frontend_url
        )


def test_redirect_urls_do_not_transport_bearer_credentials():
    offenders = []

    forbidden = (
        "access_token",
        "refresh_token",
    )

    for path in APP_ROOT.rglob("*.py"):
        tree = ast.parse(_read(path))

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            if _call_name(node) != "RedirectResponse":
                continue

            url_node = _keyword(
                node,
                "url",
            )

            if (
                url_node is None
                and node.args
            ):
                url_node = node.args[0]

            if url_node is None:
                continue

            rendered = ast.unparse(
                url_node
            ).lower()

            if any(
                credential in rendered
                for credential in forbidden
            ):
                offenders.append(
                    (
                        path,
                        node.lineno,
                    )
                )

    assert not offenders, (
        "Bearer credentials must not be "
        "transported in redirect URLs: "
        + repr(offenders)
    )


def test_totp_secret_is_not_persisted_or_consumed_raw():
    raw_generated_names_by_function = {}
    direct_storage = []
    direct_consumption = []

    for path in APP_ROOT.rglob("*.py"):
        source = _read(path)
        tree = ast.parse(source)

        parents = {}

        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parents[child] = node

        def owner_function(node):
            current = node

            while current in parents:
                current = parents[current]

                if isinstance(
                    current,
                    (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                    ),
                ):
                    return current

            return None

        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue

            if not isinstance(
                node.value,
                ast.Call,
            ):
                continue

            rendered = ast.unparse(
                node.value
            ).lower()

            if "pyotp.random_base32" not in rendered:
                continue

            owner = owner_function(node)

            if owner is None:
                continue

            names = (
                raw_generated_names_by_function
                .setdefault(
                    (
                        str(path),
                        owner.name,
                    ),
                    set(),
                )
            )

            for target in node.targets:
                if isinstance(
                    target,
                    ast.Name,
                ):
                    names.add(
                        target.id
                    )

        for node in ast.walk(tree):
            if isinstance(
                node,
                (
                    ast.Assign,
                    ast.AnnAssign,
                ),
            ):
                targets = []

                if isinstance(
                    node,
                    ast.Assign,
                ):
                    targets = node.targets
                    value = node.value
                else:
                    targets = [node.target]
                    value = node.value

                for target in targets:
                    if not (
                        isinstance(
                            target,
                            ast.Attribute,
                        )
                        and target.attr
                        == "two_factor_secret"
                    ):
                        continue

                    owner = owner_function(node)

                    if owner is None:
                        continue

                    raw_names = (
                        raw_generated_names_by_function
                        .get(
                            (
                                str(path),
                                owner.name,
                            ),
                            set(),
                        )
                    )

                    if (
                        isinstance(
                            value,
                            ast.Name,
                        )
                        and value.id
                        in raw_names
                    ):
                        direct_storage.append(
                            (
                                path,
                                node.lineno,
                            )
                        )

            if not isinstance(
                node,
                ast.Call,
            ):
                continue

            rendered_function = (
                ast.unparse(node.func)
                .lower()
            )

            if not rendered_function.endswith(
                "pyotp.totp"
            ) and rendered_function != "pyotp.totp":
                continue

            if not node.args:
                continue

            first_arg = node.args[0]

            if (
                isinstance(
                    first_arg,
                    ast.Attribute,
                )
                and first_arg.attr
                == "two_factor_secret"
            ):
                direct_consumption.append(
                    (
                        path,
                        node.lineno,
                    )
                )

    assert not direct_storage, (
        "Raw generated TOTP secrets must not "
        "be persisted directly: "
        + repr(direct_storage)
    )

    assert not direct_consumption, (
        "Persistent TOTP secrets must pass "
        "through the protection authority "
        "before pyotp consumption: "
        + repr(direct_consumption)
    )


def test_secret_bearing_urls_are_not_logged():
    offenders = []

    logging_names = {
        "print",
        "debug",
        "info",
        "warning",
        "error",
        "exception",
        "critical",
    }

    for path in APP_ROOT.rglob("*.py"):
        source = _read(path)
        tree = ast.parse(source)

        for function in ast.walk(tree):
            if not isinstance(
                function,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ):
                continue

            tainted_names = set()

            for node in ast.walk(function):
                if not isinstance(
                    node,
                    (
                        ast.Assign,
                        ast.AnnAssign,
                    ),
                ):
                    continue

                value = node.value

                if value is None:
                    continue

                rendered = (
                    ast.unparse(value)
                    .lower()
                )

                carries_url_secret = (
                    "?token=" in rendered
                    or "?access_token=" in rendered
                    or "&token=" in rendered
                    or "&access_token=" in rendered
                )

                if not carries_url_secret:
                    continue

                targets = (
                    node.targets
                    if isinstance(
                        node,
                        ast.Assign,
                    )
                    else [node.target]
                )

                for target in targets:
                    if isinstance(
                        target,
                        ast.Name,
                    ):
                        tainted_names.add(
                            target.id
                        )

            if not tainted_names:
                continue

            for node in ast.walk(function):
                if not isinstance(
                    node,
                    ast.Call,
                ):
                    continue

                name = _call_name(node)

                if name not in logging_names:
                    continue

                referenced_names = {
                    item.id
                    for argument in node.args
                    for item in ast.walk(argument)
                    if isinstance(
                        item,
                        ast.Name,
                    )
                }

                leaked = (
                    referenced_names
                    & tainted_names
                )

                if leaked:
                    offenders.append(
                        (
                            path,
                            node.lineno,
                            sorted(leaked),
                        )
                    )

    assert not offenders, (
        "Secret-bearing URLs must never be "
        "written to application logs: "
        + repr(offenders)
    )


def test_authenticated_user_dependency_enforces_current_account_state():
    security_path = (
        BACKEND_ROOT
        / "app"
        / "security.py"
    )

    source = _read(
        security_path
    )

    tree = ast.parse(
        source
    )

    target = None

    for node in tree.body:
        if (
            isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
            and node.name
            == "get_current_user"
        ):
            target = node
            break

    assert target is not None, (
        "Canonical authenticated-user "
        "dependency get_current_user "
        "must exist"
    )

    return_user_lines = [
        node.lineno
        for node in ast.walk(target)
        if (
            isinstance(node, ast.Return)
            and isinstance(
                node.value,
                ast.Name,
            )
            and node.value.id == "user"
        )
    ]

    assert return_user_lines, (
        "get_current_user must return "
        "the resolved user"
    )

    first_return_line = min(
        return_user_lines
    )

    def has_denial_guard(
        attribute_name: str,
    ) -> bool:

        for node in ast.walk(target):

            if not isinstance(
                node,
                ast.If,
            ):
                continue

            if node.lineno >= first_return_line:
                continue

            referenced_attributes = {
                child.attr
                for child in ast.walk(
                    node.test
                )
                if isinstance(
                    child,
                    ast.Attribute,
                )
            }

            if (
                attribute_name
                not in referenced_attributes
            ):
                continue

            has_raise = any(
                isinstance(
                    child,
                    ast.Raise,
                )
                for statement in node.body
                for child in ast.walk(
                    statement
                )
            )

            if has_raise:
                return True

        return False

    assert has_denial_guard(
        "is_active"
    ), (
        "Authenticated requests must "
        "re-check the current account's "
        "active state before returning "
        "the user"
    )

    assert has_denial_guard(
        "is_email_verified"
    ), (
        "Authenticated requests must "
        "re-check the current account's "
        "email-verification state before "
        "returning the user"
    )


def test_refresh_token_cookie_deletion_is_not_hardcoded_insecure():
    """
    Refresh-token deletion belongs to the same canonical lifecycle as
    creation. The deletion response must preserve the security
    attributes required to address the same browser cookie.
    """

    from starlette.responses import Response

    from app.config import settings
    from app.security_policy import delete_refresh_cookie

    policy_path = (
        APP_ROOT
        / "security_policy.py"
    ).resolve()

    low_level_calls = []

    for path in APP_ROOT.rglob("*.py"):
        tree = ast.parse(
            _read(path)
        )

        for node in ast.walk(tree):

            if not isinstance(
                node,
                ast.Call,
            ):
                continue

            if _call_name(node) != "delete_cookie":
                continue

            key = _keyword(
                node,
                "key",
            )

            if (
                _constant_string(key)
                != "refresh_token"
            ):
                continue

            low_level_calls.append(
                (
                    path.resolve(),
                    node.lineno,
                )
            )

    assert low_level_calls, (
        "No low-level refresh-token "
        "deletion authority found"
    )

    assert all(
        source_path == policy_path
        for source_path, _ in low_level_calls
    ), (
        "Refresh-token deletion must be "
        "centralized in the canonical "
        "security policy: "
        + repr(low_level_calls)
    )

    original_environment = (
        settings.ENVIRONMENT
    )

    original_frontend_url = (
        settings.FRONTEND_URL
    )

    try:
        settings.ENVIRONMENT = "production"
        settings.FRONTEND_URL = (
            "https://forge.example"
        )

        response = Response()

        delete_refresh_cookie(
            response
        )

        header = response.headers.get(
            "set-cookie",
            "",
        ).lower()

        assert "refresh_token=" in header
        assert "max-age=0" in header
        assert "secure" in header
        assert "httponly" in header
        assert "samesite=lax" in header

        settings.ENVIRONMENT = (
            "unexpected-environment"
        )

        settings.FRONTEND_URL = (
            "http://internal.invalid"
        )

        fail_secure_response = Response()

        delete_refresh_cookie(
            fail_secure_response
        )

        fail_secure_header = (
            fail_secure_response
            .headers
            .get(
                "set-cookie",
                "",
            )
            .lower()
        )

        assert "secure" in fail_secure_header

        settings.ENVIRONMENT = (
            "development"
        )

        settings.FRONTEND_URL = (
            "http://localhost:3000"
        )

        local_response = Response()

        delete_refresh_cookie(
            local_response
        )

        local_header = (
            local_response
            .headers
            .get(
                "set-cookie",
                "",
            )
            .lower()
        )

        assert "secure" not in local_header

    finally:
        settings.ENVIRONMENT = (
            original_environment
        )

        settings.FRONTEND_URL = (
            original_frontend_url
        )
