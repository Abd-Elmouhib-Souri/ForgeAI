from __future__ import annotations

from typing import Any, Dict, Optional

from app.services.domain_integrity_guard import (
    domain_integrity_guard,
    normalize_output_language,
)


class ProjectContextBuilder:
    """
    Centralise le Project Context Lock + Language Lock.

    Tous les graphs et agents doivent recevoir ce contexte.
    """

    def build(
        self,
        *,
        title: str,
        description: str,
        industry: Optional[str] = None,
        market_region: Optional[str] = None,
        output_language: str = "fr",
        analysis_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        language = normalize_output_language(output_language)

        context = domain_integrity_guard.build_project_context(
            title=title or "",
            description=description or "",
            industry=industry or "",
            market_region=market_region or "",
            output_language=language,
            analysis_data=analysis_data or {},
        )

        context["output_language"] = language
        context["language_name"] = "English" if language == "en" else "Français"
        context["language_instruction"] = domain_integrity_guard.language_instruction(
            language
        )

        return context

    def project_payload(
        self,
        *,
        project_id: int | None,
        title: str,
        description: str,
        industry: Optional[str],
        market_region: Optional[str],
        output_language: str,
    ) -> Dict[str, Any]:
        language = normalize_output_language(output_language)

        return {
            "project_id": project_id,
            "title": title or "",
            "description": description or "",
            "industry": industry or "Non spécifié",
            "market_region": market_region or "Tunisie",
            "output_language": language,
        }


project_context_builder = ProjectContextBuilder()