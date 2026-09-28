import { adminFetch } from "@/lib/admin-api";

// Sprint 7.6: relaunch of an analysis from the console (list and detail).
// The admin API only QUEUES the run (the public API executes it) and is the
// authority: it answers 409 for a live run or a never-started project. This
// helper only decides whether to SHOW the button, from the backend's flag.

export function canRelaunch(status: string | null | undefined, stalled: boolean | null | undefined) {
  if (!status || status === "not_started") return false;
  if (status === "queued" || status === "running") return Boolean(stalled);
  return true;
}

export async function relaunchAnalysis(projectId: number, title: string): Promise<string> {
  const data = await adminFetch(`/admin/analyses/${projectId}/relaunch`, {
    method: "POST",
    confirm: `Relancer l'analyse du projet « ${title} » ?\nLe résultat actuel sera remplacé par la nouvelle analyse.`,
  });
  return data?.message || "Relance en file d'attente.";
}
