import type { ForgeLang } from "@/lib/language-context";

import type {
  AnalysisData,
  FactCheckClaim,
  PersonaBuilderData,
  Project,
  SourceDisplayContext,
  SourceItem,
} from "../_types/project-detail.types";

import {
  isGlobalRegion,
  shortenText,
  uniqueStrings,
} from "./formatters";

import {
  cleanText,
  isBadCollapsedSourceText,
  normalizeSourceText,
} from "./text-cleaning";

export function getReportLanguage(
  project?: Project | null,
  analysisData?: AnalysisData | null,
  fallback: ForgeLang = "fr"
): ForgeLang {
  const raw =
    project?.output_language ||
    analysisData?.output_language ||
    analysisData?.debate_room?.output_language ||
    analysisData?.startup_score?.output_language ||
    fallback;

  return raw === "en" ? "en" : "fr";
}

export function hasSprint3Data(analysisData?: AnalysisData | null): boolean {
  if (!analysisData) return false;

  return Boolean(
    analysisData.market_study ||
      analysisData.swot ||
      analysisData.business_model_canvas ||
      analysisData.forgecrawler ||
      analysisData.competitive_analysis ||
      analysisData.financial_estimation ||
      analysisData.startup_score ||
      analysisData.persona_builder ||
      analysisData.personas ||
      analysisData.fact_check_report ||
      analysisData.debate_room
  );
}

export function getPersonaBuilderData(
  analysisData?: AnalysisData | null
): PersonaBuilderData | null {
  if (!analysisData) return null;

  return analysisData.persona_builder || analysisData.personas || null;
}

export function getOfficialStartupScore(
  analysisData?: AnalysisData | null,
  fallbackScore?: number | null
): number | null {
  const scoreData =
    analysisData?.startup_score || {};

  const candidates = [
    scoreData.potential_score,
    scoreData.score,
    scoreData.startup_score,
    scoreData.overall_score,
    scoreData.final_score,
    scoreData.score_out_of_10,
    scoreData.global_score,
  ];

  for (const candidate of candidates) {
    if (
      typeof candidate === "number" &&
      Number.isFinite(candidate)
    ) {
      const score = candidate;

      if (
        score >= 0 &&
        score <= 10
      ) {
        return score;
      }
    }
  }

  if (
    typeof fallbackScore === "number" &&
    Number.isFinite(fallbackScore)
  ) {
    return fallbackScore;
  }

  return null;
}


export function getConcreteSolution(
  analysisData: AnalysisData,
  project: Project
): string {
  const structured =
    (analysisData.project_intelligence as { structured_project_context?: Record<string, unknown> } | undefined)
      ?.structured_project_context || {};

  const structuredSolution = String(structured.solution || "").trim();
  const proposedSolution = String(analysisData.proposed_solution || "").trim();

  for (const candidate of [structuredSolution, proposedSolution]) {
    const cleaned = extractSolutionOnly(candidate);
    if (cleaned && !isGenericSolution(cleaned)) return cleaned;
  }

  const descriptionSolution = extractLabeledSolution(project.description || "");
  if (descriptionSolution) return descriptionSolution;

  const improvedIdea = analysisData.debate_room?.judge?.improved_idea;
  return improvedIdea || "—";
}

function extractLabeledSolution(value: string): string {
  const match = value.match(
    /(?:the solution is|proposed solution|solution\s*:|la solution est|solution proposée\s*:|solution proposee\s*:)([\s\S]*?)(?=(?:the first target users|target users|the mvp|mvp\s*:|the business model|business model|les utilisateurs cibles|le mvp|modèle économique|modele economique)|$)/i
  );
  return extractSolutionOnly(match?.[1] || "");
}

function extractSolutionOnly(value: string): string {
  let result = String(value || "").replace(/\s+/g, " ").trim();
  if (!result) return "";

  const contamination = [
    /\bthe problem is\b/i,
    /\bthis makes it hard\b/i,
    /\ble problème est\b/i,
    /\bce qui rend\b/i,
  ];

  for (const marker of contamination) {
    const match = marker.exec(result);
    if (match && match.index > 0) result = result.slice(0, match.index).trim();
  }

  return result.replace(/[.\s]+$/, ".");
}

export function isGenericSolution(value: string): boolean {
  const lower = value.toLowerCase();

  return (
    lower.includes("solution numérique adaptée au secteur") ||
    lower.includes("mvp à valider sur le terrain") ||
    lower.includes("mvp a valider sur le terrain") ||
    lower.includes("clear mvp directly based on the user's project description")
  );
}

export function getPublicLocalMarketAssessment(
  analysisData: AnalysisData,
  project: Project,
  language: ForgeLang = "fr"
): string {
  const value = analysisData.local_market_assessment || "";
  const region = project.market_region || analysisData.target_region || "";

  if (isGlobalRegion(region) && value.toLowerCase().includes("tunisie")) {
    if (language === "en") {
      return (
        "The project targets a global market. Before any international expansion, " +
        "ForgeAI recommends choosing a precise initial market to test demand, " +
        "acceptable pricing, user acquisition and real competition."
      );
    }

    return (
      "Le projet vise un marché global. Avant toute extension internationale, " +
      "ForgeAI recommande de choisir un marché initial précis pour tester le besoin, " +
      "le prix acceptable, l’acquisition utilisateur et la concurrence réelle."
    );
  }

  return value || "—";
}

export function getPublicAnalysisWarning(
  value?: string | null,
  status?: string | null,
  language: ForgeLang = "fr"
): string {
  if (!value) return "";

  const lowered = value.toLowerCase();

  const partialMarkers = [
    "partiellement",
    "partially",
    "n’a pas pu être complétée automatiquement",
    "n'a pas pu être complétée automatiquement",
    "could not be completed automatically",
  ];

  const isPartialMessage = partialMarkers.some((marker) =>
    lowered.includes(marker)
  );

  if (status === "completed" && isPartialMessage) {
    if (language === "en") {
      return (
        "Analysis completed. Some information should be confirmed through " +
        "field validation before any final decision."
      );
    }

    return (
      "Analyse terminée. Certaines informations doivent être confirmées par " +
      "une validation terrain avant décision finale."
    );
  }

  return cleanText(value, language);
}

export function publicAnalysisStep(
  value?: string | null,
  language: ForgeLang = "fr"
): string {
  if (!value) return "—";

  const cleaned = cleanText(value, language);

  if (language === "en") {
    return cleaned
      .replaceAll("Sprint 2", "Initial analysis")
      .replaceAll("Sprint 3", "Strategic analysis")
      .replaceAll("Startup Evaluator", "Strategic evaluator")
      .replaceAll("startup_evaluator", "strategic evaluator")
      .replaceAll("Debate Room", "Strategic debate")
      .replaceAll("Fact Checker", "Claim verification")
      .replaceAll("fact_checker", "claim verification")
      .replaceAll("Self-Correction RAG", "Claim verification")
      .replaceAll("persona_builder", "Customer personas")
      .replaceAll("Persona Builder", "Customer personas")
      .replaceAll("Analyse Sprint 3 + Debate Room terminée", "Strategic analysis completed")
      .replaceAll("Analyse terminée", "Analysis completed")
      .replaceAll("terminée partiellement", "completed")
      .replaceAll("terminé partiellement", "completed")
      .replaceAll("completed partially", "completed")
      .replaceAll("idle", "Idle");
  }

  return cleaned
    .replaceAll("Sprint 2", "Analyse initiale")
    .replaceAll("Sprint 3", "Analyse stratégique")
    .replaceAll("Startup Evaluator", "Évaluation stratégique")
    .replaceAll("startup_evaluator", "évaluation stratégique")
    .replaceAll("Debate Room", "Débat stratégique")
    .replaceAll("Fact Checker", "Vérification des affirmations")
    .replaceAll("fact_checker", "Vérification des affirmations")
    .replaceAll("Self-Correction RAG", "Vérification des affirmations")
    .replaceAll("persona_builder", "Personas clients")
    .replaceAll("Persona Builder", "Personas clients")
    .replaceAll("Analyse Analyse stratégique", "Analyse stratégique")
    .replaceAll("Analyse stratégique Analyse stratégique", "Analyse stratégique")
    .replaceAll("Analyse Analyse", "Analyse")
    .replaceAll("terminée partiellement", "terminée")
    .replaceAll("terminé partiellement", "terminé")
    .replaceAll("completed partially", "terminée")
    .replaceAll("idle", "En attente");
}

export function getSourceDisplayContext(
  project: Project,
  analysisData: AnalysisData,
  language: ForgeLang = "fr"
): SourceDisplayContext {
  const region = project.market_region || analysisData.target_region || "";
  const isGlobal = isGlobalRegion(region);

  if (language === "en") {
    return {
      isGlobal,
      directMetricLabel: isGlobal ? "Comparable solutions" : "Local competitors",
      directGroupTitle: isGlobal
        ? "Verified comparable solutions"
        : "Verified local competitors",
      directEmptyText: isGlobal
        ? "No verified comparable solution."
        : "No verified direct local competitor.",
      adjacentGroupTitle: isGlobal
        ? "Adjacent solutions"
        : "Local adjacent solutions",
      adjacentEmptyText: isGlobal
        ? "No adjacent solution found."
        : "No local adjacent solution found.",
    };
  }

  return {
    isGlobal,
    directMetricLabel: isGlobal ? "Solutions comparables" : "Concurrents locaux",
    directGroupTitle: isGlobal
      ? "Solutions comparables vérifiées"
      : "Concurrents locaux vérifiés",
    directEmptyText: isGlobal
      ? "Aucune solution comparable vérifiée."
      : "Aucun concurrent local direct vérifié.",
    adjacentGroupTitle: isGlobal
      ? "Solutions adjacentes"
      : "Solutions adjacentes locales",
    adjacentEmptyText: isGlobal
      ? "Aucune solution adjacente remontée."
      : "Aucune solution adjacente locale remontée.",
  };
}

export function getPublicDisplaySources(sources: SourceItem[]): SourceItem[] {
  return sources.filter((source) => {
    const title = String(source.title || "").trim();
    const url = String(source.url || "").trim();
    const type = String(source.source_type || "").trim();
    const snippet = String(source.snippet || "").trim();
    const normalizedSnippet = normalizeSourceText(snippet);

    if (!title && !url) return false;
    if (type === "irrelevant") return false;
    if (source.rejected) return false;
    if (source.internal_only) return false;
    if (source.public_display === false) return false;

    if (
      url.includes("youtube.com") &&
      (isBadCollapsedSourceText(normalizedSnippet) || snippet.length < 40)
    ) {
      return false;
    }

    return true;
  });
}

export function getPublicTextItems(
  items: string[],
  language: ForgeLang = "fr"
): string[] {
  return uniqueStrings(
    items
      .map((item) => normalizeSourceText(item))
      .filter((item) => item.length > 0)
      .filter((item) => !isBadCollapsedSourceText(item))
      .map((item) => cleanText(shortenText(item, 320), language))
  );
}

export function getPublicSourceReason(
  source: SourceItem,
  language: ForgeLang = "fr"
): string {
  const reason = source.why_relevant || "";
  if (!reason) return "";
  return cleanText(normalizeSourceText(reason), language);
}

export function getPublicSourceSnippet(
  source: SourceItem,
  language: ForgeLang = "fr"
): string {
  const raw = source.snippet || source.extracted_text_preview || "";
  if (!raw) return "";

  const normalized = normalizeSourceText(raw);

  if (isBadCollapsedSourceText(normalized)) {
    return "";
  }

  return cleanText(shortenText(normalized, 520), language);
}

export function getPriorityFactClaims(
  claims: FactCheckClaim[],
  maxItems?: number
): FactCheckClaim[] {
  const categoryPriority: Record<string, number> = {
    finance: 100,
    market_size: 95,
    target_users: 90,
    target_market: 90,
    problem: 85,
    solution: 80,
    local_competitors_count: 78,
    local_competition: 78,
    competitive_gap: 75,
    personas: 70,
    business_model: 68,
    startup_score: 60,
  };

  const statusPriority: Record<string, number> = {
    not_confirmed: 100,
    field_validation_required: 90,
    estimated: 70,
    sourced: 30,
  };

  const seen = new Set<string>();

  const ordered = [...claims]
    .map((claim, index) => {
      const category = claim.category || "";
      const status = claim.status || "";
      const score =
        (categoryPriority[category] ?? 40) + (statusPriority[status] ?? 20);

      return { claim, index, score };
    })
    .sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      return a.index - b.index;
    })
    .filter(({ claim }) => {
      const key = `${claim.path || ""}|${claim.category || ""}|${
        claim.claim || ""
      }`
        .trim()
        .toLowerCase();

      if (!key || seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .map((item) => item.claim);

  if (
    typeof maxItems === "number" &&
    Number.isFinite(maxItems) &&
    maxItems > 0
  ) {
    return ordered.slice(0, maxItems);
  }

  return ordered;
}
export function isVerifiedDirectCompetitorSource(
  source: SourceItem
): boolean {
  return Boolean(
    source.is_direct_competitor &&
      source.public_display !== false &&
      !source.rejected &&
      !source.internal_only &&
      source.source_type &&
      ["competitor", "pricing_page"].includes(source.source_type) &&
      source.region_match === "local" &&
      source.same_or_close_use_case &&
      source.same_or_close_solution_category &&
      (source.matched_domain_terms?.length || 0) >= 2 &&
      (source.product_evidence_signals?.length || 0) >= 2
  );
}

export function getSourceEvidenceCategories(source: SourceItem): string[] {
  return uniqueStrings(
    (source.evidence_categories || [])
      .map((item) => String(item || "").trim())
      .filter(Boolean)
  );
}