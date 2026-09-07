from __future__ import annotations

from app.schemas.analysis_context import comparison_key
from app.services.project_context_extractor import ProjectContextExtractor


def extract(description: str):
    return ProjectContextExtractor().extract(
        title="Capability Polarity Contract",
        description=description,
        industry="General operations software",
        target_region="International",
        output_language="fr",
        project_context={},
        idea_readiness={},
        analysis_data={},
    )


def capability_keys(packet) -> set[str]:
    return {
        comparison_key(value)
        for value
        in packet.solution.required_capabilities
        if comparison_key(value)
    }


def delivery_modes(packet) -> set[str]:
    return {
        value.strip()
        for value
        in (
            packet.solution.delivery_mode
            or ""
        ).split("+")
        if value.strip()
    }


def test_excluded_capabilities_cannot_become_positive_solution_requirements(
) -> None:
    """
    Universal polarity invariant.

    Capability vocabulary appearing only in explicit negative MVP scope
    must never become a positive required capability or delivery mode.

    The positive MVP remains ordinary web software.
    """

    packet = extract(
        (
            "Le produit est une application web destinée à une équipe "
            "opérationnelle pour traiter et suivre des demandes. "
            "Le MVP doit inclure : authentification ; tableau de bord ; "
            "notifications. "
            "Les exclusions du MVP sont : gestion automatisée par "
            "capteurs IoT ; prédiction par intelligence artificielle."
        )
    )

    capabilities = capability_keys(
        packet
    )

    modes = delivery_modes(
        packet
    )

    assert comparison_key(
        "tableau de bord"
    ) in capabilities, packet.solution.required_capabilities

    assert comparison_key(
        "notifications"
    ) in capabilities, packet.solution.required_capabilities

    assert comparison_key(
        "capteurs"
    ) not in capabilities, packet.solution.required_capabilities

    assert comparison_key(
        "intelligence artificielle"
    ) not in capabilities, packet.solution.required_capabilities

    assert (
        "hardware_iot"
        not in modes
    ), packet.solution.delivery_mode


def test_positive_capabilities_remain_detectable_when_explicitly_required(
) -> None:
    """
    Anti-overfitting control.

    The correction must suppress negative evidence, not globally suppress
    valid IoT / AI capability vocabulary.
    """

    packet = extract(
        (
            "Le produit est une application web destinée à une équipe "
            "opérationnelle. "
            "Le MVP doit inclure : authentification ; tableau de bord ; "
            "notifications ; collecte par capteurs IoT ; "
            "analyse par intelligence artificielle."
        )
    )

    capabilities = capability_keys(
        packet
    )

    modes = delivery_modes(
        packet
    )

    assert comparison_key(
        "capteurs"
    ) in capabilities, packet.solution.required_capabilities

    assert comparison_key(
        "intelligence artificielle"
    ) in capabilities, packet.solution.required_capabilities

    assert (
        "hardware_iot"
        in modes
    ), packet.solution.delivery_mode


def _solution_projection(packet) -> tuple[set[str], set[str]]:
    return (
        capability_keys(packet),
        delivery_modes(packet),
    )


def test_negative_scope_addition_preserves_positive_solution_projection(
) -> None:
    """
    Metamorphic invariant.

    Adding technologies only inside an explicit negative scope section
    must not change the positive solution projection.

    The invariant is verified independently in French and English.
    """

    cases = (
        (
            "fr",
            (
                "Le produit est une application web destinée à une équipe "
                "opérationnelle. "
                "Le MVP doit inclure : authentification ; tableau de bord ; "
                "notifications."
            ),
            (
                "Le produit est une application web destinée à une équipe "
                "opérationnelle. "
                "Le MVP doit inclure : authentification ; tableau de bord ; "
                "notifications. "
                "Les exclusions du MVP sont : collecte par capteurs IoT ; "
                "analyse par intelligence artificielle."
            ),
        ),
        (
            "en",
            (
                "The product is a web application for an operations team. "
                "The MVP must include: authentication; dashboard; "
                "notifications."
            ),
            (
                "The product is a web application for an operations team. "
                "The MVP must include: authentication; dashboard; "
                "notifications. "
                "MVP exclusions: collection through IoT sensors; "
                "analysis using artificial intelligence."
            ),
        ),
    )

    for language, baseline, transformed in cases:
        baseline_packet = ProjectContextExtractor().extract(
            title="Metamorphic Capability Contract",
            description=baseline,
            industry="General operations software",
            target_region="International",
            output_language=language,
            project_context={},
            idea_readiness={},
            analysis_data={},
        )

        transformed_packet = ProjectContextExtractor().extract(
            title="Metamorphic Capability Contract",
            description=transformed,
            industry="General operations software",
            target_region="International",
            output_language=language,
            project_context={},
            idea_readiness={},
            analysis_data={},
        )

        assert (
            _solution_projection(
                transformed_packet
            )
            ==
            _solution_projection(
                baseline_packet
            )
        ), (
            language,
            baseline_packet.solution,
            transformed_packet.solution,
        )

        transformed_capabilities = capability_keys(
            transformed_packet
        )

        transformed_modes = delivery_modes(
            transformed_packet
        )

        assert comparison_key(
            "capteurs"
        ) not in transformed_capabilities, (
            language,
            transformed_packet.solution.required_capabilities,
        )

        assert comparison_key(
            "intelligence artificielle"
        ) not in transformed_capabilities, (
            language,
            transformed_packet.solution.required_capabilities,
        )

        assert "hardware_iot" not in transformed_modes, (
            language,
            transformed_packet.solution.delivery_mode,
        )


def test_positive_scope_promotion_changes_solution_projection_cross_language(
) -> None:
    """
    Anti-overfitting metamorphic control.

    The same technology concepts must become positive solution evidence
    when explicitly promoted into the MVP rather than excluded.
    """

    cases = (
        (
            "fr",
            (
                "Le produit est une application web destinée à une équipe "
                "opérationnelle. "
                "Le MVP doit inclure : authentification ; tableau de bord ; "
                "notifications ; collecte par capteurs IoT ; "
                "analyse par intelligence artificielle."
            ),
        ),
        (
            "en",
            (
                "The product is a web application for an operations team. "
                "The MVP must include: authentication; dashboard; "
                "notifications; collection through IoT sensors; "
                "analysis using artificial intelligence."
            ),
        ),
    )

    for language, description in cases:
        packet = ProjectContextExtractor().extract(
            title="Positive Capability Contract",
            description=description,
            industry="General operations software",
            target_region="International",
            output_language=language,
            project_context={},
            idea_readiness={},
            analysis_data={},
        )

        capabilities = capability_keys(
            packet
        )

        modes = delivery_modes(
            packet
        )

        assert comparison_key(
            "capteurs"
        ) in capabilities, (
            language,
            packet.solution.required_capabilities,
        )

        assert comparison_key(
            "intelligence artificielle"
        ) in capabilities, (
            language,
            packet.solution.required_capabilities,
        )

        assert "hardware_iot" in modes, (
            language,
            packet.solution.delivery_mode,
        )
