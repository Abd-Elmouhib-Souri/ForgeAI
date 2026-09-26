from __future__ import annotations

from app.services.domain_integrity_guard import normalize_output_language
from typing import Any, Mapping


def _first_present(data: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    """
    Plusieurs sections historiques (Sprint 2/3) stockent le meme concept
    sous deux noms differents (ex. "value_proposition" et
    "value_propositions", "key_partners" et "key_partnerships"), avec un
    contenu identique. Renvoie la premiere valeur non vide trouvee parmi
    les noms candidats, jamais les deux — la couche d'export ne doit
    jamais dupliquer un contenu deja duplique en amont.
    """
    for key in keys:
        value = data.get(key)
        if value not in (None, "", [], {}):
            return value
    return default


def _section(analysis_data: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = analysis_data.get(key)
    return value if isinstance(value, dict) else {}


def _assemble_cover(
    analysis_data: Mapping[str, Any],
    final_report: Mapping[str, Any],
    project_name: str,
) -> dict[str, Any]:
    context = _section(final_report, "context")
    return {
        "title": project_name or context.get("project_name") or "Projet ForgeAI",
        "sector": context.get("industry_user_input")
        or analysis_data.get("detected_sector")
        or "",
        "region": context.get("target_region")
        or analysis_data.get("target_region")
        or "",
    }


def _assemble_executive_summary(
    final_report: Mapping[str, Any],
) -> dict[str, Any]:
    decision = _section(final_report, "decision")
    summary = _section(final_report, "executive_summary")
    return {
        "verdict_code": decision.get("verdict_code") or summary.get("verdict_code") or "",
        "verdict": decision.get("verdict") or "",
        "final_recommendation": decision.get("final_recommendation")
        or summary.get("final_recommendation")
        or "",
        "risk_level": decision.get("risk_level") or "",
        "debate_synthesis": decision.get("debate_synthesis") or "",
        "next_actions": decision.get("next_actions") or [],
        "critical_risks": decision.get("critical_risks") or [],
        "go_conditions": decision.get("go_conditions") or [],
        "no_go_conditions": decision.get("no_go_conditions") or [],
    }


def _assemble_description(
    analysis_data: Mapping[str, Any],
    startup_score: Mapping[str, Any],
) -> dict[str, Any]:
    breakdown = _first_present(
        startup_score,
        "breakdown",
        "score_breakdown",
        "criteria_scores",
        default={},
    )
    return {
        "problem": analysis_data.get("problem") or "",
        "solution": analysis_data.get("solution") or "",
        "innovation_score": analysis_data.get("innovation_score"),
        "innovation_breakdown_score": (
            breakdown.get("innovation") if isinstance(breakdown, dict) else None
        ),
    }


def _assemble_market_study(analysis_data: Mapping[str, Any]) -> dict[str, Any]:
    market = _section(analysis_data, "market_study")
    return {
        "summary": market.get("summary") or "",
        "market_overview": market.get("market_overview") or "",
        "target_market": market.get("target_market") or "",
        "market_size": market.get("market_size") or "",
        "customer_segments": _first_present(
            market, "customer_segments", "target_customers", default=[]
        ),
        "market_trends": _first_present(market, "market_trends", "trends", default=[]),
        "demand_drivers": market.get("demand_drivers") or [],
        "adoption_barriers": _first_present(
            market, "adoption_barriers", "barriers", "challenges", default=[]
        ),
        "market_opportunities": _first_present(
            market, "market_opportunities", "opportunities", default=[]
        ),
        "go_to_market_channels": market.get("go_to_market_channels") or [],
        "key_assumptions": market.get("key_assumptions") or [],
        "market_risks": market.get("market_risks") or [],
        "recommendations": market.get("recommendations") or [],
        "confidence_level": market.get("confidence_level") or "",
    }


def _assemble_swot(analysis_data: Mapping[str, Any]) -> dict[str, Any]:
    swot = _section(analysis_data, "swot")
    matrix = _section(swot, "swot_matrix")
    return {
        "summary": swot.get("summary") or "",
        "strengths": matrix.get("strengths") or swot.get("strengths") or [],
        "weaknesses": matrix.get("weaknesses") or swot.get("weaknesses") or [],
        "opportunities": matrix.get("opportunities") or swot.get("opportunities") or [],
        "threats": matrix.get("threats") or swot.get("threats") or [],
        "strategic_recommendations": swot.get("strategic_recommendations") or [],
        "strategic_position": swot.get("strategic_position") or "",
    }


def _assemble_business_model_canvas(
    analysis_data: Mapping[str, Any],
) -> dict[str, Any]:
    bmc = _section(analysis_data, "business_model_canvas")
    return {
        "value_proposition": _first_present(
            bmc, "value_proposition", "value_propositions", default=[]
        ),
        "customer_segments": bmc.get("customer_segments") or [],
        "channels": bmc.get("channels") or [],
        "customer_relationships": bmc.get("customer_relationships") or [],
        "revenue_streams": bmc.get("revenue_streams") or [],
        "key_resources": bmc.get("key_resources") or [],
        "key_activities": bmc.get("key_activities") or [],
        "key_partnerships": _first_present(
            bmc, "key_partnerships", "key_partners", default=[]
        ),
        "cost_structure": bmc.get("cost_structure") or [],
    }


def _assemble_competitive_analysis(
    analysis_data: Mapping[str, Any],
) -> dict[str, Any]:
    comp = _section(analysis_data, "competitive_analysis")

    def _competitor_names(items: Any) -> list[str]:
        if not isinstance(items, list):
            return []
        names = []
        for item in items:
            if isinstance(item, dict):
                name = item.get("name") or item.get("title") or ""
                if name:
                    names.append(name)
        return names

    return {
        "local_competitors": _competitor_names(comp.get("local_competitors")),
        "local_adjacent_solutions": _competitor_names(
            comp.get("local_adjacent_solutions")
        ),
        "international_benchmarks": _competitor_names(
            comp.get("international_benchmarks")
        ),
        "competitive_advantages": comp.get("competitive_advantages") or [],
        "market_gap": comp.get("market_gap") or "",
        "limitations": comp.get("limitations") or [],
    }


def _assemble_startup_score(startup_score: Mapping[str, Any]) -> dict[str, Any]:
    score = _first_present(
        startup_score,
        "score_out_of_10",
        "score",
        "startup_score",
        "overall_score",
        "final_score",
        default=None,
    )
    breakdown = _first_present(
        startup_score,
        "breakdown",
        "score_breakdown",
        "criteria_scores",
        default={},
    )
    return {
        "score_out_of_10": score,
        "verdict": startup_score.get("verdict") or "",
        "risk_level": startup_score.get("risk_level") or "",
        "score_explanation": startup_score.get("score_explanation") or "",
        "breakdown": breakdown if isinstance(breakdown, dict) else {},
        "strengths": startup_score.get("strengths") or [],
        "weaknesses": startup_score.get("weaknesses") or [],
        "recommendations": startup_score.get("recommendations") or [],
        "next_actions": startup_score.get("next_actions") or [],
    }


def _normalize_isolated_name(value: str, *, fallback: str) -> str:
    """
    Un champ cense contenir un nom court (ex. le nom d'un persona) peut,
    par un bug amont connu de persona_builder (Sprint 3), contenir un
    seul mot fonctionnel tronque (ex. "et", la conjonction française,
    plutot qu'un vrai nom). Une valeur isolee d'un seul mot tres court
    et purement fonctionnel n'est jamais un nom valide : on l'affiche
    honnetement comme non identifie plutot que d'imprimer le fragment
    brut dans un document professionnel.

    N'agit que sur un champ isole cense contenir un identifiant court ;
    jamais sur une phrase composee (une story, une phrase de SWOT), ou
    "et" peut etre la vraie conjonction francaise legitime au milieu
    d'un texte par ailleurs correct.
    """
    text = str(value or "").strip()
    is_bare_fragment = bool(text) and len(text) <= 3 and " " not in text
    return fallback if is_bare_fragment else text


def _assemble_personas(analysis_data: Mapping[str, Any]) -> list[dict[str, Any]]:
    builder = _section(analysis_data, "persona_builder")
    raw_personas = builder.get("personas")
    if not isinstance(raw_personas, list):
        return []

    personas: list[dict[str, Any]] = []
    for raw in raw_personas:
        if not isinstance(raw, dict):
            continue
        personas.append(
            {
                "name": _normalize_isolated_name(
                    raw.get("persona_name") or raw.get("name") or "",
                    fallback="Acteur non identifié",
                ),
                "role": raw.get("role") or "",
                "profile": raw.get("profile") or "",
                "main_pain": raw.get("main_pain") or "",
                "goals": raw.get("goals") or [],
                "frustrations": raw.get("frustrations") or [],
                "expected_value": raw.get("expected_value") or "",
                "adoption_trigger": raw.get("adoption_trigger") or "",
                "buying_power": raw.get("buying_power") or "",
                "decision_power": raw.get("decision_power") or "",
            }
        )
    return personas


def _assemble_backlog(analysis_data: Mapping[str, Any]) -> dict[str, Any]:
    pm = _section(analysis_data, "project_manager")
    current = _section(pm, "current")

    stories = []
    for raw in current.get("stories") or []:
        if not isinstance(raw, dict):
            continue
        stories.append(
            {
                "story_id": raw.get("story_id") or "",
                "epic_id": raw.get("epic_id") or "",
                "story": raw.get("story") or raw.get("title") or "",
                "priority": raw.get("priority") or "",
                "story_points": raw.get("story_points"),
                "acceptance_criteria": raw.get("acceptance_criteria") or [],
            }
        )

    epics = []
    for raw in current.get("epics") or []:
        if not isinstance(raw, dict):
            continue
        epics.append(
            {
                "epic_id": raw.get("epic_id") or "",
                "title": raw.get("title") or "",
                "description": raw.get("description") or "",
            }
        )

    return {"epics": epics, "stories": stories}


def _assemble_sprint_planning(analysis_data: Mapping[str, Any]) -> dict[str, Any]:
    pm = _section(analysis_data, "project_manager")
    current = _section(pm, "current")
    settings = _section(current, "settings")
    metrics = _section(current, "metrics")

    sprints = []
    story_lookup = {
        story.get("story_id"): story
        for story in (current.get("stories") or [])
        if isinstance(story, dict)
    }
    for raw in current.get("sprints") or []:
        if not isinstance(raw, dict):
            continue
        story_ids = raw.get("story_ids") or []
        sprints.append(
            {
                "sprint_number": raw.get("sprint_number"),
                "planned_story_points": raw.get("planned_story_points"),
                "stories": [
                    story_lookup[sid].get("story") or story_lookup[sid].get("title") or sid
                    for sid in story_ids
                    if sid in story_lookup
                ],
            }
        )

    return {
        "sprint_count": settings.get("sprint_count"),
        "sprint_duration_days": settings.get("sprint_duration_days"),
        "planned_velocity": settings.get("planned_velocity"),
        "team_size": settings.get("team_size"),
        "sprints": sprints,
        "total_story_points": metrics.get("total_story_points"),
        "assigned_story_points": metrics.get("assigned_story_points"),
        "scrum_master_advice": [
            item.get("rationale", "")
            for item in (current.get("scrum_master_advice") or [])
            if isinstance(item, dict)
        ],
        "ideal_burndown": metrics.get("ideal_burndown") or [],
        "planned_burndown": metrics.get("planned_burndown") or [],
    }


def _string_list(value: Any) -> list[str]:
    """Clean list of non-empty strings (tolerates None / scalars)."""
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item or "").strip()]


def _assemble_solution_architecture(
    analysis_data: Mapping[str, Any],
) -> dict[str, Any] | None:
    """
    Every element of the "Architecture technique" page, for the exports.

    Persisted shape (solution_architecture_plan_service.serialize):
        analysis_data["solution_architecture"] = {
            "envelope_version": 1,
            "canonical": CanonicalSolutionArchitectureV1 (model_dump),
            "generated_at": ...,
        }

    Observed RED (project 31, 27 Sept 2026): the export read the fields at
    the envelope ROOT, found nothing, and printed an empty "Architecture
    technique" page with no diagrams. The canonical payload is read here;
    a legacy root-level payload is still accepted.
    """
    envelope = analysis_data.get("solution_architecture")
    if not isinstance(envelope, dict):
        return None
    canonical = envelope.get("canonical")
    if not isinstance(canonical, dict):
        # Legacy / hand-seeded payloads stored the fields at the root.
        canonical = envelope
    if not any(isinstance(canonical.get(key), dict) for key in ("architecture", "stack", "uml", "database")):
        return None

    architecture = _section(canonical, "architecture")
    stack = _section(canonical, "stack")
    uml = _section(canonical, "uml")
    database = _section(canonical, "database")

    # Core layers first, then project-specific layers (e.g. real-time
    # messaging): the frontend shows them, the export must not drop them.
    stack_layers: list[dict[str, Any]] = []
    for layer in ("frontend", "backend", "database", "infrastructure"):
        spec = stack.get(layer)
        if isinstance(spec, dict):
            stack_layers.append({"layer": layer, **spec})
    additional = stack.get("additional_layers")
    if isinstance(additional, dict):
        for layer, spec in additional.items():
            if isinstance(spec, dict):
                stack_layers.append({"layer": str(layer), **spec})
    stack_layers = [
        {
            "layer": item["layer"],
            "status": item.get("status") or "",
            "technology": item.get("technology") or "",
            "justification": item.get("justification") or "",
            "alternatives": _string_list(item.get("alternatives")),
        }
        for item in stack_layers
    ]

    tables: list[dict[str, Any]] = []
    for raw in database.get("table_definitions") or []:
        if not isinstance(raw, dict):
            continue
        tables.append(
            {
                "name": raw.get("name") or "",
                "description": raw.get("description") or "",
                "columns": [
                    {
                        "name": col.get("name") or "",
                        "data_type": col.get("data_type") or "",
                        "primary_key": bool(col.get("primary_key")),
                        "nullable": bool(col.get("nullable", True)),
                    }
                    for col in raw.get("columns") or []
                    if isinstance(col, dict)
                ],
                "foreign_keys": [
                    f"{fk.get('column')} -> {fk.get('references_table')}.{fk.get('references_column')}"
                    for fk in raw.get("foreign_keys") or []
                    if isinstance(fk, dict)
                ],
            }
        )

    confidence = canonical.get("confidence")
    return {
        "available": True,
        "style": architecture.get("style") or "",
        "rationale": _string_list(architecture.get("rationale")),
        "quality_attributes": _string_list(architecture.get("quality_attributes")),
        "constraints_addressed": _string_list(architecture.get("constraints_addressed")),
        "risks": _string_list(architecture.get("risks")),
        "alternatives": _string_list(architecture.get("alternatives")),
        "conditions": _string_list(architecture.get("conditions")),
        # Simple {layer: technology} view kept for existing consumers.
        "stack": {
            item["layer"]: item["technology"]
            for item in stack_layers
            if item["technology"]
        },
        "stack_layers": stack_layers,
        "uml_diagrams": {
            diagram_type: (uml.get(diagram_type) or {}).get("source", "")
            for diagram_type in ("use_case", "class_diagram", "sequence", "activity")
            if isinstance(uml.get(diagram_type), dict)
        },
        "database_status": database.get("status") or "",
        "database_dialect": database.get("dialect") or "",
        "database_sql": database.get("sql") or "",
        "database_tables": tables,
        "database_relationships": _string_list(database.get("relationships")),
        "assumptions": _string_list(canonical.get("assumptions")),
        "warnings": _string_list(canonical.get("warnings")),
        "confidence": confidence if isinstance(confidence, (int, float)) else None,
    }


def _assemble_debate_room(analysis_data: Mapping[str, Any]) -> dict[str, Any]:
    debate = _section(analysis_data, "debate_room")
    judge = _section(debate, "judge")

    committee = [
        {
            "role": member.get("role") or "",
            "mandate": member.get("mandate") or "",
            "voting_member": bool(member.get("voting_member")),
        }
        for member in (debate.get("committee") or [])
        if isinstance(member, dict)
    ]

    # Les votes referencent chaque membre par son identifiant technique
    # (ex. "customer_problem_analyst") ; le comite fournit le vrai libelle
    # de role en francais (ex. "Analyste client et problème") pour ce
    # meme identifiant. On traduit une fois ici, jamais dans la couche
    # de rendu, pour que le nom affiche soit toujours coherent avec le
    # tableau de composition du comite.
    role_by_id = {
        raw.get("id"): raw.get("role")
        for raw in (debate.get("committee") or [])
        if isinstance(raw, dict) and raw.get("id")
    }

    votes = [
        {
            "member": role_by_id.get(vote.get("member"), vote.get("member") or ""),
            "vote": vote.get("vote") or "",
            "confidence": vote.get("confidence"),
            "reason": vote.get("reason") or "",
            "veto": bool(vote.get("veto")),
        }
        for vote in (judge.get("committee_votes") or [])
        if isinstance(vote, dict)
    ]

    return {
        "verdict": judge.get("verdict") or "",
        "verdict_code": judge.get("verdict_code") or "",
        "risk_level": judge.get("risk_level") or "",
        "potential_score": judge.get("potential_score"),
        "confidence_score": judge.get("evidence_confidence_score"),
        "execution_readiness_score": judge.get("execution_readiness_score"),
        "investment_attractiveness_score": judge.get(
            "investment_attractiveness_score"
        ),
        "debate_synthesis": judge.get("debate_synthesis") or "",
        "final_recommendation": judge.get("final_recommendation") or "",
        "improved_idea": judge.get("improved_idea") or "",
        "committee": committee,
        "votes": votes,
        "critical_risks": judge.get("critical_risks") or [],
        "missing_evidence": judge.get("missing_evidence") or [],
        "go_conditions": judge.get("go_conditions") or [],
        "no_go_conditions": judge.get("no_go_conditions") or [],
        "next_actions": judge.get("next_actions") or [],
        "rounds_count": len(debate.get("rounds") or []),
    }


def _assemble_sources(analysis_data: Mapping[str, Any]) -> list[dict[str, Any]]:
    """
    Preuves ForgeCrawler : uniquement les sources deja marquees
    "public_display" (jamais les sources internes/rejetees, meme
    politique de confidentialite que le frontend). Chaque source garde
    sa categorie canonique et son score de pertinence, pour une vraie
    tracabilite des affirmations du rapport.
    """
    crawler = _section(analysis_data, "forgecrawler")
    ledger = _section(crawler, "canonical_source_ledger")
    raw_sources = ledger.get("sources") or crawler.get("public_sources") or []

    sources = []
    for raw in raw_sources:
        if not isinstance(raw, dict):
            continue
        if raw.get("public_display") is False:
            continue
        sources.append(
            {
                "title": raw.get("title") or "",
                "url": raw.get("url") or "",
                "category": raw.get("canonical_category") or "",
                "relevance_score": raw.get("source_relevance_score"),
                "is_direct_competitor": bool(raw.get("is_direct_competitor")),
                "why_relevant": raw.get("why_relevant") or "",
            }
        )
    return sources


def assemble_export_data(
    *,
    analysis_data: Mapping[str, Any] | None,
    project_name: str,
    output_language: str | None = None,
) -> dict[str, Any]:
    """
    Point d'entree unique de la couche d'export : lit analysis_data (le
    seul etat canonique en base) et produit une structure Python propre,
    normalisee, avec un seul nom de champ par concept (jamais les
    doublons legacy "value_proposition"/"value_propositions" ou
    "key_partners"/"key_partnerships" observes dans les donnees brutes).

    Aucune mise en forme ici (pas de PDF, pas de style) : ce module ne
    fait qu'assembler la donnee. pdf_builder.py, puis plus tard le
    generateur DOCX et le generateur PPTX, consomment tous cette meme
    sortie sans jamais relire analysis_data directement.
    """
    data = analysis_data if isinstance(analysis_data, dict) else {}
    final_report = _section(data, "final_report")
    startup_score = _section(data, "startup_score")

    return {
        # Project output language: builders pick their labels from it
        # (labels.labels_for), never hard-code them.
        "language": normalize_output_language(output_language),
        "cover": _assemble_cover(data, final_report, project_name),
        "executive_summary": _assemble_executive_summary(final_report),
        "description": _assemble_description(data, startup_score),
        "market_study": _assemble_market_study(data),
        "swot": _assemble_swot(data),
        "business_model_canvas": _assemble_business_model_canvas(data),
        "competitive_analysis": _assemble_competitive_analysis(data),
        "sources": _assemble_sources(data),
        "startup_score": _assemble_startup_score(startup_score),
        "debate_room": _assemble_debate_room(data),
        "personas": _assemble_personas(data),
        "backlog": _assemble_backlog(data),
        "sprint_planning": _assemble_sprint_planning(data),
        "solution_architecture": _assemble_solution_architecture(data),
    }
