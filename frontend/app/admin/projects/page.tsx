"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { adminFetch } from "@/lib/admin-api";

type AdminProject = {
  id: number;
  title: string;
  description: string;
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

export default function AdminProjectsPage() {
  const router = useRouter();

  const [projects, setProjects] = useState<AdminProject[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [search, setSearch] = useState("");

  async function loadProjects() {
    try {
      setIsLoading(true);
      setError("");

      const data = await adminFetch("/admin/projects");
      setProjects(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue.");
    } finally {
      setIsLoading(false);
    }
  }

  async function deleteProject(project: AdminProject) {
    const confirmed = window.confirm(
      `Supprimer le projet "${project.title}" ?\n\nCette action est irréversible.`
    );

    if (!confirmed) return;

    try {
      setActionLoadingId(project.id);
      setError("");
      setMessage("");

      await adminFetch(`/admin/projects/${project.id}`, {
        method: "DELETE",
      });

      setMessage(`Projet "${project.title}" supprimé avec succès.`);
      await loadProjects();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur suppression projet.");
    } finally {
      setActionLoadingId(null);
    }
  }

  useEffect(() => {
    loadProjects();
  }, []);

  const filteredProjects = useMemo(() => {
    const query = search.toLowerCase().trim();

    if (!query) return projects;

    return projects.filter((project) => {
      return (
        project.title?.toLowerCase().includes(query) ||
        project.industry?.toLowerCase().includes(query) ||
        project.market_region?.toLowerCase().includes(query) ||
        project.owner_email?.toLowerCase().includes(query) ||
        project.analysis_status?.toLowerCase().includes(query)
      );
    });
  }, [projects, search]);

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <header className="border-b border-white/10 bg-white/5 px-6 py-4 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div>
            <p className="text-sm font-medium text-red-300">ForgeAI Admin</p>
            <h1 className="text-2xl font-bold">Gestion des projets</h1>
          </div>

          <nav className="flex flex-wrap gap-3 text-sm">
            <button
              onClick={() => router.back()}
              className="rounded-lg border border-white/10 px-4 py-2 text-white/80 hover:bg-white/10"
            >
              Retour
            </button>

            <Link
              href="/admin/dashboard"
              className="rounded-lg border border-white/10 px-4 py-2 text-white/80 hover:bg-white/10"
            >
              Dashboard
            </Link>

            <Link
              href="/admin/users"
              className="rounded-lg border border-white/10 px-4 py-2 text-white/80 hover:bg-white/10"
            >
              Users
            </Link>

            <Link
              href="/admin/analyses"
              className="rounded-lg border border-white/10 px-4 py-2 text-white/80 hover:bg-white/10"
            >
              Analyses
            </Link>
          </nav>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-6 py-8">
        <div className="grid gap-4 md:grid-cols-4">
          <Stat title="Total projets" value={projects.length} />
          <Stat
            title="Analyses terminées"
            value={projects.filter((p) => p.analysis_status === "completed").length}
          />
          <Stat
            title="Analyses en cours"
            value={projects.filter((p) => p.analysis_status === "running").length}
          />
          <Stat
            title="Analyses échouées"
            value={projects.filter((p) => p.analysis_status === "failed").length}
          />
        </div>

        <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-lg font-semibold">Liste des projets</h2>
              <p className="mt-1 text-sm text-white/50">
                Tous les projets créés par les utilisateurs.
              </p>
            </div>

            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Rechercher projet, secteur, région, owner..."
              className="w-full rounded-lg border border-white/10 bg-slate-900 px-4 py-3 text-sm outline-none focus:border-red-300 md:max-w-md"
            />
          </div>

          {message && (
            <div className="mt-5 rounded-lg border border-emerald-400/30 bg-emerald-500/10 p-3 text-sm text-emerald-200">
              {message}
            </div>
          )}

          {error && (
            <div className="mt-5 rounded-lg border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-200">
              {error}
            </div>
          )}

          {isLoading ? (
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
                    <th className="px-4 py-2">Owner</th>
                    <th className="px-4 py-2">Créé le</th>
                    <th className="px-4 py-2 text-right">Actions</th>
                  </tr>
                </thead>

                <tbody>
                  {filteredProjects.map((project) => {
                    const isBusy = actionLoadingId === project.id;

                    return (
                      <tr key={project.id} className="bg-white/5">
                        <td className="rounded-l-xl px-4 py-4">
                          <div className="font-medium">{project.title}</div>
                          <div className="line-clamp-1 text-xs text-white/40">
                            {project.description}
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

              {filteredProjects.length === 0 && (
                <div className="rounded-xl border border-white/10 bg-white/5 p-6 text-center text-white/50">
                  Aucun projet trouvé.
                </div>
              )}
            </div>
          )}
        </div>
      </section>
    </main>
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
    <span className={`rounded-full border px-3 py-1 text-xs ${className}`}>
      {status}
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