from app.services.idea_readiness_checker import (
    idea_readiness_checker,
)
from app.services.project_context_extractor import (
    comparison_key,
    project_context_extractor,
)


def _is_problem(
    sentence: str,
) -> bool:
    return (
        project_context_extractor
        ._is_problem_sentence(
            sentence
        )
    )


def _packet(
    *,
    title: str,
    description: str,
    industry: str,
    region: str,
):
    return project_context_extractor.extract(
        title=title,
        description=description,
        industry=industry,
        target_region=region,
        output_language="en",
    )


def _readiness(
    *,
    title: str,
    description: str,
    industry: str,
    region: str,
):
    return idea_readiness_checker.evaluate(
        title=title,
        description=description,
        industry=industry,
        target_region=region,
        output_language="en",
        analysis_data={},
    )


MEALMATE = (
    "MealMate is a mobile meal planning application for busy households. "
    "Many users spend too much time deciding what to cook and frequently "
    "buy food that is later wasted. "
    "The household user creates a weekly meal plan, selects dietary "
    "preferences and generates a grocery list. "
    "The household user can pay for a monthly premium subscription. "
    "The household user makes the purchase decision directly. "
    "The first MVP includes meal planning, dietary preferences, saved meals "
    "and automatic grocery lists."
)


MAINTPRO = (
    "MaintPro Contract provides preventive equipment maintenance services "
    "to small hotels. "
    "Hotels often schedule maintenance inconsistently, which creates "
    "unexpected breakdowns and operational interruptions. "
    "The hotel facility manager requests a maintenance visit. "
    "A MaintPro technician performs the inspection and maintenance work. "
    "The hotel confirms completion of the visit. "
    "The hotel pays MaintPro for the maintenance service. "
    "The hotel general manager is the main decision maker for approving "
    "the annual maintenance contract and authorizing payment."
)


def test_time_cost_and_waste_sentence_is_problem_evidence() -> None:
    sentence = (
        "Many users spend too much time deciding what to cook "
        "and frequently buy food that is later wasted."
    )

    assert _is_problem(
        sentence
    ) is True


def test_inconsistent_process_with_negative_consequence_is_problem_evidence() -> None:
    sentence = (
        "Hotels often schedule maintenance inconsistently, "
        "which creates unexpected breakdowns and operational interruptions."
    )

    assert _is_problem(
        sentence
    ) is True


def test_mealmate_packet_keeps_explicit_user_pain() -> None:
    packet = _packet(
        title="MealMate",
        description=MEALMATE,
        industry="Consumer Mobile App / Meal Planning",
        region="United Kingdom",
    )

    assert packet.problem.pain, (
        packet.problem.model_dump(
            mode="json"
        )
    )

    pain_key = comparison_key(
        packet.problem.pain
    )

    assert (
        "too much time"
        in pain_key
        or "wasted"
        in pain_key
    ), packet.problem.model_dump(
        mode="json"
    )


def test_maintpro_packet_keeps_process_failure_problem() -> None:
    packet = _packet(
        title="MaintPro Contract",
        description=MAINTPRO,
        industry="B2B Professional Services / Maintenance",
        region="Italy",
    )

    assert packet.problem.pain, (
        packet.problem.model_dump(
            mode="json"
        )
    )

    pain_key = comparison_key(
        packet.problem.pain
    )

    assert (
        "inconsistently"
        in pain_key
        or "breakdowns"
        in pain_key
        or "interruptions"
        in pain_key
    ), packet.problem.model_dump(
        mode="json"
    )


def test_mealmate_readiness_has_no_problem_blocker() -> None:
    result = _readiness(
        title="MealMate",
        description=MEALMATE,
        industry="Consumer Mobile App / Meal Planning",
        region="United Kingdom",
    )

    blockers = set(
        result.get("blockers")
        or []
    )

    assert "problem" not in blockers, result


def test_maintpro_readiness_has_no_problem_blocker() -> None:
    result = _readiness(
        title="MaintPro Contract",
        description=MAINTPRO,
        industry="B2B Professional Services / Maintenance",
        region="Italy",
    )

    blockers = set(
        result.get("blockers")
        or []
    )

    assert "problem" not in blockers, result


# ----------------------------------------------------------------------
# Negative controls:
# frequency, ordinary operations and positive capability statements must
# not become pain merely because they contain common verbs or cadence.
# ----------------------------------------------------------------------

def test_normal_recurring_operation_is_not_problem_evidence() -> None:
    sentence = (
        "Hotels schedule preventive maintenance every month."
    )

    assert _is_problem(
        sentence
    ) is False


def test_positive_product_capability_is_not_problem_evidence() -> None:
    sentence = (
        "Users create a weekly meal plan and generate a grocery list."
    )

    assert _is_problem(
        sentence
    ) is False


def test_neutral_user_frequency_is_not_problem_evidence() -> None:
    sentence = (
        "Many users prepare meals at home every week."
    )

    assert _is_problem(
        sentence
    ) is False


def test_neutral_service_frequency_is_not_problem_evidence() -> None:
    sentence = (
        "Hotels often request maintenance visits during the summer."
    )

    assert _is_problem(
        sentence
    ) is False



def test_excessive_manual_effort_is_problem_evidence() -> None:
    sentence = (
        "Teams spend too much time manually reconciling records."
    )

    assert _is_problem(
        sentence
    ) is True


def test_excessive_time_is_problem_evidence() -> None:
    sentence = (
        "Operators spend excessive time checking every record."
    )

    assert _is_problem(
        sentence
    ) is True


def test_inconsistent_process_causing_errors_is_problem_evidence() -> None:
    sentence = (
        "The process runs inconsistently, which creates repeated errors."
    )

    assert _is_problem(
        sentence
    ) is True


def test_unexpected_breakdowns_are_harm_when_consequence_is_explicit() -> None:
    sentence = (
        "The current workflow is inconsistent and causes "
        "unexpected breakdowns."
    )

    assert _is_problem(
        sentence
    ) is True


def test_normal_time_statement_is_not_problem_evidence() -> None:
    sentence = (
        "Operators spend ten minutes reviewing the report."
    )

    assert _is_problem(
        sentence
    ) is False


def test_consistent_process_is_not_problem_evidence() -> None:
    sentence = (
        "The process runs consistently and creates a daily report."
    )

    assert _is_problem(
        sentence
    ) is False
