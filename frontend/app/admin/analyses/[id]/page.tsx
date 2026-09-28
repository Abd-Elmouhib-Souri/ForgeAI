"use client";

import type { ReactNode } from "react";
import { useState } from "react";
import { useParams } from "next/navigation";
import { isAdminActionCancelled } from "@/lib/admin-api";
import AdminPageHeader from "@/app/admin/_components/AdminPageHeader";
import {
  analysisStatusLabel,
  pipelineStageLabel,
  pipelineStatusLabel,
} from "@/app/admin/_components/labels";
import { canRelaunch, relaunchAnalysis } from "@/app/admin/_components/relaunch";
import { useAdminResource } from "@/app/admin/_components/useAdminResource";

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
  diagnostics: {
    project_id: number;
    analysis_status: string;
    analysis_step: string | null;
    analysis_progress: number | null;
    analysis_error: string | null;
    analysis_started_at: string | null;
    analysis_completed_at: string | null;
    startup_evaluator: {
      completed_steps: string[];
      failed_steps: string[];
      current_step: string | null;
      progress: number | null;
      error: string | null;
    };
    debate_room: {
      completed: boolean | null;
      completed_steps: string[];
      failed_steps: string[];
      current_step: string | null;
      progress: number | null;
      error: string | null;
    };
    forgecrawler: {
      status: string | null;
      confidence_level: string | null;
      sources_count: number;
      local_competitors_count: number | null;
      market_sources_count: number | null;
    };
    technical: {
      errors_count: number;
      queries_count: number;
      errors: string[];
      queries: string[];
    };
  };
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

export default function AdminAnalysisDetailPage() {
  const params = useParams();

  const projectId = params.id as string;

  const resource = useAdminResource<AdminAnalysisDetail>(`/admin/analyses/${projectId}`);
  const detail = resource.data;
  const isLoading = !resource.data && !resource.error;
  const [message, setMessage] = useState("");
  const [actionError, setActionError] = useState("");
  const [isRelaunching, setIsRelaunching] = useState(false);
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

  return (
    <div>
      <AdminPageHeader
        title="Diagnostic d'analyse IA"
        backHref="/admin/analyses"
        backLabel="Analyses IA"
        actions={
          detail && canRelaunch(detail.project.analysis_status, detail.analysis_stalled) ? (
            <button
              type="button"
              onClick={relaunch}
              disabled={isRelaunching}
              className="rounded-lg bg-amber-500 px-4 py-2 font-semibold text-slate-950 transition hover:bg-amber-400 disabled:opacity-60"
            >
              {isRelaunching ? "Relance..." : "Relancer l'analyse"}
            </button>
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

        {detail && (
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

            {/* Sprint 7.6: post-analysis pipeline, as computed by the backend. */}
            <section className="rounded-2xl border border-white/10 bg-white/5 p-6">
              <h2 className="text-lg font-semibold">Pipeline post-analyse</h2>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {Object.entries(detail.pipeline.stages).map(([stage, state]) => (
                  <div key={stage} className="rounded-xl border border-white/10 bg-white/5 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-medium">{pipelineStageLabel(stage)}</p>
                      <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/80">
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
            </section>
            <section className="rounded-2xl border border-white/10 bg-white/5 p-6">
              <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div>
                  <p className="text-sm text-red-300">
                    Projet #{detail.project.id}
                  </p>

                  <h2 className="mt-1 text-2xl font-bold">
                    {detail.project.title}
                  </h2>

                  <p className="mt-2 text-sm text-white/50">
                    Propriétaire : {detail.project.owner_name || "-"} ·{" "}
                    {detail.project.owner_email || "-"}
                  </p>
                </div>

                <div className="flex flex-wrap gap-2">
                  <Badge label={analysisStatusLabel(detail.project.analysis_status)} />
                  <Badge label={`${detail.project.analysis_progress ?? 0}%`} />
                  <Badge label={String(detail.project.startup_score ?? "-")} />
                </div>
              </div>

              <div className="mt-5 grid gap-3 md:grid-cols-4">
                <Info label="Secteur" value={detail.project.industry || "-"} />
                <Info label="Région" value={detail.project.market_region || "-"} />
                <Info
                  label="Début"
                  value={formatDate(detail.project.analysis_started_at)}
                />
                <Info
                  label="Fin"
                  value={formatDate(detail.project.analysis_completed_at)}
                />
              </div>

              {detail.project.analysis_error && (
                <div className="mt-5 rounded-xl border border-red-400/30 bg-red-500/10 p-4">
                  <p className="text-sm font-semibold text-red-200">
                    analysis_error brut
                  </p>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-red-100">
                    {detail.project.analysis_error}
                  </p>
                </div>
              )}
            </section>

            <section className="grid gap-6 lg:grid-cols-3">
              <Panel title="Startup Evaluator">
                <Info
                  label="Progression"
                  value={`${detail.diagnostics.startup_evaluator.progress ?? "-"}%`}
                />
                <Info
                  label="Étape courante"
                  value={detail.diagnostics.startup_evaluator.current_step || "-"}
                />
                <Info
                  label="Erreur"
                  value={detail.diagnostics.startup_evaluator.error || "Aucune"}
                />

                <ListBlock
                  title="Étapes réussies"
                  items={detail.diagnostics.startup_evaluator.completed_steps}
                />

                <ListBlock
                  title="Étapes échouées"
                  items={detail.diagnostics.startup_evaluator.failed_steps}
                  danger
                />
              </Panel>

              <Panel title="Debate Room">
                <Info
                  label="Terminé"
                  value={
                    detail.diagnostics.debate_room.completed === true
                      ? "Oui"
                      : detail.diagnostics.debate_room.completed === false
                        ? "Non"
                        : "-"
                  }
                />
                <Info
                  label="Progression"
                  value={`${detail.diagnostics.debate_room.progress ?? "-"}%`}
                />
                <Info
                  label="Étape courante"
                  value={detail.diagnostics.debate_room.current_step || "-"}
                />
                <Info
                  label="Erreur"
                  value={detail.diagnostics.debate_room.error || "Aucune"}
                />

                <ListBlock
                  title="Étapes réussies"
                  items={detail.diagnostics.debate_room.completed_steps}
                />

                <ListBlock
                  title="Étapes échouées"
                  items={detail.diagnostics.debate_room.failed_steps}
                  danger
                />
              </Panel>

              <Panel title="ForgeCrawler / Sources">
                <Info
                  label="Statut"
                  value={detail.diagnostics.forgecrawler.status || "-"}
                />
                <Info
                  label="Confidence"
                  value={detail.diagnostics.forgecrawler.confidence_level || "-"}
                />
                <Info
                  label="Sources"
                  value={String(detail.diagnostics.forgecrawler.sources_count)}
                />
                <Info
                  label="Concurrents locaux"
                  value={String(
                    detail.diagnostics.forgecrawler.local_competitors_count ?? "-"
                  )}
                />
                <Info
                  label="Sources marché"
                  value={String(
                    detail.diagnostics.forgecrawler.market_sources_count ?? "-"
                  )}
                />
              </Panel>
            </section>

            <section className="grid gap-6 lg:grid-cols-2">
              <Panel
                title={`Erreurs techniques (${detail.diagnostics.technical.errors_count})`}
              >
                <ListBlock
                  title="Erreurs internes détectées"
                  items={detail.diagnostics.technical.errors}
                  danger
                />
              </Panel>

              <Panel
                title={`Requêtes / queries (${detail.diagnostics.technical.queries_count})`}
              >
                <ListBlock
                  title="Requêtes utilisées"
                  items={detail.diagnostics.technical.queries}
                />
              </Panel>
            </section>

            <Panel title="JSON brut complet — analysis_data">
              <JsonBlock value={detail.analysis_data} />
            </Panel>
          </div>
        )}
      </section>
    </div>
  );
}

function Panel({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
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
      <p className="mt-1 break-words text-sm font-medium text-white/80">
        {value || "-"}
      </p>
    </div>
  );
}

function Badge({ label }: { label: string }) {
  return (
    <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/70">
      {label}
    </span>
  );
}

function ListBlock({
  title,
  items,
  danger = false,
}: {
  title: string;
  items: string[];
  danger?: boolean;
}) {
  return (
    <div className="rounded-lg border border-white/10 bg-slate-950/40 p-4">
      <p
        className={
          danger
            ? "text-sm font-semibold text-red-200"
            : "text-sm font-semibold text-white"
        }
      >
        {title}
      </p>

      {items.length > 0 ? (
        <ul className="mt-3 max-h-72 list-disc space-y-2 overflow-auto pl-5 text-sm leading-6 text-white/70">
          {items.map((item, index) => (
            <li key={`${item}-${index}`} className="break-words">
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-white/40">Aucun élément.</p>
      )}
    </div>
  );
}

function JsonBlock({ value }: { value: unknown }) {
  return (
    <pre className="max-h-[700px] overflow-auto rounded-xl border border-white/10 bg-slate-950 p-4 text-xs leading-5 text-emerald-100">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
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