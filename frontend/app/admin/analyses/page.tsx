"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { adminFetch } from "@/lib/admin-api";

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
};

export default function AdminAnalysesPage() {
  const router = useRouter();

  const [analyses, setAnalyses] = useState<AdminAnalysis[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<"all" | "completed" | "running" | "failed">(
    "all"
  );

  async function loadAnalyses() {
    try {
      setIsLoading(true);
      setError("");

      const data = await adminFetch("/admin/analyses");
      setAnalyses(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadAnalyses();
  }, []);

  const filteredAnalyses = useMemo(() => {
    if (filter === "all") return analyses;
    return analyses.filter((item) => item.analysis_status === filter);
  }, [analyses, filter]);

  const stats = useMemo(() => {
    return {
      total: analyses.length,
      completed: analyses.filter((a) => a.analysis_status === "completed").length,
      running: analyses.filter((a) => a.analysis_status === "running").length,
      failed: analyses.filter((a) => a.analysis_status === "failed").length,
    };
  }, [analyses]);

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <header className="border-b border-white/10 bg-white/5 px-6 py-4 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div>
            <p className="text-sm font-medium text-red-300">ForgeAI Admin</p>
            <h1 className="text-2xl font-bold">Suivi des analyses IA</h1>
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
              href="/admin/projects"
              className="rounded-lg border border-white/10 px-4 py-2 text-white/80 hover:bg-white/10"
            >
              Projects
            </Link>

            <Link
              href="/admin/errors"
              className="rounded-lg border border-white/10 px-4 py-2 text-white/80 hover:bg-white/10"
            >
              Errors
            </Link>
          </nav>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-6 py-8">
        <div className="grid gap-4 md:grid-cols-4">
          <Stat title="Total analyses" value={stats.total} />
          <Stat title="Terminées" value={stats.completed} />
          <Stat title="En cours" value={stats.running} />
          <Stat title="Échouées" value={stats.failed} />
        </div>

        <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-lg font-semibold">Liste des analyses</h2>
              <p className="mt-1 text-sm text-white/50">
                Suivi des analyses IA de tous les projets.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <FilterButton label="Toutes" active={filter === "all"} onClick={() => setFilter("all")} />
              <FilterButton label="Terminées" active={filter === "completed"} onClick={() => setFilter("completed")} />
              <FilterButton label="En cours" active={filter === "running"} onClick={() => setFilter("running")} />
              <FilterButton label="Échouées" active={filter === "failed"} onClick={() => setFilter("failed")} />
            </div>
          </div>

          {error && (
            <div className="mt-5 rounded-lg border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-200">
              {error}
            </div>
          )}

          {isLoading ? (
            <div className="mt-6 rounded-xl border border-white/10 bg-white/5 p-6 text-white/60">
              Chargement des analyses...
            </div>
          ) : (
            <div className="mt-6 overflow-x-auto">
              <table className="w-full min-w-[1250px] border-separate border-spacing-y-3 text-left text-sm">
                <thead className="text-white/50">
                  <tr>
                    <th className="px-4 py-2">Projet</th>
                    <th className="px-4 py-2">Secteur</th>
                    <th className="px-4 py-2">Région</th>
                    <th className="px-4 py-2">Score</th>
                    <th className="px-4 py-2">Statut</th>
                    <th className="px-4 py-2">Progression</th>
                    <th className="px-4 py-2">Owner</th>
                    <th className="px-4 py-2">Fin</th>
                    <th className="px-4 py-2 text-right">Actions</th>
                  </tr>
                </thead>

                <tbody>
                  {filteredAnalyses.map((analysis) => (
                    <tr key={analysis.project_id} className="bg-white/5">
                      <td className="rounded-l-xl px-4 py-4">
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

                      <td className="px-4 py-4">{analysis.industry}</td>
                      <td className="px-4 py-4">{analysis.market_region}</td>
                      <td className="px-4 py-4 font-semibold">
                        {analysis.startup_score ?? "-"}
                      </td>

                      <td className="px-4 py-4">
                        <Badge status={analysis.analysis_status} />
                      </td>

                      <td className="px-4 py-4">
                        <div className="h-2 w-32 overflow-hidden rounded-full bg-white/10">
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

                      <td className="px-4 py-4">
                        <div>{analysis.owner_name}</div>
                        <div className="text-xs text-white/40">
                          {analysis.owner_email}
                        </div>
                      </td>

                      <td className="px-4 py-4 text-white/60">
                        {analysis.analysis_completed_at
                          ? formatDate(analysis.analysis_completed_at)
                          : "-"}
                      </td>

                      <td className="rounded-r-xl px-4 py-4 text-right">
                        <Link
                          href={`/admin/analyses/${analysis.project_id}`}
                          className="rounded-lg border border-cyan-400/30 bg-cyan-500/10 px-3 py-2 text-xs font-medium text-cyan-200 transition hover:bg-cyan-500/20"
                        >
                          Diagnostic
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {filteredAnalyses.length === 0 && (
                <div className="rounded-xl border border-white/10 bg-white/5 p-6 text-center text-white/50">
                  Aucune analyse trouvée.
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

function FilterButton({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={
        active
          ? "rounded-lg bg-red-500 px-3 py-2 text-xs font-medium text-white"
          : "rounded-lg border border-white/10 px-3 py-2 text-xs text-white/70 transition hover:bg-white/10"
      }
    >
      {label}
    </button>
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