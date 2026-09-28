"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { adminFetch } from "@/lib/admin-api";
import AdminPageHeader from "@/app/admin/_components/AdminPageHeader";
import { analysisStatusLabel } from "@/app/admin/_components/labels";

type UserDetail = {
  user: {
    id: number;
    email: string;
    full_name: string;
    role: string;
    is_active: boolean;
    is_email_verified: boolean;
    is_two_factor_enabled: boolean;
    created_at: string;
    project_count: number;
  };
  stats: {
    total_projects: number;
    completed_analyses: number;
    failed_analyses: number;
    average_score: number | null;
  };
  last_project: Project | null;
};

type Project = {
  id: number;
  title: string;
  description: string;
  industry: string;
  market_region: string;
  status: string;
  startup_score: number | null;
  analysis_status: string;
  analysis_step: string;
  analysis_progress: number;
  analysis_error: string | null;
  created_at: string;
};

export default function AdminUserDetailPage() {
  const params = useParams();
  const userId = params.id as string;

  const [detail, setDetail] = useState<UserDetail | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const loadData = useCallback(async () => {
    if (!userId) return;

    try {
      setIsLoading(true);
      setError("");

      const userData = await adminFetch(`/admin/users/${userId}`);
      const userProjects = await adminFetch(`/admin/users/${userId}/projects`);

      setDetail(userData);
      setProjects(userProjects);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue.");
      setDetail(null);
      setProjects([]);
    } finally {
      setIsLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  return (
    <div>
      <AdminPageHeader title="Détail utilisateur" backHref="/admin/users" backLabel="Utilisateurs" />

      <section className="mx-auto max-w-7xl px-6 py-8">
        {isLoading && (
          <div className="rounded-xl border border-white/10 bg-white/5 p-6 text-white/60">
            Chargement...
          </div>
        )}

        {error && (
          <div className="rounded-xl border border-red-400/30 bg-red-500/10 p-6 text-red-200">
            {error}
          </div>
        )}

        {detail && (
          <>
            <div className="grid gap-4 md:grid-cols-4">
              <Stat title="Projets" value={detail.stats.total_projects} />
              <Stat
                title="Analyses terminées"
                value={detail.stats.completed_analyses}
              />
              <Stat
                title="Analyses échouées"
                value={detail.stats.failed_analyses}
              />
              <Stat
                title="Score moyen"
                value={detail.stats.average_score ?? "-"}
              />
            </div>

            <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-6">
              <h2 className="text-xl font-semibold">{detail.user.full_name}</h2>
              <p className="mt-1 text-white/50">{detail.user.email}</p>

              <div className="mt-5 grid gap-3 md:grid-cols-2">
                <Info label="Rôle" value={detail.user.role} />
                <Info
                  label="Compte actif"
                  value={detail.user.is_active ? "Oui" : "Non"}
                />
                <Info
                  label="Email vérifié"
                  value={detail.user.is_email_verified ? "Oui" : "Non"}
                />
                <Info
                  label="2FA"
                  value={detail.user.is_two_factor_enabled ? "Oui" : "Non"}
                />
              </div>
            </div>

            <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-6">
              <h2 className="text-xl font-semibold">Projets de cet utilisateur</h2>

              <div className="mt-5 overflow-x-auto">
                <table className="w-full min-w-[900px] border-separate border-spacing-y-3 text-left text-sm">
                  <thead className="text-white/50">
                    <tr>
                      <th className="px-4 py-2">Projet</th>
                      <th className="px-4 py-2">Secteur</th>
                      <th className="px-4 py-2">Région</th>
                      <th className="px-4 py-2">Score</th>
                      <th className="px-4 py-2">Analyse</th>
                      <th className="px-4 py-2">Progression</th>
                      <th className="px-4 py-2">Créé le</th>
                    </tr>
                  </thead>

                  <tbody>
                    {projects.map((project) => (
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
                        <td className="px-4 py-4">{analysisStatusLabel(project.analysis_status)}</td>
                        <td className="px-4 py-4">
                          {project.analysis_progress ?? 0}%
                        </td>
                        <td className="rounded-r-xl px-4 py-4 text-white/60">
                          {formatDate(project.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {projects.length === 0 && (
                  <div className="rounded-xl border border-white/10 bg-white/5 p-6 text-center text-white/50">
                    Aucun projet.
                  </div>
                )}
              </div>
            </div>
          </>
        )}
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

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/5 px-4 py-3">
      <p className="text-xs text-white/40">{label}</p>
      <p className="mt-1 font-medium">{value}</p>
    </div>
  );
}

function formatDate(value: string) {
  if (!value) return "-";

  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}