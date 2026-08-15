import inspect


from app.agents.debate_room_graph import (
    DebateRoomGraph,
)


def test_debate_run_uses_one_universal_adaptive_route() -> None:
    source = inspect.getsource(
        DebateRoomGraph.run
    )

    assert "b2b_workflow_saas" not in source

    required = (
        "_round_adaptive_problem",
        "_round_adaptive_market",
        "_round_adaptive_product",
        "_round_adaptive_economics",
        "_round_adaptive_decision",
    )

    for name in required:
        assert name in source


def test_debate_legacy_round_builders_are_removed() -> None:
    legacy = (
        "_round_problem",
        "_round_market",
        "_round_mvp",
        "_round_finance",
        "_round_decision",
    )

    for name in legacy:
        assert not hasattr(
            DebateRoomGraph,
            name,
        )


def test_universal_routing_does_not_forbid_canonical_archetype_consumption() -> None:
    source = inspect.getsource(
        DebateRoomGraph.run
    )

    # Routing is universal. Archetype information may still be consumed
    # elsewhere for canonical actors, workflows, risks or metrics.
    assert (
        'context.get("project_archetype")'
        not in source
    )
