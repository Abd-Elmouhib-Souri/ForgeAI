from app.schemas.analysis_context import (
    ActorRole,
    comparison_key,
)
from app.services.project_context_extractor import (
    project_context_extractor,
)


def role_names(items, role):
    return {
        comparison_key(name)
        for name, actual_role in items
        if actual_role == role
    }


def test_negated_payment_relation_never_creates_payer():
    cases = (
        (
            (
                "Le technicien utilise la plateforme chaque jour "
                "et n\u2019est donc pas n\u00e9cessairement la "
                "personne qui d\u00e9cide du budget ou qui paie "
                "l\u2019abonnement."
            ),
            "technicien",
        ),
        (
            (
                "The technician uses the platform every day and "
                "is not necessarily the person who decides the "
                "budget or pays the subscription."
            ),
            "technician",
        ),
        (
            "Le superviseur ne paie pas l\u2019abonnement.",
            "superviseur",
        ),
        (
            "The supervisor does not pay the subscription.",
            "supervisor",
        ),
    )

    for sentence, forbidden in cases:
        declared = (
            project_context_extractor
            ._declared_actor_roles(
                sentence
            )
        )

        assert (
            comparison_key(forbidden)
            not in role_names(
                declared,
                ActorRole.PAYER,
            )
        ), declared


def test_positive_payment_predicate_remains_payer():
    cases = (
        (
            "L\u2019entreprise cliente paie un abonnement mensuel.",
            "entreprise cliente",
        ),
        (
            "The client company pays a monthly subscription.",
            "client company",
        ),
    )

    for sentence, expected in cases:
        declared = (
            project_context_extractor
            ._declared_actor_roles(
                sentence
            )
        )

        assert (
            comparison_key(expected)
            in role_names(
                declared,
                ActorRole.PAYER,
            )
        ), declared


def test_primary_user_list_stops_before_relative_clause():
    cases = (
        (
            (
                "Les utilisateurs principaux sont les techniciens "
                "de maintenance, les responsables maintenance et "
                "les responsables de production qui suivent "
                "l\u2019\u00e9tat des \u00e9quipements et les "
                "interventions."
            ),
            (
                "techniciens de maintenance",
                "responsables maintenance",
                "responsables de production",
            ),
            (
                "interventions",
                "\u00e9quipements",
            ),
        ),
        (
            (
                "The primary users are maintenance technicians, "
                "maintenance managers and production managers who "
                "track equipment status and interventions."
            ),
            (
                "maintenance technicians",
                "maintenance managers",
                "production managers",
            ),
            (
                "equipment",
                "interventions",
            ),
        ),
    )

    for sentence, expected, forbidden in cases:
        declared = (
            project_context_extractor
            ._declared_actor_groups(
                sentence
            )
        )

        actual = {
            comparison_key(name)
            for name, _role in declared
        }

        for value in expected:
            assert (
                comparison_key(value)
                in actual
            ), declared

        for value in forbidden:
            assert (
                comparison_key(value)
                not in actual
            ), declared


def test_target_relative_objects_never_become_actors():
    cases = (
        (
            "fr",
            (
                "La solution est destin\u00e9e aux petites et "
                "moyennes entreprises industrielles en France "
                "qui organisent la maintenance de leurs machines "
                "et \u00e9quipements."
            ),
            "petites et moyennes entreprises industrielles en France",
            (
                "machines",
                "\u00e9quipements",
            ),
        ),
        (
            "en",
            (
                "The solution is intended for small and medium "
                "industrial companies in France that organize "
                "maintenance for their machines and equipment."
            ),
            "small and medium industrial companies in France",
            (
                "machines",
                "equipment",
            ),
        ),
    )

    for language, description, expected, forbidden in cases:
        packet = (
            project_context_extractor
            .extract(
                title="ActorBoundary",
                description=description,
                industry="software",
                target_region="Europe",
                output_language=language,
            )
        )

        actual = {
            comparison_key(actor.name)
            for actor in packet.actors
        }

        assert (
            comparison_key(expected)
            in actual
        ), packet.actors

        for value in forbidden:
            assert (
                comparison_key(value)
                not in actual
            ), packet.actors
