/*
 * Post-analysis pipeline (Plan produit -> Architecture technique).
 *
 * Types mirror backend/app/services/post_analysis_pipeline.py and the
 * stable failure codes of backend/app/services/llm_failure_classifier.py.
 * The backend owns every decision; this module only formats it for humans.
 */

export type PipelineStageStatus =
  | "not_started"
  | "pending"
  | "running"
  | "completed"
  | "degraded"
  | "waiting_retry"
  | "failed";

export type PipelineStageKey = "project_manager" | "solution_architecture";

export type PipelineStage = {
  status: PipelineStageStatus;
  attempts: number;
  error_code: string | null;
  misconfigured_models: string[];
  next_retry_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  updated_at: string | null;
};

export type PipelineState = {
  version: number;
  analysis_status: string | null;
  status: PipelineStageStatus;
  stages: Record<PipelineStageKey, PipelineStage>;
  max_automatic_attempts: number;
};

type Lang = "fr" | "en";

const lang = (language: string): Lang => (language === "en" ? "en" : "fr");

// Statuses where the backend is still working or will retry by itself.
export function isPipelineActive(status: PipelineStageStatus | undefined): boolean {
  return status === "pending" || status === "running";
}

// A section may be displayed once its artifact exists (final or provisional).
export function isStageDisplayable(stage: PipelineStage | undefined): boolean {
  return stage?.status === "completed" || stage?.status === "degraded";
}

export function stageStatusLabel(status: PipelineStageStatus, language: string): string {
  const labels: Record<Lang, Record<PipelineStageStatus, string>> = {
    fr: {
      not_started: "Non lancé",
      pending: "En attente",
      running: "En cours…",
      completed: "Terminé",
      degraded: "Provisoire",
      waiting_retry: "Nouvel essai prévu",
      failed: "Échec",
    },
    en: {
      not_started: "Not started",
      pending: "Queued",
      running: "Running…",
      completed: "Done",
      degraded: "Provisional",
      waiting_retry: "Retry scheduled",
      failed: "Failed",
    },
  };
  return labels[lang(language)][status] ?? status;
}

// Human explanation of a stable backend failure code (never raw errors).
export function failureReasonMessage(
  code: string | null | undefined,
  language: string,
): string | null {
  if (!code) return null;
  const messages: Record<Lang, Record<string, string>> = {
    fr: {
      llm_quota_or_unavailable:
        "Les fournisseurs IA ont atteint leur quota ou sont momentanément indisponibles.",
      llm_configuration_error:
        "Aucun modèle IA configuré ne répond (modèle introuvable ou clé invalide). La configuration du serveur doit être corrigée ; la génération reprendra au redémarrage du backend.",
      invalid_model_output:
        "L'IA a produit une réponse invalide ; un nouvel essai est nécessaire.",
      context_invalid:
        "Le contexte du projet est incomplet ou invalide : relancez l'analyse.",
      ai_fallback_used:
        "Plan provisoire construit sans IA (règles déterministes), en attendant que l'IA soit disponible.",
      unexpected_error: "Erreur inattendue lors de la génération.",
    },
    en: {
      llm_quota_or_unavailable:
        "AI providers reached their quota or are temporarily unavailable.",
      llm_configuration_error:
        "No configured AI model answers (model not found or invalid key). The server configuration must be fixed; generation resumes when the backend restarts.",
      invalid_model_output: "The AI returned an invalid answer; another attempt is needed.",
      context_invalid: "The project context is incomplete or invalid: re-run the analysis.",
      ai_fallback_used:
        "Provisional plan built without AI (deterministic rules) until the AI is available.",
      unexpected_error: "Unexpected error during generation.",
    },
  };
  return messages[lang(language)][code] ?? messages[lang(language)].unexpected_error;
}

export function misconfiguredModelsMessage(models: string[] | undefined, language: string): string | null {
  if (!models || models.length === 0) return null;
  return lang(language) === "en"
    ? `Model not found on the server: ${models.join(", ")} — update the backend .env.`
    : `Modèle introuvable côté serveur : ${models.join(", ")} — mettez à jour le .env du backend.`;
}

export function nextRetryMessage(iso: string | null | undefined, language: string, now: number = Date.now()): string | null {
  if (!iso) return null;
  const at = new Date(iso);
  if (Number.isNaN(at.getTime())) return null;
  const minutes = Math.max(0, Math.round((at.getTime() - now) / 60000));
  const time = at.toLocaleTimeString(lang(language) === "en" ? "en-GB" : "fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
  });
  if (lang(language) === "en") {
    return minutes <= 0 ? `Automatic retry imminent (${time}).` : `Automatic retry at ${time} (in ${minutes} min).`;
  }
  return minutes <= 0
    ? `Reprise automatique imminente (${time}).`
    : `Reprise automatique à ${time} (dans ${minutes} min).`;
}
