"use client";

import { FormEvent, useState } from "react";
import { adminDownload, adminFetch, isAdminActionCancelled } from "@/lib/admin-api";
import { ANALYSIS_STATUS_LABELS, analysisStatusLabel } from "@/app/admin/_components/labels";
import { buildListQuery, type Page } from "@/app/admin/_components/listQuery";
import Pagination from "@/app/admin/_components/Pagination";
import type { AdminStats } from "@/app/admin/_components/stats";
import { useAdminResource } from "@/app/admin/_components/useAdminResource";
import AdminPageHeader from "@/app/admin/_components/AdminPageHeader";

type AdminProject = {
  id: number;
  title: string;
  description_excerpt: string | null; // first 160 characters, cut by the API
  industry: string;
  market_region: string;
  status: string;
  startup_score: number | null;
  analysis_status: string;
  analysis_progress: number;
  analysis_error: string | null;
  owner_email: string;
  owner_name: string;
  created_at: string;
  updated_at: string;
};

const SORTS: Record<string, { label: string; sort: string; order: "asc" | "desc" }> = {
  recent: { label: "Plus récents", sort: "created_at", order: "desc" },
  updated: { label: "Modifiés récemment", sort: "updated_at", order: "desc" },
  score: { label: "Meilleur score", sort: "startup_score", order: "desc" },
  title: { label: "Titre (A → Z)", sort: "title", order: "asc" },
};

const PAGE_SIZE = 25;

export default function AdminProjectsPage() {
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [searchDraft, setSearchDraft] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sortKey, setSortKey] = useState("recent");
  const [page, setPage] = useState(1);

  // Sprint 7.4: search, status filter, sort and paging are done by the API;
  // the same filters feed the CSV export.
  const filters = { search, status: statusFilter, sort: SORTS[sortKey].sort, order: SORTS[sortKey].order };
  const list = useAdminResource<Page<AdminProject>>(
    `/admin/projects${buildListQuery({ ...filters, page, page_size: PAGE_SIZE })}`,
  );
  const stats = useAdminResource<AdminStats>("/admin/stats");
  const projects = list.data?.items ?? [];

  function loadProjects() {
    list.reload();
    stats.reload();
  }

  function applySearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSearch(searchDraft);
    setPage(1);
  }

  async function exportCsv() {
    try {
      setError("");
      await adminDownload(`/admin/projects/export.csv${buildListQuery(filters)}`, "forgeai-projets.csv");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export impossible.");
    }
  }

  async function deleteProject(project: AdminProject) {
    try {
      setActionLoadingId(project.id);
      setError("");
      setMessage("");

      // Sensitive: the admin API requires a fresh 2FA code (Sprint 7.1).
      await adminFetch(`/admin/projects/${project.id}`, {
        confirm: `Supprimer définitivement le projet « ${project.title} » ?\nSon analyse et ses documents exportés seront supprimés.`,
        method: "DELETE",
      });

      setMessage(`Projet "${project.title}" supprimé avec succès.`);
      await loadProjects();
    } catch (err) {
      if (isAdminActionCancelled(err)) return;
      setError(err instanceof Error ? err.message : "Erreur suppression projet.");
    } finally {
      setActionLoadingId(null);
    }
  }

  return (
    <div>
      <AdminPageHeader title="Projets" subtitle="Tous les projets créés sur la plateforme." />

      <section className="mx-auto max-w-7xl px-6 py-8">
        <div className="grid gap-4 md:grid-cols-4">
          {/* Counters of the whole platform, computed by the database. */}
          <Stat title="Total projets" value={stats.data?.projects.total ?? 0} />
          <Stat title="Analyses terminées" value={stats.data?.analyses.completed ?? 0} />
          <Stat title="Analyses en cours" value={stats.data?.analyses.running ?? 0} />
          <Stat title="Analyses échouées" value={stats.data?.analyses.failed ?? 0} />
        </div>

        <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-lg font-semibold">Liste des projets</h2>
              <p className="mt-1 text-sm text-white/50">
                Tous les projets créés par les utilisateurs.
              </p>
            </div>

            <button
              type="button"
              onClick={exportCsv}
              className="rounded-lg border border-white/10 px-4 py-2 text-sm text-white/80 transition hover:bg-white/10"
            >
              Exporter en CSV
            </button>
          </div>

          <form onSubmit={applySearch} className="mt-5 flex flex-col gap-3 md:flex-row">
            <input
              value={searchDraft}
              onChange={(event) => setSearchDraft(event.target.value)}
              placeholder="Rechercher projet, secteur, région, propriétaire..."
              className="w-full rounded-lg border border-white/10 bg-slate-900 px-4 py-2.5 text-sm outline-none focus:border-red-300 md:max-w-md"
            />
            <button type="submit" className="rounded-lg bg-white/15 px-4 py-2.5 text-sm font-semibold hover:bg-white/25">
              Rechercher
            </button>
            <select
              value={statusFilter}
              onChange={(event) => {
                setStatusFilter(event.target.value);
                setPage(1);
              }}
              aria-label="Statut de l'analyse"
              className="rounded-lg border border-white/10 bg-slate-900 px-3 py-2.5 text-sm md:ml-auto"
            >
              <option value="">Tous les statuts</option>
              {Object.entries(ANALYSIS_STATUS_LABELS).map(([code, label]) => (
                <option key={code} value={code}>
                  {label}
                </option>
              ))}
            </select>
            <select
              value={sortKey}
              onChange={(event) => {
                setSortKey(event.target.value);
                setPage(1);
              }}
              aria-label="Trier"
              className="rounded-lg border border-white/10 bg-slate-900 px-3 py-2.5 text-sm"
            >
              {Object.entries(SORTS).map(([key, option]) => (
                <option key={key} value={key}>
                  {option.label}
                </option>
              ))}
            </select>
          </form>

          {message && (
            <div className="mt-5 rounded-lg border border-emerald-400/30 bg-emerald-500/10 p-3 text-sm text-emerald-200">
              {message}
            </div>
          )}

          {(error || list.error) && (
            <div className="mt-5 rounded-lg border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-200">
              {error || list.error}
            </div>
          )}

          {!list.data ? (
            <div className="mt-6 rounded-xl border border-white/10 bg-white/5 p-6 text-white/60">
              Chargement des projets...
            </div>
          ) : (
            <div className="mt-6 overflow-x-auto">
              <table className="w-full min-w-[1200px] border-separate border-spacing-y-3 text-left text-sm">
                <thead className="text-white/50">
                  <tr>
                    <th className="px-4 py-2">Projet</th>
                    <th className="px-4 py-2">Secteur</th>
                    <th className="px-4 py-2">Région</th>
                    <th className="px-4 py-2">Score</th>
                    <th className="px-4 py-2">Analyse</th>
                    <th className="px-4 py-2">Propriétaire</th>
                    <th className="px-4 py-2">Créé le</th>
                    <th className="px-4 py-2 text-right">Actions</th>
                  </tr>
                </thead>

                <tbody>
                  {projects.map((project) => {
                    const isBusy = actionLoadingId === project.id;

                    return (
                      <tr key={project.id} className="bg-white/5">
                        <td className="rounded-l-xl px-4 py-4">
                          <div className="font-medium">{project.title}</div>
                          <div className="line-clamp-1 text-xs text-white/40">
                            {project.description_excerpt}
                          </div>
                        </td>

                        <td className="px-4 py-4">{project.industry}</td>
                        <td className="px-4 py-4">{project.market_region}</td>
                        <td className="px-4 py-4 font-semibold">
                          {project.startup_score ?? "-"}
                        </td>

                        <td className="px-4 py-4">
                          <Badge status={project.analysis_status} />
                          <div className="mt-1 text-xs text-white/40">
                            {project.analysis_progress ?? 0}%
                          </div>
                        </td>

                        <td className="px-4 py-4">
                          <div>{project.owner_name}</div>
                          <div className="text-xs text-white/40">
                            {project.owner_email}
                          </div>
                        </td>

                        <td className="px-4 py-4 text-white/60">
                          {formatDate(project.created_at)}
                        </td>

                        <td className="rounded-r-xl px-4 py-4">
                          <div className="flex justify-end gap-2">
                            <button
                              disabled={isBusy}
                              onClick={() => deleteProject(project)}
                              className="rounded-lg border border-red-400/30 bg-red-500/10 px-3 py-2 text-xs text-red-200 transition hover:bg-red-500/20 disabled:opacity-50"
                            >
                              Supprimer
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              {list.data.total === 0 && (
                <div className="rounded-xl border border-white/10 bg-white/5 p-6 text-center text-white/50">
                  Aucun projet trouvé.
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
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}