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
