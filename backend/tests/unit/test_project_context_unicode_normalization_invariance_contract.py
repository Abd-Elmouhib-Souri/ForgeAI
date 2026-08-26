from __future__ import annotations

import unicodedata

from app.services.project_context_extractor import (
    ProjectContextExtractor,
)


def extract(description: str):
    return ProjectContextExtractor().extract(
        title="UnicodeInvariantProject",
        description=description,
        industry="",
        target_region="",
        output_language="fr",
    )


def actor_rows(packet):
    result = []

    for actor in packet.actors or []:
        role = actor.role

        if hasattr(role, "value"):
            role = role.value

        result.append(
            (
                actor.name,
                role,
            )
        )

    return result


def semantic_actor_projection(description: str):
    packet = extract(description)

    return actor_rows(packet)


def assert_nfc_nfd_equivalent(description: str):
    nfc = unicodedata.normalize(
        "NFC",
        description,
    )

    nfd = unicodedata.normalize(
        "NFD",
        description,
    )

    assert nfc != nfd

    nfc_projection = (
        semantic_actor_projection(
            nfc
        )
    )

    nfd_projection = (
        semantic_actor_projection(
            nfd
        )
    )

    assert (
        nfd_projection
        == nfc_projection
    ), {
        "nfc": nfc_projection,
        "nfd": nfd_projection,
        "nfc_ascii": ascii(nfc),
        "nfd_ascii": ascii(nfd),
    }


def test_unicode_invariance_label_first_operational_user():
    assert_nfc_nfd_equivalent(
        (
            "L\u2019utilisateur op\u00e9rationnel principal est "
            "le superviseur d\u2019\u00e9quipe. "
            "Le superviseur utilise le syst\u00e8me."
        )
    )


def test_unicode_invariance_actor_first_primary_user():
    assert_nfc_nfd_equivalent(
        (
            "Le coordinateur r\u00e9gional est "
            "l\u2019utilisateur principal."
        )
    )


def test_unicode_invariance_plural_primary_users():
    assert_nfc_nfd_equivalent(
        (
            "Les op\u00e9rateurs logistiques sont "
            "les utilisateurs principaux."
        )
    )
