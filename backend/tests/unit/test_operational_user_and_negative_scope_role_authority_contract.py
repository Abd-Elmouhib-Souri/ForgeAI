from __future__ import annotations

from app.services.project_context_extractor import (
    comparison_key,
    project_context_extractor,
)
from app.services.scope_polarity import (
    is_scope_exclusion_statement,
)


def _extract(
    description: str,
    *,
    language: str = "fr",
):
    return project_context_extractor.extract(
        title="WorkFlowX",
        description=description,
        industry="B2B SaaS / Workforce Operations",
        target_region=(
            "France"
            if language == "fr"
            else "United Kingdom"
        ),
        output_language=language,
    )


def _actor_rows(packet):
    rows = []

    for actor in (
        packet.actors
        or []
    ):
        if isinstance(actor, dict):
            name = actor.get("name")
            role = actor.get("role")
        else:
            name = getattr(
                actor,
                "name",
                None,
            )

            raw_role = getattr(
                actor,
                "role",
                None,
            )

            role = getattr(
                raw_role,
                "value",
                raw_role,
            )

        if name:
            rows.append(
                (
                    str(name),
                    str(role or ""),
                )
            )

    return rows


def _role_for(
    packet,
    expected_name: str,
):
    expected_key = comparison_key(
        expected_name
    )

    return {
        comparison_key(name):
            role
        for name, role
        in _actor_rows(packet)
    }.get(
        expected_key
    )


def _payer_keys(packet):
    return {
        comparison_key(value)
        for value in (
            packet.payer_actor_names
            or []
        )
        if comparison_key(value)
    }


def test_french_primary_operational_user_declaration_materializes_actor() -> None:
    packet = _extract(
        (
            "WorkFlowX est un logiciel SaaS B2B. "
            "L\u2019utilisateur op\u00e9rationnel principal "
            "de WorkFlowX est le superviseur d\u2019\u00e9quipe. "
            "Le superviseur utilise la plateforme chaque jour "
            "pour publier les plannings."
        )
    )

    role = _role_for(
        packet,
        "superviseur d\u2019\u00e9quipe",
    )

    assert role in {
        "user",
        "operator",
        "beneficiary",
    }, _actor_rows(packet)


def test_english_primary_operational_user_declaration_materializes_actor() -> None:
    packet = _extract(
        (
            "WorkFlowX is a B2B SaaS product. "
            "The primary operational user of WorkFlowX "
            "is the shift supervisor. "
            "The supervisor uses the platform every day "
            "to publish schedules."
        ),
        language="en",
    )

    role = _role_for(
        packet,
        "shift supervisor",
    )

    assert role in {
        "user",
        "operator",
        "beneficiary",
    }, _actor_rows(packet)


def test_french_secondary_user_declaration_materializes_actor() -> None:
    packet = _extract(
        (
            "WorkFlowX est un logiciel SaaS B2B. "
            "Les employ\u00e9s sont des utilisateurs secondaires. "
            "Ils consultent leur planning dans la plateforme."
        )
    )

    role = _role_for(
        packet,
        "employ\u00e9s",
    )

    assert role in {
        "user",
        "operator",
        "beneficiary",
    }, _actor_rows(packet)


def test_english_secondary_user_declaration_materializes_actor() -> None:
    packet = _extract(
        (
            "WorkFlowX is a B2B SaaS product. "
            "Employees are secondary users. "
            "They view their schedules in the platform."
        ),
        language="en",
    )

    role = _role_for(
        packet,
        "Employees",
    )

    assert role in {
        "user",
        "operator",
        "beneficiary",
    }, _actor_rows(packet)


def test_multiline_negative_scope_block_cannot_create_bogus_payer() -> None:
    description = (
        "WorkFlowX est un logiciel SaaS B2B. "
        "L\u2019entreprise cliente paie un abonnement mensuel.\n\n"
        "Le MVP ne comprend pas :\n"
        "- la gestion de la paie ;\n"
        "- le recrutement ;\n"
        "- la gestion comptable."
    )

    sentences = (
        project_context_extractor
        ._sentences(description)
    )

    exclusion_sentences = [
        sentence
        for sentence in sentences
        if is_scope_exclusion_statement(
            sentence
        )
    ]

    assert exclusion_sentences, sentences

    packet = _extract(
        description
    )

    payer_keys = _payer_keys(
        packet
    )

    assert (
        comparison_key(
            "entreprise cliente"
        )
        in payer_keys
    ), packet.payer_actor_names

    assert all(
        "gestion de la"
        not in payer_key
        for payer_key in payer_keys
    ), packet.payer_actor_names

    assert all(
        not (
            role == "payer"
            and "gestion de la"
            in comparison_key(name)
        )
        for name, role
        in _actor_rows(packet)
    ), _actor_rows(packet)


def test_direct_negative_scope_payment_noun_cannot_create_payer() -> None:
    description = (
        "WorkFlowX est un logiciel SaaS B2B. "
        "Le MVP ne comprend pas la gestion de la paie."
    )

    assert (
        is_scope_exclusion_statement(
            "Le MVP ne comprend pas la gestion de la paie."
        )
        is True
    )

    packet = _extract(
        description
    )

    assert not (
        packet.payer_actor_names
        or []
    ), packet.payer_actor_names

    assert all(
        role != "payer"
        for _, role
        in _actor_rows(packet)
    ), _actor_rows(packet)


def test_positive_french_payment_predicate_remains_authoritative() -> None:
    packet = _extract(
        (
            "WorkFlowX est un logiciel SaaS B2B. "
            "L\u2019entreprise industrielle cliente "
            "paie un abonnement mensuel par site."
        )
    )

    payer_keys = _payer_keys(
        packet
    )

    assert (
        comparison_key(
            "entreprise industrielle cliente"
        )
        in payer_keys
    ), packet.payer_actor_names


def test_positive_operational_actor_survives_unrelated_scope_exclusion() -> None:
    packet = _extract(
        (
            "WorkFlowX est un logiciel SaaS B2B. "
            "L\u2019utilisateur op\u00e9rationnel principal "
            "de WorkFlowX est le superviseur d\u2019\u00e9quipe. "
            "Le MVP ne comprend pas la gestion de la paie."
        )
    )

    role = _role_for(
        packet,
        "superviseur d\u2019\u00e9quipe",
    )

    assert role in {
        "user",
        "operator",
        "beneficiary",
    }, _actor_rows(packet)



def test_positive_payment_before_same_sentence_scope_exclusion_remains_authoritative() -> None:
    packet = _extract(
        (
            "L\u2019entreprise cliente paie un abonnement mensuel ; "
            "le MVP ne comprend pas la gestion de la paie."
        )
    )

    payer_keys = _payer_keys(
        packet
    )

    assert (
        comparison_key(
            "entreprise cliente"
        )
        in payer_keys
    ), packet.payer_actor_names

    assert all(
        "mvp ne comprend pas"
        not in value
        and "gestion de la"
        not in value
        for value in payer_keys
    ), packet.payer_actor_names
