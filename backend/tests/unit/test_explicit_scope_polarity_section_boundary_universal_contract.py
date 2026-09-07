from __future__ import annotations

from app.schemas.analysis_context import (
    comparison_key,
)

from app.services.project_context_extractor import (
    ProjectContextExtractor,
)


def _packet(
    description: str,
    *,
    language: str = "en",
):
    return (
        ProjectContextExtractor()
        .extract(
            title="Neutral Scope Section Boundary",
            description=description,
            industry="Generic operations software",
            target_region="Global",
            output_language=language,
            project_context={},
            idea_readiness={},
            analysis_data={},
        )
    )


def _keys(
    values,
) -> list[str]:
    return [
        comparison_key(value)
        for value in values
        if comparison_key(value)
    ]


def _expected(
    *values: str,
) -> list[str]:
    return [
        comparison_key(value)
        for value in values
    ]


def test_en_does_not_include_heading_switches_scope_polarity() -> None:
    """
    A current explicit negative MVP heading owns the polarity of the
    structural rows that follow it.

    A positive section must stop when the negative heading begins.
    """

    packet = _packet(
        "A generic operations platform.\n"
        "MVP scope:\n"
        "- capability alpha\n"
        "- capability beta\n"
        "The MVP does NOT include:\n"
        "- capability gamma\n"
        "- capability delta\n"
        "Business objective:\n"
        "Reduce manual coordination."
    )

    assert _keys(
        packet.mvp_scope
    ) == _expected(
        "capability alpha",
        "capability beta",
    ), packet.mvp_scope

    assert _keys(
        packet.scope_exclusions
    ) == _expected(
        "capability gamma",
        "capability delta",
    ), packet.scope_exclusions


def test_fr_ninclut_pas_heading_switches_scope_polarity() -> None:
    """
    The same authority invariant applies independently of language.

    The French negative heading is expressed with unicode escapes so
    the contract itself remains ASCII-safe across PowerShell runtimes.
    """

    packet = _packet(
        "Une plateforme generique de gestion.\n"
        "P\u00e9rim\u00e8tre MVP :\n"
        "- capacite alpha\n"
        "- capacite beta\n"
        "Le MVP n'inclut pas :\n"
        "- capacite gamma\n"
        "- capacite delta\n"
        "Objectif metier :\n"
        "Reduire la coordination manuelle.",
        language="fr",
    )

    assert _keys(
        packet.mvp_scope
    ) == _expected(
        "capacite alpha",
        "capacite beta",
    ), packet.mvp_scope

    assert _keys(
        packet.scope_exclusions
    ) == _expected(
        "capacite gamma",
        "capacite delta",
    ), packet.scope_exclusions


def test_semantically_equivalent_negative_headings_have_equivalent_output() -> None:
    """
    Heading wording is syntax, not business truth.

    Two explicit ways of declaring the same negative MVP section must
    yield the same canonical positive and negative scope.
    """

    established = _packet(
        "A generic operations platform.\n"
        "MVP capabilities:\n"
        "- account access\n"
        "- record management\n"
        "Explicitly out of scope for the MVP:\n"
        "- automatic billing\n"
        "- payroll processing\n"
        "Business objective:\n"
        "Reduce manual coordination."
    )

    natural_language = _packet(
        "A generic operations platform.\n"
        "MVP capabilities:\n"
        "- account access\n"
        "- record management\n"
        "The MVP does NOT include:\n"
        "- automatic billing\n"
        "- payroll processing\n"
        "Business objective:\n"
        "Reduce manual coordination."
    )

    assert _keys(
        established.mvp_scope
    ) == _expected(
        "account access",
        "record management",
    ), established.mvp_scope

    assert _keys(
        established.scope_exclusions
    ) == _expected(
        "automatic billing",
        "payroll processing",
    ), established.scope_exclusions

    assert _keys(
        natural_language.mvp_scope
    ) == _keys(
        established.mvp_scope
    ), natural_language.mvp_scope

    assert _keys(
        natural_language.scope_exclusions
    ) == _keys(
        established.scope_exclusions
    ), natural_language.scope_exclusions


def test_non_scope_heading_terminates_explicit_negative_scope() -> None:
    """
    A following semantic section must terminate the scope section.

    Constraint rows are not MVP capabilities and are not MVP
    exclusions merely because they follow an exclusion section.
    """

    packet = _packet(
        "A generic operations platform.\n"
        "MVP capabilities:\n"
        "- capability alpha\n"
        "Explicitly out of scope for the MVP:\n"
        "- capability gamma\n"
        "Important constraints:\n"
        "- encrypted storage\n"
        "- audit logging\n"
        "Business objective:\n"
        "Reduce manual coordination."
    )

    assert _keys(
        packet.mvp_scope
    ) == _expected(
        "capability alpha",
    ), packet.mvp_scope

    assert _keys(
        packet.scope_exclusions
    ) == _expected(
        "capability gamma",
    ), packet.scope_exclusions

    all_scope = set(
        _keys(packet.mvp_scope)
        +
        _keys(packet.scope_exclusions)
    )

    assert comparison_key(
        "encrypted storage"
    ) not in all_scope

    assert comparison_key(
        "audit logging"
    ) not in all_scope


def test_established_explicit_out_of_scope_heading_remains_supported() -> None:
    """
    Preservation control.

    The new contract must not redefine the already-supported explicit
    out-of-scope syntax or introduce project-specific behavior.
    """

    packet = _packet(
        "A generic operations platform.\n"
        "MVP capabilities:\n"
        "- capability alpha\n"
        "- capability beta\n"
        "Explicitly out of scope for the MVP:\n"
        "- capability gamma\n"
        "- capability delta\n"
        "Business objective:\n"
        "Reduce manual coordination."
    )

    assert _keys(
        packet.mvp_scope
    ) == _expected(
        "capability alpha",
        "capability beta",
    ), packet.mvp_scope

    assert _keys(
        packet.scope_exclusions
    ) == _expected(
        "capability gamma",
        "capability delta",
    ), packet.scope_exclusions