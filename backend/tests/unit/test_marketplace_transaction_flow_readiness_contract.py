import pytest

from app.services.context_confidence_gate import (
    context_confidence_gate,
)
from app.services.project_context_extractor import (
    project_context_extractor,
)


def extract(
    description: str,
    *,
    language: str,
):
    return (
        project_context_extractor
        .extract(
            title="FlowContract",
            description=description,
            industry=(
                "two-sided marketplace"
            ),
            target_region="Europe",
            output_language=language,
        )
    )


@pytest.mark.parametrize(
    (
        "description",
        "language",
    ),
    (
        (
            (
                "Le probleme est un processus fragmente. "
                "La plateforme met en relation deux cotes. "
                "Le premier cote est constitue de fournisseurs. "
                "Le second cote est constitue de clients. "
                "Le workflow principal est le suivant : "
                "un fournisseur publie une offre. "
                "Un client envoie une demande. "
                "La transaction est ensuite cloturee. "
                "L'unite de transaction principale est "
                "une reservation de service."
            ),
            "fr",
        ),
        (
            (
                "The current process is fragmented. "
                "The platform connects two sides. "
                "The first side consists of providers. "
                "The second side consists of customers. "
                "The main workflow is as follows: "
                "a provider publishes an offer. "
                "A customer sends a request. "
                "The transaction is then closed. "
                "The primary transaction unit is "
                "a service booking."
            ),
            "en",
        ),
    ),
)
def test_explicit_unit_with_start_and_end_resolves_flow(
    description,
    language,
):
    packet = extract(
        description,
        language=language,
    )

    transaction = (
        packet.transaction_unit
    )

    assert transaction.is_explicit

    assert (
        transaction.initiation_action
    )

    assert (
        transaction.completion_action
    )

    assert (
        "transaction_flow"
        not in (
            context_confidence_gate
            .evaluate(
                packet
            )
            .blockers
        )
    )


@pytest.mark.parametrize(
    (
        "description",
        "language",
    ),
    (
        (
            (
                "Le probleme est un processus fragmente. "
                "La plateforme met en relation deux cotes. "
                "Le premier cote est constitue de fournisseurs. "
                "Le second cote est constitue de clients. "
                "Un client envoie une demande. "
                "L'unite de transaction principale est "
                "une reservation de service."
            ),
            "fr",
        ),
        (
            (
                "The current process is fragmented. "
                "The platform connects two sides. "
                "The first side consists of providers. "
                "The second side consists of customers. "
                "A customer sends a request. "
                "The primary transaction unit is "
                "a service booking."
            ),
            "en",
        ),
    ),
)
def test_explicit_unit_without_end_keeps_flow_blocker(
    description,
    language,
):
    packet = extract(
        description,
        language=language,
    )

    transaction = (
        packet.transaction_unit
    )

    assert transaction.is_explicit

    assert (
        transaction.completion_action
        == ""
    )

    assert (
        "transaction_flow"
        in (
            context_confidence_gate
            .evaluate(
                packet
            )
            .blockers
        )
    )


def test_terminal_statement_alone_does_not_manufacture_start():
    packet = extract(
        (
            "The current process is fragmented. "
            "The platform connects two sides. "
            "The first side consists of providers. "
            "The second side consists of customers. "
            "The transaction is closed. "
            "The primary transaction unit is "
            "a service booking."
        ),
        language="en",
    )

    transaction = (
        packet.transaction_unit
    )

    assert (
        transaction.initiation_action
        == ""
    )

    assert (
        transaction.completion_action
    )

    assert (
        "transaction_flow"
        in (
            context_confidence_gate
            .evaluate(
                packet
            )
            .blockers
        )
    )
