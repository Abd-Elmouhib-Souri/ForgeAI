from copy import deepcopy

import pytest

from app.services.evidence_ledger import (
    evidence_ledger,
)


@pytest.mark.parametrize(
    (
        "language",
        "raw_overview",
        "expected_overview",
        "raw_local_context",
        "expected_local_context",
    ),
    [
        (
            "fr",
            "Le marche test doit etre verifie sur le terrain.",
            (
                "Hypoth\u00e8se \u00e0 valider : "
                "Le marche test doit etre verifie sur le terrain."
            ),
            "Commencer par un pilote test limite.",
            (
                "Recommandation : "
                "Commencer par un pilote test limite."
            ),
        ),
        (
            "en",
            "The test market must be validated in the field.",
            (
                "Hypothesis to validate: "
                "The test market must be validated in the field."
            ),
            "Start with a limited test pilot.",
            (
                "Recommendation: "
                "Start with a limited test pilot."
            ),
        ),
    ],
)
def test_public_evidence_sanitization_is_idempotent(
    language: str,
    raw_overview: str,
    expected_overview: str,
    raw_local_context: str,
    expected_local_context: str,
) -> None:
    analysis = {
        "output_language": language,
        "market_study": {
            "market_overview": raw_overview,
            "local_context": raw_local_context,
        },
    }

    first = evidence_ledger.sanitize_public_claims(
        deepcopy(analysis)
    )

    second = evidence_ledger.sanitize_public_claims(
        deepcopy(first)
    )

    third = evidence_ledger.sanitize_public_claims(
        deepcopy(second)
    )

    first_market = first["market_study"]
    second_market = second["market_study"]
    third_market = third["market_study"]

    assert (
        first_market["market_overview"]
        == expected_overview
    )

    assert (
        first_market["local_context"]
        == expected_local_context
    )

    assert (
        second_market["market_overview"]
        == expected_overview
    )

    assert (
        second_market["local_context"]
        == expected_local_context
    )

    assert (
        third_market["market_overview"]
        == expected_overview
    )

    assert (
        third_market["local_context"]
        == expected_local_context
    )


@pytest.mark.parametrize(
    (
        "language",
        "market_overview",
        "local_context",
    ),
    [
        (
            "fr",
            (
                "Hypoth\u00e8se \u00e0 valider : "
                "Le marche est deja qualifie."
            ),
            (
                "Recommandation : "
                "Executer un pilote."
            ),
        ),
        (
            "en",
            (
                "Hypothesis to validate: "
                "The market is already qualified."
            ),
            (
                "Recommendation: "
                "Run a pilot."
            ),
        ),
    ],
)
def test_public_evidence_sanitization_does_not_duplicate_existing_prefix(
    language: str,
    market_overview: str,
    local_context: str,
) -> None:
    analysis = {
        "output_language": language,
        "market_study": {
            "market_overview": market_overview,
            "local_context": local_context,
        },
    }

    sanitized = (
        evidence_ledger
        .sanitize_public_claims(
            deepcopy(analysis)
        )
    )

    assert (
        sanitized["market_study"][
            "market_overview"
        ]
        == market_overview
    )

    assert (
        sanitized["market_study"][
            "local_context"
        ]
        == local_context
    )


@pytest.mark.parametrize(
    (
        "language",
        "market_overview",
        "expected_overview",
        "local_context",
        "expected_local_context",
    ),
    [
        (
            "fr",
            (
                "Hypoth\u00e8se \u00e0 valider : "
                "Hypoth\u00e8se \u00e0 valider : "
                "Hypoth\u00e8se \u00e0 valider : "
                "Le marche historique doit etre valide."
            ),
            (
                "Hypoth\u00e8se \u00e0 valider : "
                "Le marche historique doit etre valide."
            ),
            (
                "Recommandation : "
                "Recommandation : "
                "Recommandation : "
                "Executer un pilote historique."
            ),
            (
                "Recommandation : "
                "Executer un pilote historique."
            ),
        ),
        (
            "en",
            (
                "Hypothesis to validate: "
                "Hypothesis to validate: "
                "Hypothesis to validate: "
                "The historical market must be validated."
            ),
            (
                "Hypothesis to validate: "
                "The historical market must be validated."
            ),
            (
                "Recommendation: "
                "Recommendation: "
                "Recommendation: "
                "Run a historical pilot."
            ),
            (
                "Recommendation: "
                "Run a historical pilot."
            ),
        ),
    ],
)
def test_public_evidence_sanitization_collapses_repeated_canonical_prefixes(
    language: str,
    market_overview: str,
    expected_overview: str,
    local_context: str,
    expected_local_context: str,
) -> None:
    analysis = {
        "output_language": language,
        "market_study": {
            "market_overview": market_overview,
            "local_context": local_context,
        },
    }

    sanitized = (
        evidence_ledger
        .sanitize_public_claims(
            deepcopy(analysis)
        )
    )

    assert (
        sanitized["market_study"][
            "market_overview"
        ]
        == expected_overview
    )

    assert (
        sanitized["market_study"][
            "local_context"
        ]
        == expected_local_context
    )


@pytest.mark.parametrize(
    (
        "language",
        "raw_overview",
        "public_overview",
        "raw_local_context",
        "public_local_context",
    ),
    [
        (
            "fr",
            "Le marche canonique doit etre valide.",
            (
                "Hypoth\u00e8se \u00e0 valider : "
                "Le marche canonique doit etre valide."
            ),
            "Executer un pilote canonique.",
            (
                "Recommandation : "
                "Executer un pilote canonique."
            ),
        ),
        (
            "en",
            "The canonical market must be validated.",
            (
                "Hypothesis to validate: "
                "The canonical market must be validated."
            ),
            "Run a canonical pilot.",
            (
                "Recommendation: "
                "Run a canonical pilot."
            ),
        ),
    ],
)
def test_public_sanitization_keeps_canonical_claim_text_stable(
    language: str,
    raw_overview: str,
    public_overview: str,
    raw_local_context: str,
    public_local_context: str,
) -> None:
    analysis = {
        "output_language": language,
        "market_study": {
            "market_overview": raw_overview,
            "local_context": raw_local_context,
        },
    }

    first = evidence_ledger.sanitize_public_claims(
        deepcopy(analysis)
    )

    second = evidence_ledger.sanitize_public_claims(
        deepcopy(first)
    )

    third = evidence_ledger.sanitize_public_claims(
        deepcopy(second)
    )

    def claim_map(packet):
        return {
            item["claim_id"]: item
            for item in (
                packet.get("evidence_ledger", {})
                .get("claims", [])
            )
            if isinstance(item, dict)
            and item.get("claim_id")
        }

    first_claims = claim_map(first)
    second_claims = claim_map(second)
    third_claims = claim_map(third)

    for result in (
        first,
        second,
        third,
    ):
        assert (
            result["market_study"][
                "market_overview"
            ]
            == public_overview
        )

        assert (
            result["market_study"][
                "local_context"
            ]
            == public_local_context
        )

    for claims in (
        first_claims,
        second_claims,
        third_claims,
    ):
        assert (
            claims["market_overview"][
                "claim"
            ]
            == raw_overview
        )

        assert (
            claims["market_overview"][
                "public_text"
            ]
            == raw_overview
        )

        assert (
            claims["local_context"][
                "claim"
            ]
            == raw_local_context
        )

        assert (
            claims["local_context"][
                "public_text"
            ]
            == raw_local_context
        )
