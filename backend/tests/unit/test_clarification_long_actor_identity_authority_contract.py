
from __future__ import annotations

import pytest

from app.schemas.analysis_context import (
    ProjectContextPacketV3,
)
from app.services.clarification_answer_projector import (
    clarification_answer_projector,
)


def empty_packet(
    language: str,
) -> ProjectContextPacketV3:
    return ProjectContextPacketV3(
        project_name=(
            "Universal clarification identity probe"
        ),
        description=(
            "Original project description."
        ),
        language=language,
    )


@pytest.mark.parametrize(
    (
        "language",
        "field",
        "answer",
    ),
    [
        (
            "fr",
            "supply_side",
            (
                "Les prestataires sont des techniciens et soci?t?s "
                "de maintenance industrielle qualifi?s qui re?oivent "
                "les demandes des entreprises, analysent le besoin "
                "technique, proposent une intervention avec disponibilit? "
                "et conditions, puis r?alisent la prestation sur site. "
                "Ils restent responsables de l'ex?cution technique de "
                "l'intervention et peuvent joindre les informations "
                "n?cessaires avant acceptation."
            ),
        ),
        (
            "en",
            "demand_side",
            (
                "The client side consists of industrial companies whose "
                "maintenance managers submit technical service requests, "
                "compare provider proposals, validate the selected service "
                "and confirm completion after the intervention. These "
                "companies remain responsible for the purchasing decision "
                "and for accepting the completed work before payment."
            ),
        ),
        (
            "fr",
            "decision_maker",
            (
                "Le d?cideur principal est le directeur des op?rations "
                "industrielles qui ?value le besoin avec le responsable "
                "maintenance, v?rifie le budget disponible, compare les "
                "options propos?es et donne l'autorisation finale avant "
                "engagement contractuel avec le prestataire s?lectionn?."
            ),
        ),
    ],
)
def test_long_actor_clarification_preserves_fact_without_using_full_answer_as_identity(
    language: str,
    field: str,
    answer: str,
) -> None:
    assert len(answer) > 180

    packet = clarification_answer_projector.apply(
        empty_packet(
            language
        ),
        {
            field:
                answer,
        },
    )

    assert (
        packet.clarification_facts[
            field
        ]
        == answer
    )

    actor_names = [
        actor.name
        for actor
        in packet.actors
    ]

    assert answer not in actor_names

    assert all(
        len(name) <= 180
        for name
        in actor_names
    ), actor_names


def test_long_actor_answer_never_rewrites_original_description() -> None:
    packet = empty_packet(
        "fr"
    )

    original = packet.description

    answer = (
        "Les prestataires sont des entreprises techniques qualifi?es "
        "qui re?oivent les demandes, analysent le besoin, proposent "
        "une intervention et assurent ensuite la r?alisation, le suivi "
        "op?rationnel et la communication n?cessaire avec le client "
        "jusqu'? la cl?ture compl?te de la prestation."
    )

    assert len(answer) > 180

    projected = clarification_answer_projector.apply(
        packet,
        {
            "supply_side":
                answer,
        },
    )

    assert projected.description == original

    assert (
        projected.clarification_facts[
            "supply_side"
        ]
        == answer
    )
