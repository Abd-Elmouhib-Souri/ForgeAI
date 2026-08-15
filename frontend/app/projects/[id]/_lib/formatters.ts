import type { AnalysisStatus, TextList } from "../_types/project-detail.types";

export function getErrorMessage(error: unknown, fallback: string): string {
  if (
    typeof error === "object" &&
    error !== null &&
    "response" in error &&
    typeof (error as { response?: unknown }).response === "object" &&
    (error as { response?: unknown }).response !== null
  ) {
    const response = (error as { response?: { data?: { detail?: string } } })
      .response;

    if (response?.data?.detail) {
      return response.data.detail;
    }
  }

  return fallback;
}

export function formatDate(value?: string | null, locale = "fr-FR"): string {
  if (!value) return "—";

  try {
    return new Date(value).toLocaleString(locale);
  } catch {
    return "—";
  }
}

export function formatScore(value?: number | null): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  return `${value.toFixed(2)}/10`;
}

export function clampProgress(value?: number | null): number {
  if (typeof value !== "number" || Number.isNaN(value)) return 0;
  return Math.max(0, Math.min(100, Math.round(value)));
}

export function normalizeList(value?: TextList): string[] {
  if (!value) return [];
  if (Array.isArray(value)) return value.filter(Boolean);
  return [value].filter(Boolean);
}

export function uniqueStrings(values: string[]): string[] {
  const result: string[] = [];
  const seen = new Set<string>();

  for (const value of values) {
    const clean = String(value || "").trim();
    if (!clean) continue;

    const key = clean.toLowerCase();

    if (!seen.has(key)) {
      seen.add(key);
      result.push(clean);
    }
  }

  return result;
}

export function shortenText(value: string, maxLength: number): string {
  if (value.length <= maxLength) return value;

  const sliced = value.slice(0, maxLength);
  const lastSpace = sliced.lastIndexOf(" ");

  if (lastSpace > 120) {
    return `${sliced.slice(0, lastSpace)}...`;
  }

  return `${sliced}...`;
}

export function statusLabel(status?: AnalysisStatus | null): string {
  switch (status) {
    case "not_started":
      return "Non lancée";
    case "pending":
      return "En attente";
    case "running":
      return "En cours";
    case "completed":
      return "Terminée";
    case "failed":
      return "Échouée";
    default:
      return status || "Non lancée";
  }
}

export function statusLabelEn(status?: AnalysisStatus | null): string {
  switch (status) {
    case "not_started":
      return "Not started";
    case "pending":
      return "Pending";
    case "running":
      return "Running";
    case "completed":
      return "Completed";
    case "failed":
      return "Failed";
    default:
      return status || "Not started";
  }
}

export function confidenceLabel(value?: string): string {
  switch (value) {
    case "high":
      return "Élevée";
    case "medium":
      return "Moyenne";
    case "low":
      return "Faible";
    default:
      return value || "—";
  }
}

export function confidenceLabelEn(value?: string): string {
  switch (value) {
    case "high":
      return "High";
    case "medium":
      return "Medium";
    case "low":
      return "Low";
    default:
      return value || "—";
  }
}

export function riskLevelLabel(value?: string): string {
  switch (value) {
    case "low":
      return "Faible";
    case "medium":
      return "Moyen";
    case "high":
      return "Élevé";
    default:
      return value || "—";
  }
}

export function riskLevelLabelEn(value?: string): string {
  switch (value) {
    case "low":
      return "Low";
    case "medium":
      return "Medium";
    case "high":
      return "High";
    default:
      return value || "—";
  }
}

export function difficultyLabel(value?: string | null): string {
  switch (value) {
    case "low":
      return "Faible";
    case "medium":
      return "Moyenne";
    case "high":
      return "Élevée";
    default:
      return value || "—";
  }
}

export function verdictLabel(value?: string): string {
  const normalized = String(value || "")
    .trim()
    .toLowerCase()
    .replaceAll("-", "_")
    .replaceAll(" ", "_");

  if (["go", "poursuivre", "continue", "continued"].includes(normalized)) {
    return "POURSUIVRE";
  }
  if (["conditional_go", "continue_with_conditions", "poursuivre_sous_conditions"].includes(normalized)) {
    return "POURSUIVRE SOUS CONDITIONS";
  }
  if (["pivot", "pivoter"].includes(normalized)) {
    return "PIVOTER";
  }
  if (["no_go", "stop", "abandonner", "abandon"].includes(normalized)) {
    return "NE PAS POURSUIVRE";
  }
  if (["insufficient_evidence", "preuves_insuffisantes"].includes(normalized)) {
    return "PREUVES INSUFFISANTES";
  }
  return value || "—";
}

export function sourceTypeLabel(value?: string): string {
  switch (value) {
    case "competitor":
      return "Solution comparable";
    case "pricing_page":
      return "Source commerciale";
    case "adjacent_solution":
      return "Solution proche";
    case "directory":
      return "Annuaire professionnel";
    case "market_article":
      return "Source marché";
    case "regulation":
      return "Source réglementaire";
    case "irrelevant":
      return "Source non retenue";
    default:
      return value || "Source externe";
  }
}

export function regionLabel(value?: string): string {
  switch (value) {
    case "local":
      return "Local";
    case "regional":
      return "Régional";
    case "international":
      return "International";
    case "unknown":
      return "Non déterminé";
    default:
      return value || "—";
  }
}

export function isGlobalRegion(value?: string | null): boolean {
  const region = String(value || "").toLowerCase();

  return (
    region.includes("global") ||
    region.includes("international") ||
    region.includes("world")
  );
}