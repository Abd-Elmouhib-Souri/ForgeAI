from app.services.project_intelligence_layer import (
    ProjectIntelligenceLayer,
    project_intelligence_layer,
)


def test_short_hint_does_not_match_inside_product_name():
    result = (
        project_intelligence_layer
        ._extract_sentence(
            (
                "ToolShare Pro connects businesses. "
                "No explicit product form is declared."
            ),
            {
                "tool",
            },
        )
    )

    assert result == ""


def test_short_hint_matches_real_standalone_word():
    result = (
        project_intelligence_layer
        ._extract_sentence(
            (
                "This tool helps operational teams "
                "coordinate recurring work."
            ),
            {
                "tool",
            },
        )
    )

    assert (
        result
        == (
            "This tool helps operational teams "
            "coordinate recurring work."
        )
    )


def test_solution_selection_does_not_promote_product_name_substring():
    result = (
        project_intelligence_layer
        ._extract_sentence(
            (
                "ToolShare Pro is a B2B marketplace. "
                "The platform connects two distinct business sides. "
                "ToolShare Pro charges a commission on each "
                "transaction completed via the platform."
            ),
            ProjectIntelligenceLayer
            .SOLUTION_HINTS(),
        )
    )

    assert (
        result
        == (
            "The platform connects two distinct "
            "business sides."
        )
    )


def test_solution_selection_is_equivalent_in_french():
    result = (
        project_intelligence_layer
        ._extract_sentence(
            (
                "ToolShare Pro est une marketplace B2B. "
                "La plateforme met en relation deux "
                "c\u00f4t\u00e9s professionnels distincts. "
                "ToolShare Pro pr\u00e9l\u00e8ve une commission "
                "sur chaque transaction via la plateforme."
            ),
            ProjectIntelligenceLayer
            .SOLUTION_HINTS(),
        )
    )

    assert (
        result
        == (
            "La plateforme met en relation deux "
            "c\u00f4t\u00e9s professionnels distincts."
        )
    )
