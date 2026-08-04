import json
import logging
from typing import Any, Dict

from app.agents.base_agent import BaseAgent
from app.rag.market_rag import MarketRAGService
from app.rag.web_dynamic_rag import DynamicWebRAGService
from app.services.domain_integrity_guard import (
    domain_integrity_guard,
    normalize_output_language,
)
from app.services.project_context_builder import project_context_builder

logger = logging.getLogger(__name__)


class AIBusinessAnalystAgent(BaseAgent):
    """
    Agent Business Analyst dynamique.

    Corrections :
    - Language Lock FR/EN ;
    - Project Context Lock ;
    - RAG global statique prudent ;
    - RAG web local dynamique ;
    - validation anti-contamination avant retour.
    """

    def _get_region(self, input_data: Dict[str, Any]) -> str:
        return str(
            input_data.get("region")
            or input_data.get("market_region")
            or input_data.get("target_region")
            or ""
        ).strip()

    def _get_output_language(self, input_data: Dict[str, Any]) -> str:
        return normalize_output_language(input_data.get("output_language", "fr"))

    def _build_rag_query(self, input_data: Dict[str, Any]) -> str:
        title = input_data.get("title", "")
        description = input_data.get("description", "")
        industry = input_data.get("industry", "")
        region = self._get_region(input_data)

        return (
            f"Title: {title}\n"
            f"Description: {description}\n"
            f"Industry: {industry}\n"
            f"Region: {region}"
        )

    def _get_project_context(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        existing = input_data.get("project_context")

        if isinstance(existing, dict) and existing.get("anchor_terms"):
            return existing

        return project_context_builder.build(
            title=input_data.get("title", ""),
            description=input_data.get("description", ""),
            industry=input_data.get("industry", ""),
            market_region=self._get_region(input_data),
            output_language=self._get_output_language(input_data),
            analysis_data={},
        )

    def _get_global_market_context(
        self,
        input_data: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> str:
        try:
            rag_service = getattr(self, "market_rag", None) or MarketRAGService()

            return rag_service.search_market_context(
                query=self._build_rag_query(input_data),
                top_k=3,
                sector_hint=input_data.get("industry"),
                project_context=project_context,
            )

        except TypeError:
            try:
                rag_service = getattr(self, "market_rag", None) or MarketRAGService()

                return rag_service.search_market_context(
                    query=self._build_rag_query(input_data),
                    top_k=3,
                    sector_hint=input_data.get("industry"),
                )
            except Exception as exc:
                logger.error("[AIBusinessAnalystAgent] Global RAG failed: %s", exc)
                return ""

        except Exception as exc:
            logger.error("[AIBusinessAnalystAgent] Global RAG failed: %s", exc)
            return ""

    async def _get_local_market_context(
        self,
        input_data: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        language = self._get_output_language(input_data)

        try:
            dynamic_web_rag = getattr(self, "dynamic_web_rag", None) or DynamicWebRAGService()

            title = input_data.get("title", "")
            description = input_data.get("description", "")
            industry = input_data.get("industry") or "Non spécifié"
            region = self._get_region(input_data)

            web_description = f"{title}. {description}".strip()

            return await dynamic_web_rag.build_local_context(
                sector=industry,
                region=region,
                description=web_description,
                project_context=project_context,
                output_language=language,
            )

        except Exception as exc:
            logger.error("[AIBusinessAnalystAgent] Local dynamic RAG failed: %s", exc)

            if language == "en":
                local_context = (
                    "No reliable local web context was found. "
                    "The local analysis must remain cautious."
                )
            else:
                local_context = (
                    "Aucun contexte web local fiable n'a été trouvé. "
                    "L'analyse locale doit rester prudente."
                )

            return {
                "local_context": local_context,
                "passages": [],
                "sources": [],
                "web_results_count": 0,
                "chunks_count": 0,
                "cleanup_done": True,
                "error": str(exc),
            }

    def _build_prompt(
        self,
        input_data: Dict[str, Any],
        project_context: Dict[str, Any],
        global_market_context: str,
        local_market_context: str,
    ) -> str:
        language = self._get_output_language(input_data)
        title = input_data.get("title") or "Non spécifié"
        description = input_data.get("description") or "Non spécifiée"
        industry = input_data.get("industry") or "Non spécifié"
        region = self._get_region(input_data)
        structured_context = (
            input_data.get("structured_project_context")
            or (input_data.get("analysis_data") or {}).get("structured_project_context")
            or (input_data.get("project_context") or {}).get("structured_project_context")
            or {}
        )
        structured_context_json = json.dumps(
            structured_context,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

        if language == "en":
            return f"""
You are an expert in startup analysis, innovation strategy, market analysis and business modeling.

Return ONLY one valid JSON object.
Do not add markdown.
Do not add text before or after the JSON.

{project_context.get("language_instruction", "")}

STRICT PROJECT CONTEXT:
{project_context.get("domain_instruction", "")}

PROJECT INPUT:
Title: {title}
Description: {description}
Industry provided by the user: {industry}
Target region: {region or "Not specified"}

CANONICAL STRUCTURED PROJECT CONTEXT:
{structured_context_json}

GLOBAL STATIC RAG CONTEXT:
{global_market_context}

LOCAL DYNAMIC WEB RAG CONTEXT:
{local_market_context}

CONTEXT USAGE RULES:
- Global context is only a general benchmark.
- Local context is more important for local feasibility.
- Never present global figures as local market data.
- Never invent local data if local sources are weak.
- Never reuse examples from another project.
- Stay strictly linked to the user's project input.
- The canonical structured context is authoritative for actors, problem, solution, workflows, MVP scope, metrics and constraints.
- Never replace a specific workflow with a generic phrase such as "complete the core action".
- Keep MVP scope separate from success metrics and constraints.

SCORING RULES:
- innovation_score must be an integer from 1 to 10.
- Do not give 10/10 except for a truly exceptional and validated idea.
- Weak, broad, copied, unclear or unvalidated ideas must receive a low or medium score.

EXPECTED JSON:
{{
  "summary": "2-3 sentence summary",
  "detected_sector": "detected sector",
  "target_region": "{region}",
  "problem": "main problem solved by the idea",
  "target_users": "target user description",
  "innovation_score": 7,
  "recommended_technologies": ["tech1", "tech2", "tech3"],
  "difficulty": "low | medium | high",
  "global_market_assessment": "global market potential assessment",
  "local_market_assessment": "local/regional feasibility assessment based on local dynamic web context",
  "data_limitations": "limits of global and local data used",
  "sources_used": ["source/context 1", "source/context 2"],
  "improvement_suggestions": ["suggestion 1", "suggestion 2", "suggestion 3"]
}}
""".strip()

        return f"""
Tu es un expert en analyse de startups, stratégie d’innovation, étude de marché et business model.

Retourne UNIQUEMENT un objet JSON valide.
N'ajoute pas de markdown.
N'ajoute aucun texte avant ou après le JSON.

{project_context.get("language_instruction", "")}

CONTEXTE PROJET STRICT :
{project_context.get("domain_instruction", "")}

INPUT PROJET :
Titre : {title}
Description : {description}
Secteur indiqué par l'utilisateur : {industry}
Région cible : {region or "Non définie"}

CONTEXTE PROJET STRUCTURÉ CANONIQUE :
{structured_context_json}

CONTEXTE RAG STATIQUE GLOBAL :
{global_market_context}

CONTEXTE RAG WEB DYNAMIQUE LOCAL :
{local_market_context}

RÈGLES D’UTILISATION DU CONTEXTE :
- Le contexte global est seulement un benchmark général.
- Le contexte local est prioritaire pour la faisabilité locale.
- Ne présente jamais des chiffres mondiaux comme des données locales.
- N’invente jamais de données locales si les sources locales sont faibles.
- Ne réutilise jamais des exemples d’un autre projet.
- Reste strictement lié à l’input du projet utilisateur.
- Le contexte structuré canonique est prioritaire pour les acteurs, le problème, la solution, les workflows, le MVP, les métriques et les contraintes.
- Ne remplace jamais un workflow précis par une phrase générique comme « réaliser l’opération terrain principale ».
- Sépare strictement le périmètre MVP, les métriques de réussite et les contraintes.

RÈGLES DE SCORING :
- innovation_score doit être un entier entre 1 et 10.
- Ne donne jamais 10/10 sauf idée réellement exceptionnelle et validée.
- Les idées faibles, trop larges, copiées, floues ou non validées doivent recevoir un score faible ou moyen.

FORMAT JSON ATTENDU :
{{
  "summary": "résumé en 2-3 phrases",
  "detected_sector": "secteur détecté automatiquement",
  "target_region": "{region}",
  "problem": "problème principal que l'idée résout",
  "target_users": "description de la cible utilisateur",
  "innovation_score": 7,
  "recommended_technologies": ["tech1", "tech2", "tech3"],
  "difficulty": "low | medium | high",
  "global_market_assessment": "analyse du potentiel mondial/global",
  "local_market_assessment": "analyse de la faisabilité locale/régionale basée sur le contexte web local dynamique",
  "data_limitations": "limites des données globales et locales utilisées",
  "sources_used": ["source/contexte 1", "source/contexte 2"],
  "improvement_suggestions": ["suggestion 1", "suggestion 2", "suggestion 3"]
}}
""".strip()

    def _post_process_result(
        self,
        result: Dict[str, Any],
        input_data: Dict[str, Any],
        project_context: Dict[str, Any],
        local_rag_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        language = self._get_output_language(input_data)
        region = self._get_region(input_data)

        if not isinstance(result, dict):
            return {
                "error": "invalid_llm_result",
                "raw": str(result)[:500],
            }

        if result.get("error"):
            return result

        if "innovation_score" in result and isinstance(result["innovation_score"], (int, float)):
            result["innovation_score"] = max(1, min(10, int(result["innovation_score"])))
        else:
            result["innovation_score"] = 5

        difficulty = str(result.get("difficulty") or "medium").lower()

        if difficulty not in {"low", "medium", "high"}:
            difficulty = "medium"

        result["difficulty"] = difficulty

        if not isinstance(result.get("recommended_technologies"), list):
            result["recommended_technologies"] = (
                ["Frontend web", "Backend API", "Database"]
                if language == "en"
                else ["Frontend web", "API backend", "Base de données"]
            )

        result["recommended_technologies"] = [
            str(item).strip()
            for item in result["recommended_technologies"][:7]
            if str(item).strip()
        ]

        while len(result["recommended_technologies"]) < 3:
            result["recommended_technologies"].append(
                "Technology to validate" if language == "en" else "Technologie à valider"
            )

        if not isinstance(result.get("improvement_suggestions"), list):
            result["improvement_suggestions"] = []

        while len(result["improvement_suggestions"]) < 3:
            result["improvement_suggestions"].append(
                "Clarify the MVP and validate it with target users."
                if language == "en"
                else "Clarifier le MVP et le valider auprès des utilisateurs ciblés."
            )

        result["improvement_suggestions"] = result["improvement_suggestions"][:3]

        if not result.get("target_region"):
            result["target_region"] = region

        if not isinstance(result.get("sources_used"), list):
            result["sources_used"] = []

        local_market_candidates = []
        local_market_sources = []
        for source in local_rag_result.get("sources") or []:
            if not isinstance(source, dict) or not source.get("url"):
                continue
            result["sources_used"].append(str(source["url"]))

            # Preserve every non-rejected local candidate for one final
            # canonical re-evaluation. LocalMarketSearch intentionally accepts
            # useful internal evidence for RAG; filtering only public_display
            # here disconnected valid local pages from CompetitiveAnalysis.
            if not bool(source.get("rejected")):
                local_market_candidates.append(dict(source))

            if (
                bool(source.get("public_display"))
                and not bool(source.get("internal_only"))
                and not bool(source.get("rejected"))
            ):
                local_market_sources.append(dict(source))

        # Internal hand-off only. The public sanitizer removes both keys after
        # CompetitiveAnalysis has built the canonical ledger.
        result["local_market_candidates"] = local_market_candidates
        result["local_market_sources"] = local_market_sources

        if not result["sources_used"]:
            result["sources_used"] = (
                ["Static global RAG context", "Dynamic local web context"]
                if language == "en"
                else ["Contexte RAG statique global", "Contexte web local dynamique"]
            )

        structured = (
            input_data.get("structured_project_context")
            or (input_data.get("analysis_data") or {}).get("structured_project_context")
            or project_context.get("structured_project_context")
            or {}
        )
        if isinstance(structured, dict):
            result["target_region"] = structured.get("target_region") or region
            result["problem"] = structured.get("problem") or result.get("problem")
            result["target_users"] = structured.get("target_users") or result.get("target_users")
            result["project_archetype"] = structured.get("project_archetype")
            result["priority_workflows"] = structured.get("priority_workflows") or []
            result["mvp_scope"] = structured.get("mvp_scope") or ""
            result["success_metrics"] = structured.get("success_metrics") or []
            result["constraints"] = structured.get("constraints") or []
            result["business_model"] = structured.get("business_model") or ""
            result["solution"] = structured.get("solution") or result.get("solution")

        validation = domain_integrity_guard.validate_object(
            data=result,
            project_context=project_context,
        )

        if not validation["is_valid"]:
            result = domain_integrity_guard.sanitize_object(
                data=result,
                project_context=project_context,
            )

        return result

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(
            "[AIBusinessAnalystAgent] Start | project=%s",
            input_data.get("title", "Sans titre"),
        )

        language = self._get_output_language(input_data)

        project_context = self._get_project_context(input_data)

        global_market_context = self._get_global_market_context(
            input_data=input_data,
            project_context=project_context,
        )

        if not global_market_context:
            global_market_context = (
                "No global static RAG context is available. The global assessment must remain cautious."
                if language == "en"
                else "Aucun contexte RAG global disponible. L'analyse globale doit rester prudente."
            )

        local_rag_result = await self._get_local_market_context(
            input_data=input_data,
            project_context=project_context,
        )

        local_market_context = local_rag_result.get("local_context") or (
            "No reliable local web context was found."
            if language == "en"
            else "Aucun contexte web local fiable n'a été trouvé."
        )

        prompt = self._build_prompt(
            input_data=input_data,
            project_context=project_context,
            global_market_context=global_market_context,
            local_market_context=local_market_context,
        )

        raw_response = await self.llm.invoke(
            prompt,
            task_type="business_analysis_dynamic_context_locked",
        )

        result = self._parse_json_response(raw_response)

        result = self._post_process_result(
            result=result,
            input_data=input_data,
            project_context=project_context,
            local_rag_result=local_rag_result,
        )

        result["project_context_meta"] = {
            "domain_label": project_context.get("domain_label"),
            "output_language": language,
            "anchor_terms": project_context.get("anchor_terms", [])[:30],
        }

        return result