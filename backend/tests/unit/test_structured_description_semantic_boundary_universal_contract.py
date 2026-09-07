from __future__ import annotations

import app.services.idea_readiness_checker as readiness_module
import app.services.project_context_extractor as extractor_module

from app.schemas.analysis_context import (
    clean_text,
)

from app.services.idea_readiness_checker import (
    IdeaReadinessChecker,
)

from app.services.project_context_extractor import (
    ProjectContextExtractor,
)

from app.services.project_intelligence_layer import (
    ProjectIntelligenceLayer,
)


DESCRIPTION = (
    "A generic software product coordinates a workflow.\n"
    "Primary operational users:\n"
    "- operations coordinator\n"
    "- inventory manager\n"
    "Paying customer:\n"
    "- operating organization\n"
    "Decision makers:\n"
    "- organization owner\n"
    "- operations manager\n"
    "MVP capabilities:\n"
    "- function alpha"
)


def test_atomic_clean_text_contract_remains_flat() -> None:
    """
    clean_text is the canonical atomic-text normalizer.

    This contract deliberately remains flat. The product correction must
    therefore introduce/use a structure-preserving semantic representation
    rather than silently changing clean_text globally.
    """

    assert clean_text(
        "alpha\nbeta"
    ) == (
        "alpha beta"
    )


def test_direct_payer_authority_is_green_on_structured_input() -> None:
    """
    Downstream payer authority is already GREEN when structural evidence
    reaches it intact.
    """

    pil = (
        extractor_module
        .project_intelligence_layer
    )

    assert (
        pil
        ._extract_economic_buyer_from_description(
            DESCRIPTION
        )
        ==
        "operating organization"
    )


def test_project_intelligence_build_preserves_structured_description_semantics() -> None:
    """
    Public PIL build must not erase semantic section structure before its
    deterministic extractors consume the description.
    """

    result = (
        ProjectIntelligenceLayer()
        .build(
            title="Neutral Structure Probe",
            description=DESCRIPTION,
            industry="software",
            target_region="Global",
            output_language="en",
            project_context={},
            idea_readiness={},
            analysis_data={},
        )
    )

    structured = (
        result.get(
            "structured_project_context"
        )
        or {}
    )

    assert (
        structured.get(
            "economic_buyer"
        )
        ==
        "operating organization"
    )


def test_project_context_extractor_hands_structured_description_to_pil(
    monkeypatch,
) -> None:
    """
    ProjectContextExtractor may keep a flat canonical packet description,
    but semantic consumers must receive the structure-preserving form.
    """

    pil = (
        extractor_module
        .project_intelligence_layer
    )

    original_build = pil.build

    seen = []


    def traced_build(
        *args,
        **kwargs,
    ):

        description = (
            kwargs.get(
                "description"
            )
        )

        seen.append(
            description
        )

        return original_build(
            *args,
            **kwargs,
        )


    monkeypatch.setattr(
        pil,
        "build",
        traced_build,
    )


    packet = (
        ProjectContextExtractor()
        .extract(
            title="Neutral Extractor Structure Probe",
            description=DESCRIPTION,
            industry="software",
            target_region="Global",
            output_language="en",
            project_context={},
            idea_readiness={},
            analysis_data={},
        )
    )


    assert seen

    assert "\n" in seen[0]

    # Public/canonical packet compatibility remains flat.
    assert "\n" not in packet.description

    assert (
        packet.description
        ==
        clean_text(
            DESCRIPTION
        )
    )


def test_idea_readiness_hands_structured_description_to_context_extractor(
    monkeypatch,
) -> None:
    """
    Readiness is an upstream canonical entry point. It must not destroy
    semantic structure before ProjectContextExtractor sees the description.
    """

    extractor = (
        readiness_module
        .project_context_extractor
    )

    original_extract = (
        extractor.extract
    )

    seen = []


    def traced_extract(
        *args,
        **kwargs,
    ):

        seen.append(
            kwargs.get(
                "description"
            )
        )

        return original_extract(
            *args,
            **kwargs,
        )


    monkeypatch.setattr(
        extractor,
        "extract",
        traced_extract,
    )


    IdeaReadinessChecker().evaluate(
        title="Neutral Readiness Structure Probe",
        description=DESCRIPTION,
        industry="software",
        target_region="Global",
        output_language="en",
        project_context={},
        analysis_data={},
    )


    assert seen

    assert "\n" in seen[0]