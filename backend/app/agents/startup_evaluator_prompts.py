import json
from typing import Any, Dict

from app.services.domain_integrity_guard import normalize_output_language


def _safe_json(data: Any, max_chars: int = 6000) -> str:
    try:
        text = json.dumps(data, ensure_ascii=False, indent=2)
    except Exception:
        text = str(data)

    return text[:max_chars]


def _language(state: Dict[str, Any]) -> str:
    return normalize_output_language(state.get("output_language", "fr"))


def _json_language_rule(language: str) -> str:
    if language == "en":
        return (
            "LANGUAGE LOCK: every JSON string value must be written in English. "
            "Keep JSON keys exactly as specified."
        )

    return (
        "LANGUAGE LOCK : toutes les valeurs textuelles du JSON doivent être en français. "
        "Garde exactement les clés JSON demandées."
    )


def build_common_context(state: Dict[str, Any]) -> str:
    analysis_data = state.get("analysis_data") or {}
    project_context = state.get("project_context") or {}
    language = _language(state)

    if language == "en":
        return f"""
PROJECT TO ANALYZE

Title:
{state.get("title", "")}

Description:
{state.get("description", "")}

Industry:
{state.get("industry") or "Not specified"}

Target region:
{state.get("region") or "Tunisia"}

Dynamic Project Context:
{project_context.get("domain_instruction", "")}

Previous analysis:
{_safe_json(analysis_data)}
""".strip()

    return f"""
PROJET À ANALYSER

Titre :
{state.get("title", "")}

Description :
{state.get("description", "")}

Secteur :
{state.get("industry") or "Non spécifié"}

Région cible :
{state.get("region") or "Tunisie"}

Contexte dynamique verrouillé :
{project_context.get("domain_instruction", "")}

Analyse déjà générée :
{_safe_json(analysis_data)}
""".strip()


def build_market_study_prompt(state: Dict[str, Any]) -> str:
    context = build_common_context(state)
    language = _language(state)
    language_rule = _json_language_rule(language)

    if language == "en":
        role = "You are a startup market research expert."
        task = "Generate a realistic, cautious and contextual market study."
        rules = """
Rules:
- Do not invent precise numbers when no source is available.
- Mention uncertainty when data is limited.
- Adapt the analysis to the target country or region.
- Stay strictly linked to the user's project input.
"""
        structure = """
{
  "market_size": "market size or cautious qualitative estimate",
  "target_market": "precise target market",
  "market_trends": ["trend 1", "trend 2", "trend 3"],
  "customer_segments": ["segment 1", "segment 2", "segment 3"],
  "opportunities": ["opportunity 1", "opportunity 2", "opportunity 3"],
  "risks": ["risk 1", "risk 2", "risk 3"],
  "data_confidence": "low | medium | high"
}
"""
    else:
        role = "Tu es un expert en étude de marché pour startups."
        task = "Génère une étude de marché claire, réaliste et contextualisée."
        rules = """
Règles :
- Ne pas inventer de chiffre précis si aucune source n'est disponible.
- Mentionner les limites si les données sont incertaines.
- Adapter l'analyse au pays ou à la région cible.
- Rester strictement lié à l’input du projet utilisateur.
"""
        structure = """
{
  "market_size": "taille du marché ou estimation qualitative prudente",
  "target_market": "marché cible précis",
  "market_trends": ["tendance 1", "tendance 2", "tendance 3"],
  "customer_segments": ["segment 1", "segment 2", "segment 3"],
  "opportunities": ["opportunité 1", "opportunité 2", "opportunité 3"],
  "risks": ["risque 1", "risque 2", "risque 3"],
  "data_confidence": "low | medium | high"
}
"""

    return f"""
{role}

{task}

{language_rule}

{context}

Return only valid JSON.
No markdown.
No text outside JSON.

Required JSON structure:
{structure}

{rules}
""".strip()


def build_swot_prompt(state: Dict[str, Any]) -> str:
    context = build_common_context(state)
    language = _language(state)
    language_rule = _json_language_rule(language)

    if language == "en":
        role = "You are a startup strategy consultant."
        rules = """
Rules:
- Minimum 3 items per category.
- Points must be specific to the current project.
- Avoid generic statements like "good idea" or "interesting market".
"""
        structure = """
{
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "weaknesses": ["weakness 1", "weakness 2", "weakness 3"],
  "opportunities": ["opportunity 1", "opportunity 2", "opportunity 3"],
  "threats": ["threat 1", "threat 2", "threat 3"]
}
"""
    else:
        role = "Tu es un consultant stratégie startup."
        rules = """
Règles :
- Minimum 3 éléments par catégorie.
- Les points doivent être spécifiques au projet actuel.
- Évite les phrases génériques comme "bonne idée" ou "marché intéressant".
"""
        structure = """
{
  "strengths": ["force 1", "force 2", "force 3"],
  "weaknesses": ["faiblesse 1", "faiblesse 2", "faiblesse 3"],
  "opportunities": ["opportunité 1", "opportunité 2", "opportunité 3"],
  "threats": ["menace 1", "menace 2", "menace 3"]
}
"""

    return f"""
{role}

{language_rule}

{context}

Return only valid JSON.
No markdown.
No text outside JSON.

Required JSON structure:
{structure}

{rules}
""".strip()


def build_bmc_prompt(state: Dict[str, Any]) -> str:
    context = build_common_context(state)
    language = _language(state)
    language_rule = _json_language_rule(language)

    if language == "en":
        role = "You are a Business Model Canvas expert."
        rules = """
Rules:
- Every block must be concrete and useful.
- Adapt to the project context and target region.
- Do not use lists of objects, only text per block.
"""
        structure = """
{
  "value_proposition": "clear value proposition",
  "customer_segments": "priority customer segments",
  "channels": "acquisition and distribution channels",
  "customer_relationships": "customer relationship type",
  "revenue_streams": "revenue sources",
  "key_resources": "key resources",
  "key_activities": "key activities",
  "key_partners": "key partners",
  "cost_structure": "cost structure"
}
"""
    else:
        role = "Tu es un expert Business Model Canvas."
        rules = """
Règles :
- Chaque bloc doit être concret et utile.
- Adapter au contexte du projet et à la région cible.
- Ne pas mettre de listes d'objets, uniquement du texte par bloc.
"""
        structure = """
{
  "value_proposition": "proposition de valeur claire",
  "customer_segments": "segments clients prioritaires",
  "channels": "canaux d'acquisition et distribution",
  "customer_relationships": "type de relation client",
  "revenue_streams": "sources de revenus",
  "key_resources": "ressources clés",
  "key_activities": "activités clés",
  "key_partners": "partenaires clés",
  "cost_structure": "structure de coûts"
}
"""

    return f"""
{role}

{language_rule}

{context}

Return only valid JSON.
No markdown.
No text outside JSON.

Required JSON structure:
{structure}

{rules}
""".strip()


def build_financial_estimation_prompt(state: Dict[str, Any]) -> str:
    context = build_common_context(state)
    language = _language(state)
    language_rule = _json_language_rule(language)

    if language == "en":
        role = "You are a startup financial analyst."
        rules = """
Rules:
- Stay cautious.
- Do not give unrealistic financial promises.
- Adapt to local context when possible.
- If cost data is missing, write that field validation is required.
"""
        structure = """
{
  "mvp_budget_estimate": "MVP budget estimate",
  "infrastructure_cost_estimate": "infrastructure cost estimate",
  "possible_revenue_streams": ["revenue 1", "revenue 2", "revenue 3"],
  "roi_outlook": "cautious ROI outlook",
  "financial_risk_level": "low | medium | high"
}
"""
    else:
        role = "Tu es un analyste financier startup."
        rules = """
Règles :
- Rester prudent.
- Ne pas donner de promesse financière irréaliste.
- Adapter au contexte local si possible.
- Si les données de coût manquent, dire qu’une validation terrain est nécessaire.
"""
        structure = """
{
  "mvp_budget_estimate": "estimation du budget MVP",
  "infrastructure_cost_estimate": "estimation des coûts infrastructure",
  "possible_revenue_streams": ["revenu 1", "revenu 2", "revenu 3"],
  "roi_outlook": "perspective ROI prudente",
  "financial_risk_level": "low | medium | high"
}
"""

    return f"""
{role}

{language_rule}

{context}

Return only valid JSON.
No markdown.
No text outside JSON.

Required JSON structure:
{structure}

{rules}
""".strip()


def build_startup_score_prompt(state: Dict[str, Any]) -> str:
    context = build_common_context(state)
    language = _language(state)
    language_rule = _json_language_rule(language)

    if language == "en":
        role = "You are a startup evaluation committee."
        rules = """
Rules:
- Each score must be between 1 and 10.
- Never give 10/10 everywhere except for a truly exceptional case.
- Innovation = originality and differentiation.
- Feasibility = technical and operational feasibility.
- Profitability = revenue potential versus cost.
- Scalability = ability to grow.
- Be strict with broad, unclear or unvalidated ideas.
"""
        explanation = "short and clear explanation"
    else:
        role = "Tu es un comité d'évaluation startup."
        rules = """
Règles :
- Chaque score doit être entre 1 et 10.
- Ne donne jamais 10/10 partout sauf cas réellement exceptionnel.
- Innovation = originalité et différenciation.
- Feasibility = faisabilité technique et opérationnelle.
- Profitability = potentiel de revenus vs coûts.
- Scalability = capacité à grandir.
- Sois strict avec les idées trop larges, floues ou non validées.
"""
        explanation = "explication courte et claire"

    return f"""
{role}

{language_rule}

{context}

Return only valid JSON.
No markdown.
No text outside JSON.

Required JSON structure:
{{
  "innovation": 1,
  "feasibility": 1,
  "profitability": 1,
  "scalability": 1,
  "score_explanation": "{explanation}",
  "manual_review_required": false
}}

{rules}
""".strip()