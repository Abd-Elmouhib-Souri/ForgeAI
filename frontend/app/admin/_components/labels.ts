// Sprint 7.3: one place for the French labels of the codes the admin API
// returns (roles, analysis statuses). Unknown codes are shown as they are,
// never hidden.

export const ROLE_LABELS: Record<string, string> = {
  admin: "Administrateur",
  entrepreneur: "Entrepreneur",
  student: "Étudiant",
  consultant: "Consultant",
};

export const ANALYSIS_STATUS_LABELS: Record<string, string> = {
  not_started: "Non lancée",
  queued: "En file d'attente",
  running: "En cours",
  needs_clarification: "Précisions requises",
  completed: "Terminée",
  failed: "Échouée",
};

export function roleLabel(role: string | null | undefined) {
  if (!role) return "—";
  return ROLE_LABELS[role] ?? role;
}

export function analysisStatusLabel(status: string | null | undefined) {
  if (!status) return "—";
  return ANALYSIS_STATUS_LABELS[status] ?? status;
}

// Sprint 7.6: post-analysis pipeline (backend: post_analysis_pipeline.py).
export const PIPELINE_STAGE_LABELS: Record<string, string> = {
  project_manager: "Plan projet",
  solution_architecture: "Architecture de la solution",
};

export const PIPELINE_STATUS_LABELS: Record<string, string> = {
  not_started: "Non lancée",
  pending: "En attente",
  running: "En cours",
  completed: "Terminée",
  degraded: "Version de secours",
  waiting_retry: "Nouvel essai programmé",
  failed: "Échouée",
};

export function pipelineStageLabel(stage: string) {
  return PIPELINE_STAGE_LABELS[stage] ?? stage;
}

export function pipelineStatusLabel(status: string | null | undefined) {
  if (!status) return "—";
  return PIPELINE_STATUS_LABELS[status] ?? status;
}
