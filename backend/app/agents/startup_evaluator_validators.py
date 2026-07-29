from typing import Any, Dict, List

from app.services.domain_integrity_guard import normalize_output_language


def ensure_list(value: Any) -> List[str]:
    if value is None:
        return []

    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    if isinstance(value, str):
        return [value.strip()] if value.strip() else []

    return [str(value).strip()]


def ensure_min_items(
    items: List[str],
    min_items: int,
    fallback_prefix: str,
    output_language: str = "fr",
) -> List[str]:
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    language = normalize_output_language(output_language)

    while len(cleaned) < min_items:
        if language == "en":
            cleaned.append(f"{fallback_prefix} to clarify further.")
        else:
            cleaned.append(f"{fallback_prefix} à préciser davantage.")

    return cleaned


def clamp_score(value: Any, default: int = 5) -> int:
    try:
        score = int(round(float(value)))
    except Exception:
        score = default

    return max(1, min(10, score))


def _fallbacks(output_language: str) -> Dict[str, str]:
    language = normalize_output_language(output_language)

    if language == "en":
        return {
            "market_size": "Market to estimate with additional data.",
            "target_market": "Target segment to clarify.",
            "trend": "Market trend",
            "segment": "Customer segment",
            "opportunity": "Opportunity",
            "risk": "Risk",
            "strength": "Strength",
            "weakness": "Weakness",
            "threat": "Threat",
            "value_proposition": "Value proposition to clarify.",
            "customer_segments": "Customer segments to clarify.",
            "channels": "Channels to clarify.",
            "customer_relationships": "Customer relationship to clarify.",
            "revenue_streams": "Revenue streams to clarify.",
            "key_resources": "Key resources to clarify.",
            "key_activities": "Key activities to clarify.",
            "key_partners": "Key partners to clarify.",
            "cost_structure": "Cost structure to clarify.",
            "mvp_budget": "MVP budget to estimate.",
            "infrastructure_cost": "Infrastructure cost to estimate.",
            "revenue": "Revenue source",
            "roi": "ROI outlook to clarify.",
            "score_explanation": "Score calculated from strategic dimensions.",
            "score_warning": "Exceptional score detected — human review recommended.",
        }

    return {
        "market_size": "Marché à estimer avec des données complémentaires.",
        "target_market": "Segment cible à préciser.",
        "trend": "Tendance marché",
        "segment": "Segment client",
        "opportunity": "Opportunité",
        "risk": "Risque",
        "strength": "Force",
        "weakness": "Faiblesse",
        "threat": "Menace",
        "value_proposition": "Proposition de valeur à préciser.",
        "customer_segments": "Segments clients à préciser.",
        "channels": "Canaux à préciser.",
        "customer_relationships": "Relation client à préciser.",
        "revenue_streams": "Sources de revenus à préciser.",
        "key_resources": "Ressources clés à préciser.",
        "key_activities": "Activités clés à préciser.",
        "key_partners": "Partenaires clés à préciser.",
        "cost_structure": "Structure de coûts à préciser.",
        "mvp_budget": "Budget MVP à estimer.",
        "infrastructure_cost": "Coût infrastructure à estimer.",
        "revenue": "Source de revenu",
        "roi": "ROI prévisionnel à préciser.",
        "score_explanation": "Score calculé à partir des dimensions stratégiques.",
        "score_warning": "Score exceptionnel détecté — validation humaine recommandée.",
    }


def validate_market_study(
    data: Dict[str, Any],
    output_language: str = "fr",
) -> Dict[str, Any]:
    fb = _fallbacks(output_language)

    return {
        "market_size": str(data.get("market_size") or fb["market_size"]),
        "target_market": str(data.get("target_market") or fb["target_market"]),
        "market_trends": ensure_min_items(
            ensure_list(data.get("market_trends")),
            3,
            fb["trend"],
            output_language,
        ),
        "customer_segments": ensure_min_items(
            ensure_list(data.get("customer_segments")),
            3,
            fb["segment"],
            output_language,
        ),
        "opportunities": ensure_min_items(
            ensure_list(data.get("opportunities")),
            3,
            fb["opportunity"],
            output_language,
        ),
        "risks": ensure_min_items(
            ensure_list(data.get("risks")),
            3,
            fb["risk"],
            output_language,
        ),
        "data_confidence": str(data.get("data_confidence") or "medium"),
    }


def validate_swot(
    data: Dict[str, Any],
    output_language: str = "fr",
) -> Dict[str, Any]:
    fb = _fallbacks(output_language)

    return {
        "strengths": ensure_min_items(
            ensure_list(data.get("strengths")),
            3,
            fb["strength"],
            output_language,
        ),
        "weaknesses": ensure_min_items(
            ensure_list(data.get("weaknesses")),
            3,
            fb["weakness"],
            output_language,
        ),
        "opportunities": ensure_min_items(
            ensure_list(data.get("opportunities")),
            3,
            fb["opportunity"],
            output_language,
        ),
        "threats": ensure_min_items(
            ensure_list(data.get("threats")),
            3,
            fb["threat"],
            output_language,
        ),
    }


def validate_bmc(
    data: Dict[str, Any],
    output_language: str = "fr",
) -> Dict[str, Any]:
    fb = _fallbacks(output_language)

    return {
        "value_proposition": str(data.get("value_proposition") or fb["value_proposition"]),
        "customer_segments": str(data.get("customer_segments") or fb["customer_segments"]),
        "channels": str(data.get("channels") or fb["channels"]),
        "customer_relationships": str(data.get("customer_relationships") or fb["customer_relationships"]),
        "revenue_streams": str(data.get("revenue_streams") or fb["revenue_streams"]),
        "key_resources": str(data.get("key_resources") or fb["key_resources"]),
        "key_activities": str(data.get("key_activities") or fb["key_activities"]),
        "key_partners": str(data.get("key_partners") or fb["key_partners"]),
        "cost_structure": str(data.get("cost_structure") or fb["cost_structure"]),
    }


def validate_financial_estimation(
    data: Dict[str, Any],
    output_language: str = "fr",
) -> Dict[str, Any]:
    fb = _fallbacks(output_language)

    return {
        "mvp_budget_estimate": str(data.get("mvp_budget_estimate") or fb["mvp_budget"]),
        "infrastructure_cost_estimate": str(
            data.get("infrastructure_cost_estimate") or fb["infrastructure_cost"]
        ),
        "possible_revenue_streams": ensure_min_items(
            ensure_list(data.get("possible_revenue_streams")),
            3,
            fb["revenue"],
            output_language,
        ),
        "roi_outlook": str(data.get("roi_outlook") or fb["roi"]),
        "financial_risk_level": str(data.get("financial_risk_level") or "medium"),
    }


def validate_startup_score(
    data: Dict[str, Any],
    output_language: str = "fr",
) -> Dict[str, Any]:
    fb = _fallbacks(output_language)

    innovation = clamp_score(data.get("innovation"), default=7)
    feasibility = clamp_score(data.get("feasibility"), default=6)
    profitability = clamp_score(data.get("profitability"), default=6)
    scalability = clamp_score(data.get("scalability"), default=7)

    manual_review_required = bool(data.get("manual_review_required", False))
    score_warning = data.get("score_warning")

    if innovation == 10 and feasibility == 10 and profitability == 10 and scalability == 10:
        feasibility = 8
        manual_review_required = True
        score_warning = fb["score_warning"]

    global_score = round(
        (innovation + feasibility + profitability + scalability) / 4,
        2,
    )

    return {
        "innovation": innovation,
        "feasibility": feasibility,
        "profitability": profitability,
        "scalability": scalability,
        "global_score": global_score,
        "score_explanation": str(data.get("score_explanation") or fb["score_explanation"]),
        "manual_review_required": manual_review_required,
        "score_warning": score_warning,
    }