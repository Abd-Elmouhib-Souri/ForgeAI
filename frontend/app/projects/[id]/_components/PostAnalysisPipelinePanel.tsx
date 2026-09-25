"use client";

/*
 * Frise de progression du pipeline post-analyse :
 *   Analyse terminée -> Plan produit (Sprint 4) -> Architecture technique (Sprint 5)
 *
 * Remplace les boutons "Générer" affichés pendant l'analyse : le backend
 * enchaîne tout seul les deux étapes. Ce panneau interroge
 * GET /projects/{id}/pipeline, affiche l'état et la vraie cause d'un échec
 * (quota, modèle introuvable, réponse invalide) avec l'heure de reprise
 * automatique, et propose un seul bouton "Relancer" quand c'est utile.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import api from "@/lib/api";

import {
  failureReasonMessage,
  isPipelineActive,
  misconfiguredModelsMessage,
  nextRetryMessage,
  stageStatusLabel,
  type PipelineStage,
  type PipelineStageKey,
  type PipelineState,
  type PipelineStageStatus,
} from "../_lib/pipeline";

// Polling cadence: fast while the backend works, slow while it waits for a
// scheduled retry, none once every stage is settled.
const ACTIVE_POLL_MS = 4000;
const WAITING_POLL_MS = 30000;

const copy = {
  fr: {
    eyebrow: "Génération automatique",
    title: "Plan produit et architecture technique",
    intro:
      "ForgeAI enchaîne automatiquement le plan Agile puis l'architecture technique dès la fin de l'analyse. Aucune action n'est nécessaire.",
    stages: {
      project_manager: "Plan produit (backlog et sprints)",
      solution_architecture: "Architecture technique (stack, UML, base de données)",
    } as Record<PipelineStageKey, string>,
    attempt: (n: number, max: number) => `Essai ${n}/${max}`,
    retryNow: "Relancer maintenant",
    launch: "Générer le plan et l'architecture",
    launching: "Relance en cours…",
    loadError: "Impossible de lire l'état de la génération.",
    actionError: "La relance a échoué.",
  },
  en: {
    eyebrow: "Automatic generation",
    title: "Product plan and technical architecture",
    intro:
      "ForgeAI automatically builds the Agile plan, then the technical architecture, as soon as the analysis ends. No action is needed.",
    stages: {
      project_manager: "Product plan (backlog and sprints)",
      solution_architecture: "Technical architecture (stack, UML, database)",
    } as Record<PipelineStageKey, string>,
    attempt: (n: number, max: number) => `Attempt ${n}/${max}`,
    retryNow: "Retry now",
    launch: "Generate plan and architecture",
    launching: "Restarting…",
    loadError: "Unable to read the generation status.",
    actionError: "Retry failed.",
  },
};

const STAGE_ORDER: PipelineStageKey[] = ["project_manager", "solution_architecture"];

// Tailwind classes per status (same palette as the rest of the report).
const PILL: Record<PipelineStageStatus, string> = {
  not_started: "bg-slate-100 text-slate-600",
  pending: "bg-sky-100 text-sky-700",
  running: "bg-violet-100 text-violet-700",
  completed: "bg-emerald-100 text-emerald-700",
  degraded: "bg-amber-100 text-amber-800",
  waiting_retry: "bg-amber-100 text-amber-800",
  failed: "bg-red-100 text-red-700",
};

function pollDelay(state: PipelineState | null): number | null {
  if (!state) return null;
  if (isPipelineActive(state.status)) return ACTIVE_POLL_MS;
  const waiting = STAGE_ORDER.some((key) => {
    const stage = state.stages[key];
    return stage?.status === "waiting_retry" || (stage?.status === "degraded" && Boolean(stage.next_retry_at));
  });
  return waiting ? WAITING_POLL_MS : null;
}

function StageRow({
  stage,
  label,
  language,
  maxAttempts,
  t,
}: {
  stage: PipelineStage;
  label: string;
  language: string;
  maxAttempts: number;
  t: (typeof copy)["fr"];
}) {
  const reason = failureReasonMessage(stage.error_code, language);
  const models = misconfiguredModelsMessage(stage.misconfigured_models, language);
  const retry =
    stage.status === "waiting_retry" || stage.status === "degraded"
      ? nextRetryMessage(stage.next_retry_at, language)
      : null;
  const showDetails = stage.status !== "completed" && (reason || models || retry);

  return (
    <li className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm font-black text-slate-900">{label}</p>
        <div className="flex items-center gap-2">
          {stage.attempts > 1 && stage.status !== "completed" && (
            <span className="text-xs font-semibold text-slate-500">{t.attempt(stage.attempts, maxAttempts)}</span>
          )}
          <span className={`rounded-full px-3 py-1 text-xs font-black ${PILL[stage.status] ?? PILL.pending}`}>
            {stageStatusLabel(stage.status, language)}
          </span>
        </div>
      </div>
      {stage.status === "running" && (
        <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-violet-100">
          <div className="h-full w-1/3 animate-pulse rounded-full bg-violet-500" />
        </div>
      )}
      {showDetails && (
        <div className="mt-3 space-y-1 text-xs font-semibold leading-5 text-slate-600">
          {reason && <p>{reason}</p>}
          {models && <p className="text-red-700">{models}</p>}
          {retry && <p className="text-amber-800">{retry}</p>}
        </div>
      )}
    </li>
  );
}

export default function PostAnalysisPipelinePanel({
  projectId,
  language,
  onStateChange,
}: {
  projectId: string;
  language: string;
  onStateChange?: (state: PipelineState) => void;
}) {
  const t = language === "en" ? copy.en : copy.fr;

  const [state, setState] = useState<PipelineState | null>(null);
  const [error, setError] = useState("");
  const [working, setWorking] = useState(false);

  // Keep the latest callback without re-creating the polling loop.
  const onStateChangeRef = useRef(onStateChange);
  useEffect(() => {
    onStateChangeRef.current = onStateChange;
  }, [onStateChange]);

  const fetchState = useCallback(async (): Promise<PipelineState | null> => {
    try {
      const response = await api.get<PipelineState>(`/projects/${projectId}/pipeline`);
      setState(response.data);
      setError("");
      onStateChangeRef.current?.(response.data);
      return response.data;
    } catch {
      setError(t.loadError);
      return null;
    }
  }, [projectId, t.loadError]);

  // Recursive polling: each response decides the next delay (or stops).
  const [pollKey, setPollKey] = useState(0);
  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;

    const tick = async () => {
      const next = await fetchState();
      if (cancelled) return;
      const delay = pollDelay(next);
      if (delay !== null) timer = window.setTimeout(() => void tick(), delay);
    };

    timer = window.setTimeout(() => void tick(), 0);
    return () => {
      cancelled = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [fetchState, pollKey]);

  const relaunch = async () => {
    setWorking(true);
    setError("");
    try {
      await api.post(`/projects/${projectId}/pipeline/run`);
      setPollKey((key) => key + 1); // restart polling immediately
    } catch {
      setError(t.actionError);
    } finally {
      setWorking(false);
    }
  };

  if (!state) {
    return error ? (
      <p className="rounded-2xl border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">{error}</p>
    ) : null;
  }

  // Nothing to show once both stages are final: the sections take over.
  if (state.status === "completed") return null;

  const canRelaunch = ["failed", "waiting_retry", "degraded", "not_started"].includes(state.status);

  return (
    <section className="scroll-mt-28" id="post-analysis-pipeline">
      <div className="rounded-3xl border border-violet-100 bg-gradient-to-br from-violet-50 via-white to-sky-50 p-6 shadow-sm">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.18em] text-violet-600">{t.eyebrow}</p>
            <h2 className="mt-1 text-2xl font-black text-slate-950">{t.title}</h2>
            <p className="mt-2 max-w-3xl text-sm font-medium leading-6 text-slate-600">{t.intro}</p>
          </div>
          {canRelaunch && (
            <button
              type="button"
              disabled={working}
              onClick={() => void relaunch()}
              className="shrink-0 rounded-2xl bg-violet-700 px-5 py-3 text-sm font-black text-white transition hover:bg-violet-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {working ? t.launching : state.status === "not_started" ? t.launch : t.retryNow}
            </button>
          )}
        </div>

        <ol className="mt-5 grid gap-3">
          {STAGE_ORDER.map((key) => (
            <StageRow
              key={key}
              stage={state.stages[key]}
              label={t.stages[key]}
              language={language}
              maxAttempts={state.max_automatic_attempts}
              t={t}
            />
          ))}
        </ol>

        {error && (
          <p className="mt-4 rounded-2xl border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">{error}</p>
        )}
      </div>
    </section>
  );
}
