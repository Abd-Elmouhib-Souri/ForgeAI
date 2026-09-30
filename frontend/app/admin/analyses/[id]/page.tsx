"use client";

import type { ReactNode } from "react";
import { useState } from "react";
import { useParams } from "next/navigation";
import { RotateCcw } from "lucide-react";
import { isAdminActionCancelled } from "@/lib/admin-api";
import AdminPageHeader from "@/app/admin/_components/AdminPageHeader";
import { Button } from "@/app/admin/_components/Button";
import {
  analysisStatusLabel,
  pipelineStageLabel,
  pipelineStatusLabel,
} from "@/app/admin/_components/labels";
import { canRelaunch, relaunchAnalysis } from "@/app/admin/_components/relaunch";
import { useAdminResource } from "@/app/admin/_components/useAdminResource";

// Sprint 7.8: everything below is decided by the backend (analysis_diagnostics);
// the page only picks a colour for each status it receives.
type StepStatus = "completed" | "degraded" | "failed" | "running" | "not_run";
type SummaryLevel = "ok" | "warning" | "error" | "running" | "not_started";

type Diagnostics = {
  summary: {
    level: SummaryLevel;
    headline: string;
    steps_done: number;
    steps_total: number;
    duration_seconds: number | null;
  };
  steps: {
    key: string;
    label: string;
    status: StepStatus;
    status_label: string;
    notes: string[];
    error: string | null;
  }[];
  sources: {
    status_label: string;
    confidence_label: string;
    total: number;
    local: number | null;
    regional: number | null;
    international: number | null;
    local_competitors: number | null;
    market: number | null;
    rejected: number | null;
    removed_by_safety_filter: number | null;
    no_relevant_source: boolean;
  };
  evidence: {
    overall_label: string;
    verdict_label: string;
    score: number | null;
    claims_total: number | null;
    claims_sourced: number | null;
    claims_estimated: number | null;
  };
  errors: { where: string; message: string }[];
  queries: { total: number; unique: string[] };
  not_recorded: string[];
};

type AdminAnalysisDetail = {
  project: {
    id: number;
    title: string;
    description: string;
    industry: string;
    market_region: string;
    status: string;
    startup_score: number | null;
    analysis_status: string;
    analysis_step: string | null;
    analysis_progress: number | null;
    analysis_error: string | null;
    analysis_started_at: string | null;
    analysis_completed_at: string | null;
    owner_email: string | null;
    owner_name: string | null;
    created_at: string | null;
    updated_at: string | null;
  };
  diagnostics: Diagnostics;
  analysis_data: unknown;
  // Sprint 7.6: decided by the backend.
  analysis_stalled: boolean;
  pipeline: {
    status: string;
    stages: Record<
      string,
      { status: string; attempts?: number; error_code?: string | null; next_retry_at?: string | null; updated_at?: string | null }
    >;
  };
};

// One colour per status received from the backend (display only).
const STEP_STYLES: Record<StepStatus, string> = {
  completed: "border-emerald-400/30 bg-emerald-500/10 text-emerald-200",
  degraded: "border-amber-400/40 bg-amber-500/15 text-amber-200",
  failed: "border-red-400/40 bg-red-500/15 text-red-200",
  running: "border-sky-400/40 bg-sky-500/15 text-sky-200",
  not_run: "border-white/10 bg-white/5 text-white/50",
};

const SUMMARY_STYLES: Record<SummaryLevel, string> = {
  ok: "border-emerald-400/30 bg-emerald-500/10 text-emerald-100",
  warning: "border-amber-400/30 bg-amber-500/10 text-amber-100",
  error: "border-red-400/30 bg-red-500/10 text-red-100",
  running: "border-sky-400/30 bg-sky-500/10 text-sky-100",
  not_started: "border-white/10 bg-white/5 text-white/70",
};

export default function AdminAnalysisDetailPage() {
  const params = useParams();

  const projectId = params.id as string;

  const resource = useAdminResource<AdminAnalysisDetail>(`/admin/analyses/${projectId}`);
  const detail = resource.data;
  const isLoading = !resource.data && !resource.error;
  const [message, setMessage] = useState("");
  const [actionError, setActionError] = useState("");
  const [isRelaunching, setIsRelaunching] = useState(false);
  // The raw analysis_data can weigh more than 1 MB: serialise it only once opened.
  const [showRaw, setShowRaw] = useState(false);
  const error = actionError || resource.error;

  async function relaunch() {
    if (!detail) return;
    try {
      setIsRelaunching(true);
      setMessage("");
      setActionError("");
      setMessage(await relaunchAnalysis(detail.project.id, detail.project.title));
      resource.reload();
    } catch (err) {
      if (isAdminActionCancelled(err)) return;
      setActionError(err instanceof Error ? err.message : "Relance impossible.");
    } finally {
      setIsRelaunching(false);
    }
  }

  const diagnostics = detail?.diagnostics;

  return (
    <div>
      <AdminPageHeader
        title="Diagnostic d'analyse IA"
        backHref="/admin/analyses"
        backLabel="Analyses IA"
        actions={
          detail && canRelaunch(detail.project.analysis_status, detail.analysis_stalled) ? (
            <Button variant="warning" icon={RotateCcw} loading={isRelaunching} onClick={relaunch}>
              {isRelaunching ? "Relance..." : "Relancer l'analyse"}
            </Button>
          ) : undefined
        }
      />

      <section className="mx-auto max-w-7xl px-6 py-8">
        {isLoading && (
          <div className="rounded-xl border border-white/10 bg-white/5 p-6 text-white/70">
            Chargement du diagnostic...
          </div>
        )}

        {error && (
          <div className="rounded-xl border border-red-400/30 bg-red-500/10 p-6 text-red-200">
            {error}
          </div>
        )}

        {message && (
          <div className="mb-6 rounded-xl border border-emerald-400/30 bg-emerald-500/10 p-4 text-sm text-emerald-200">
            {message}
          </div>
        )}

        {detail && diagnostics && (
          <div className="space-y-6">
            {detail.analysis_stalled && (
              <div className="rounded-2xl border border-amber-400/30 bg-amber-500/10 p-5 text-sm text-amber-100">
                <p className="font-semibold">Analyse bloquée</p>
                <p className="mt-1 text-amber-100/80">
                  Aucun signe de vie depuis plus de 20 minutes (redémarrage ou panne du serveur). Elle ne
                  reprendra pas seule : relancez-la.
                </p>
              </div>
            )}

            {/* Project identity */}
            <section className="rounded-2xl border border-white/10 bg-white/5 p-6">
              <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div>
                  <p className="text-sm text-red-300">Projet #{detail.project.id}</p>
                  <h2 className="mt-1 text-2xl font-bold">{detail.project.title}</h2>
                  <p className="mt-2 text-sm text-white/50">
                    Propriétaire : {detail.project.owner_name || "-"} · {detail.project.owner_email || "-"}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge label={analysisStatusLabel(detail.project.analysis_status)} />
                  <Badge label={`${detail.project.analysis_progress ?? 0}%`} />
                </div>
              </div>

              <div className="mt-5 grid gap-3 md:grid-cols-4">
                <Info label="Secteur" value={detail.project.industry || "-"} />
                <Info label="Région" value={detail.project.market_region || "-"} />
                <Info label="Début" value={formatDate(detail.project.analysis_started_at)} />
                <Info label="Fin" value={formatDate(detail.project.analysis_completed_at)} />
              </div>
            </section>

            {/* One-line verdict of the run */}
            <section className={`rounded-2xl border p-6 ${SUMMARY_STYLES[diagnostics.summary.level]}`}>
              <p className="text-xl font-semibold">{diagnostics.summary.headline}</p>
              <p className="mt-2 text-sm opacity-80">
                {diagnostics.summary.steps_done} étape(s) sur {diagnostics.summary.steps_total} ·
                durée totale : {formatDuration(diagnostics.summary.duration_seconds)}
              </p>
              {detail.project.analysis_error && (
                <p className="mt-3 whitespace-pre-wrap text-sm">
                  Message d’erreur enregistré : {detail.project.analysis_error}
                </p>
              )}
            </section>

            {/* Steps of the analysis, in pipeline order */}
            <Panel title="Étapes de l'analyse">
              <ol className="space-y-2">
                {diagnostics.steps.map((step, index) => (
                  <li
                    key={step.key}
                    className="flex flex-col gap-2 rounded-xl border border-white/10 bg-slate-950/40 p-4 md:flex-row md:items-start md:justify-between"
                  >
                    <div>
                      <p className="font-medium">
                        <span className="mr-2 text-white/40">{index + 1}.</span>
                        {step.label}
                      </p>
                      {step.notes.map((note) => (
                        <p key={note} className="mt-1 text-sm text-amber-200">{note}</p>
                      ))}
                      {step.error && (
                        <p className="mt-1 break-words text-sm text-red-200">Erreur : {step.error}</p>
                      )}
                    </div>
                    <span
                      className={`self-start whitespace-nowrap rounded-full border px-3 py-1 text-xs ${STEP_STYLES[step.status]}`}
                    >
                      {step.status_label}
                    </span>
                  </li>
                ))}
              </ol>
            </Panel>

            <section className="grid gap-6 lg:grid-cols-2">
              <Panel title="Sources">
                {diagnostics.sources.no_relevant_source && (
                  <p className="text-sm text-amber-200">Aucune source pertinente vérifiée n’a été trouvée.</p>
                )}
                <div className="grid gap-3 sm:grid-cols-2">
                  <Info label="Recherche" value={diagnostics.sources.status_label} />
                  <Info label="Confiance des sources" value={diagnostics.sources.confidence_label} />
                  <Info label="Sources retenues" value={count(diagnostics.sources.total)} />
                  <Info
                    label="Locales / régionales / internationales"
                    value={`${count(diagnostics.sources.local)} / ${count(diagnostics.sources.regional)} / ${count(diagnostics.sources.international)}`}
                  />
                  <Info label="Concurrents locaux" value={count(diagnostics.sources.local_competitors)} />
                  <Info label="Sources marché" value={count(diagnostics.sources.market)} />
                  <Info label="Sources rejetées" value={count(diagnostics.sources.rejected)} />
                  <Info
                    label="Retirées par le filtre de sécurité"
                    value={count(diagnostics.sources.removed_by_safety_filter)}
                  />
                </div>
              </Panel>

              <Panel title="Preuves et verdict">
                <div className="grid gap-3 sm:grid-cols-2">
                  <Info label="Verdict" value={diagnostics.evidence.verdict_label} />
                  <Info
                    label="Score"
                    value={diagnostics.evidence.score === null ? "-" : `${diagnostics.evidence.score} / 10`}
                  />
                  <Info label="Confiance globale des preuves" value={diagnostics.evidence.overall_label} />
                  <Info label="Affirmations vérifiées" value={count(diagnostics.evidence.claims_total)} />
                  <Info label="dont sourcées" value={count(diagnostics.evidence.claims_sourced)} />
                  <Info label="dont estimées" value={count(diagnostics.evidence.claims_estimated)} />
                </div>
              </Panel>
            </section>

            <section className="grid gap-6 lg:grid-cols-2">
              <Panel title={`Erreurs techniques (${diagnostics.errors.length})`}>
                {diagnostics.errors.length > 0 ? (
                  <ul className="max-h-72 space-y-2 overflow-auto text-sm">
                    {diagnostics.errors.map((item, index) => (
                      <li key={`${item.where}-${index}`} className="break-words text-red-100">
                        <span className="font-semibold text-red-200">{item.where} :</span> {item.message}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-white/50">Aucune erreur enregistrée.</p>
                )}
              </Panel>

              <Panel
                title={`Requêtes de recherche (${diagnostics.queries.unique.length} distinctes sur ${diagnostics.queries.total})`}
              >
                {diagnostics.queries.unique.length > 0 ? (
                  <ul className="max-h-72 list-disc space-y-1 overflow-auto pl-5 text-sm text-white/70">
                    {diagnostics.queries.unique.map((query) => (
                      <li key={query} className="break-words">{query}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-white/50">Aucune requête enregistrée.</p>
                )}
              </Panel>
            </section>

            {/* Sprint 7.6: post-analysis pipeline, as computed by the backend. */}
            <Panel title="Pipeline post-analyse">
              <div className="grid gap-3 md:grid-cols-2">
                {Object.entries(detail.pipeline.stages).map(([stage, state]) => (
                  <div key={stage} className="rounded-xl border border-white/10 bg-white/5 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-medium">{pipelineStageLabel(stage)}</p>
                      <span className="whitespace-nowrap rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/80">
                        {pipelineStatusLabel(state.status)}
                      </span>
                    </div>
                    <p className="mt-2 text-xs text-white/50">
                      Tentatives : {state.attempts ?? 0}
                      {state.error_code ? ` · code : ${state.error_code}` : ""}
                      {state.next_retry_at ? ` · prochain essai : ${formatDate(state.next_retry_at)}` : ""}
                    </p>
                  </div>
                ))}
              </div>
            </Panel>

            {/* Honest about what the analysis does not keep. */}
            {diagnostics.not_recorded.length > 0 && (
              <p className="text-sm text-white/50">
                Non enregistré par l’analyse : {diagnostics.not_recorded.join(" · ")}.
              </p>
            )}

            <details
              className="rounded-2xl border border-white/10 bg-white/5 p-6"
              onToggle={(event) => setShowRaw(event.currentTarget.open)}
            >
              <summary className="cursor-pointer text-lg font-semibold">Données brutes (JSON)</summary>
              <div className="mt-4">{showRaw ? <JsonBlock value={detail.analysis_data} /> : null}</div>
            </details>
          </div>
        )}
      </section>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
      <h3 className="text-lg font-semibold">{title}</h3>
      <div className="mt-4 space-y-4">{children}</div>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-slate-950/40 px-4 py-3">
      <p className="text-xs text-white/40">{label}</p>
      <p className="mt-1 break-words text-sm font-medium text-white/80">{value || "-"}</p>
    </div>
  );
}

function Badge({ label }: { label: string }) {
  return (
    <span className="whitespace-nowrap rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/70">
      {label}
    </span>
  );
}

function JsonBlock({ value }: { value: unknown }) {
  return (
    <pre className="max-h-[700px] overflow-auto rounded-xl border border-white/10 bg-slate-950 p-4 text-xs leading-5 text-emerald-100">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

function count(value: number | null) {
  return value === null || value === undefined ? "-" : String(value);
}

// 432 -> "7 min 12 s"; null -> "-".
function formatDuration(seconds: number | null) {
  if (seconds === null || seconds === undefined) return "-";
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return minutes > 0 ? `${minutes} min ${rest} s` : `${rest} s`;
}

function formatDate(value?: string | null) {
  if (!value) return "-";

  try {
    return new Intl.DateTimeFormat("fr-FR", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return "-";
  }
}
