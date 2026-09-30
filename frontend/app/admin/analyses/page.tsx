"use client";

import { FormEvent, useState } from "react";
import { RotateCcw, Search, Stethoscope } from "lucide-react";
import { isAdminActionCancelled } from "@/lib/admin-api";
import { Button, ButtonLink } from "@/app/admin/_components/Button";
import FilterTabs from "@/app/admin/_components/FilterTabs";
import { canRelaunch, relaunchAnalysis } from "@/app/admin/_components/relaunch";
import { buildListQuery, type Page } from "@/app/admin/_components/listQuery";
import Pagination from "@/app/admin/_components/Pagination";
import type { AdminStats } from "@/app/admin/_components/stats";
import { useAdminResource } from "@/app/admin/_components/useAdminResource";
import AdminPageHeader from "@/app/admin/_components/AdminPageHeader";
import { analysisStatusLabel } from "@/app/admin/_components/labels";

type AdminAnalysis = {
  project_id: number;
  title: string;
  industry: string;
  market_region: string;
  startup_score: number | null;
  analysis_status: string;
  analysis_step: string;
  analysis_progress: number;
  analysis_error: string | null;
  analysis_started_at: string | null;
  analysis_completed_at: string | null;
  owner_email: string;
  owner_name: string;
  analysis_stalled: boolean; // decided by the backend (no sign of life)
};

const PAGE_SIZE = 25;

type StatusFilter = "all" | "completed" | "running" | "failed";

const STATUS_FILTERS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "Toutes" },
  { value: "completed", label: "Terminées" },
  { value: "running", label: "En cours" },
  { value: "failed", label: "Échouées" },
];

export default function AdminAnalysesPage() {
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [searchDraft, setSearchDraft] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  // Sprint 7.4: status filter, search and paging are done by the API.
  const list = useAdminResource<Page<AdminAnalysis>>(
    `/admin/analyses${buildListQuery({
      status: filter === "all" ? "" : filter,
      search,
      page,
      page_size: PAGE_SIZE,
    })}`,
  );
  const stats = useAdminResource<AdminStats>("/admin/stats");
  const analyses = list.data?.items ?? [];
  const [message, setMessage] = useState("");
  const [actionError, setActionError] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);

  async function relaunch(analysis: AdminAnalysis) {
    try {
      setBusyId(analysis.project_id);
      setMessage("");
      setActionError("");
      setMessage(await relaunchAnalysis(analysis.project_id, analysis.title));
      list.reload();
      stats.reload();
    } catch (err) {
      if (isAdminActionCancelled(err)) return;
      setActionError(err instanceof Error ? err.message : "Relance impossible.");
    } finally {
      setBusyId(null);
    }
  }

  function changeFilter(next: typeof filter) {
    setFilter(next);
    setPage(1);
  }

  function applySearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSearch(searchDraft);
    setPage(1);
  }

  return (
    <div>
      <AdminPageHeader title="Analyses IA" subtitle="Suivi des analyses lancées par les clients." />

      <section className="mx-auto max-w-7xl px-6 py-8">
        <div className="grid gap-4 md:grid-cols-4">
          {/* Counters of the whole platform, computed by the database. */}
          <Stat title="Total analyses" value={stats.data?.analyses.total ?? 0} />
          <Stat title="Terminées" value={stats.data?.analyses.completed ?? 0} />
          <Stat title="En cours" value={stats.data?.analyses.running ?? 0} />
          <Stat title="Échouées" value={stats.data?.analyses.failed ?? 0} />
        </div>

        <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-lg font-semibold">Liste des analyses</h2>
              <p className="mt-1 text-sm text-white/50">
                Suivi des analyses IA de tous les projets.
              </p>
            </div>

            <FilterTabs label="Filtrer par statut" options={STATUS_FILTERS} value={filter} onChange={changeFilter} />
          </div>

          <form onSubmit={applySearch} className="mt-5 flex flex-col gap-3 md:flex-row">
            <input
              value={searchDraft}
              onChange={(event) => setSearchDraft(event.target.value)}
              placeholder="Rechercher projet, secteur, région, propriétaire..."
              className="w-full rounded-lg border border-white/10 bg-slate-900 px-4 py-2.5 text-sm outline-none focus:border-red-300 md:max-w-md"
            />
            <Button type="submit" icon={Search}>
              Rechercher
            </Button>
          </form>

          {message && (
            <div className="mt-5 rounded-lg border border-emerald-400/30 bg-emerald-500/10 p-3 text-sm text-emerald-200">
              {message}
            </div>
          )}

          {(actionError || list.error) && (
            <div className="mt-5 rounded-lg border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-200">
              {actionError || list.error}
            </div>
          )}

          {!list.data ? (
            <div className="mt-6 rounded-xl border border-white/10 bg-white/5 p-6 text-white/60">
              Chargement des analyses...
            </div>
          ) : (
            <div className="mt-6 overflow-x-auto">
              <table className="w-full min-w-[960px] border-separate border-spacing-y-3 text-left text-sm">
                <thead className="text-white/50">
                  <tr>
                    <th className="px-3 py-2">Projet</th>
                    <th className="px-3 py-2">Secteur</th>
                    <th className="px-3 py-2">Région</th>
                    <th className="px-3 py-2">Score</th>
                    <th className="px-3 py-2">Statut</th>
                    <th className="px-3 py-2">Progression</th>
                    <th className="px-3 py-2">Propriétaire</th>
                    <th className="px-3 py-2">Fin</th>
                    <th className="px-3 py-2 text-right">Actions</th>
                  </tr>
                </thead>

                <tbody>
                  {analyses.map((analysis) => (
                    <tr key={analysis.project_id} className="bg-white/5">
                      <td className="rounded-l-xl px-3 py-4">
                        <div className="font-medium">{analysis.title}</div>
                        <div className="text-xs text-white/40">
                          {analysis.analysis_step || "-"}
                        </div>

                        {analysis.analysis_error && (
                          <div className="mt-2 rounded-lg border border-red-400/30 bg-red-500/10 p-2 text-xs text-red-200">
                            {analysis.analysis_error}
                          </div>
                        )}
                      </td>

                      <td className="px-3 py-4">{analysis.industry}</td>
                      <td className="px-3 py-4">{analysis.market_region}</td>
                      <td className="px-3 py-4 font-semibold">
                        {analysis.startup_score ?? "-"}
                      </td>

                      <td className="px-3 py-4">
                        <Badge status={analysis.analysis_status} />
                        {analysis.analysis_stalled && (
                          <span
                            title="Aucun signe de vie depuis plus de 20 minutes (redémarrage, panne)."
                            className="ml-2 rounded-full border border-amber-400/30 bg-amber-500/10 px-2 py-1 text-xs text-amber-200"
                          >
                            Bloquée
                          </span>
                        )}
                      </td>

                      <td className="px-3 py-4">
                        <div className="h-2 w-24 overflow-hidden rounded-full bg-white/10">
                          <div
                            className="h-full bg-cyan-400"
                            style={{
                              width: `${analysis.analysis_progress || 0}%`,
                            }}
                          />
                        </div>
                        <div className="mt-1 text-xs text-white/40">
                          {analysis.analysis_progress || 0}%
                        </div>
                      </td>

                      <td className="px-3 py-4">
                        <div>{analysis.owner_name}</div>
                        <div className="text-xs text-white/40">
                          {analysis.owner_email}
                        </div>
                      </td>

                      <td className="whitespace-nowrap px-3 py-4 text-white/60">
                        {analysis.analysis_completed_at
                          ? formatDate(analysis.analysis_completed_at)
                          : "-"}
                      </td>

                      <td className="rounded-r-xl px-3 py-4 text-right">
                        {/* Flex + gap, no wrap: both actions on one line, the column takes their width. */}
                        <div className="flex flex-nowrap items-center justify-end gap-2">
                        {canRelaunch(analysis.analysis_status, analysis.analysis_stalled) && (
                          <Button
                            variant="warning"
                            size="sm"
                            icon={RotateCcw}
                            loading={busyId === analysis.project_id}
                            onClick={() => relaunch(analysis)}
                          >
                            Relancer
                          </Button>
                        )}
                        <ButtonLink
                          href={`/admin/analyses/${analysis.project_id}`}
                          variant="info"
                          size="sm"
                          icon={Stethoscope}
                        >
                          Diagnostic
                        </ButtonLink>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {list.data.total === 0 && (
                <div className="rounded-xl border border-white/10 bg-white/5 p-6 text-center text-white/50">
                  Aucune analyse trouvée.
                </div>
              )}

              <Pagination
                page={page}
                pageSize={PAGE_SIZE}
                total={list.data.total}
                isLoading={list.isLoading}
                onPageChange={setPage}
              />
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function Stat({ title, value }: { title: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
      <p className="text-sm text-white/50">{title}</p>
      <p className="mt-2 text-3xl font-bold">{value}</p>
    </div>
  );
}

function Badge({ status }: { status: string }) {
  const className =
    status === "completed"
      ? "border-emerald-400/30 bg-emerald-500/10 text-emerald-200"
      : status === "failed"
        ? "border-red-400/30 bg-red-500/10 text-red-200"
        : status === "running"
          ? "border-cyan-400/30 bg-cyan-500/10 text-cyan-200"
          : "border-white/10 bg-white/5 text-white/60";

  return (
    <span className={`whitespace-nowrap rounded-full border px-3 py-1 text-xs ${className}`}>
      {analysisStatusLabel(status)}
    </span>
  );
}

function formatDate(value: string) {
  if (!value) return "-";

  return new Intl.DateTimeFormat("fr-FR", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}