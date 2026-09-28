"use client";

import { useEffect, useState } from "react";
import { adminFetch } from "@/lib/admin-api";
import AdminPageHeader from "@/app/admin/_components/AdminPageHeader";

type AdminStats = {
  users: {
    total: number;
    active: number;
    verified: number;
    unverified?: number;
    admins: number;
  };
  projects: {
    total: number;
  };
  analyses: {
    completed: number;
    running: number;
    failed: number;
    with_errors?: number;
    average_score: number | null;
  };
  top_sectors: {
    industry: string;
    count: number;
  }[];
  top_regions: {
    region: string;
    count: number;
  }[];
};

export default function AdminDashboardPage() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  async function loadStats() {
    try {
      setIsLoading(true);
      setError("");

      const data = await adminFetch("/admin/stats");
      setStats(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadStats();
  }, []);

  return (
    <div>
      <AdminPageHeader title="Tableau de bord" subtitle="Vue d'ensemble de la plateforme ForgeAI." />

      <section className="mx-auto max-w-7xl px-6 py-8">
        {isLoading && (
          <div className="rounded-xl border border-white/10 bg-white/5 p-6 text-white/70">
            Chargement des statistiques...
          </div>
        )}

        {error && (
          <div className="rounded-xl border border-red-400/30 bg-red-500/10 p-6 text-red-200">
            {error}
          </div>
        )}

        {stats && (
          <>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <StatCard
                title="Utilisateurs"
                value={stats.users.total}
                subtitle={`${stats.users.active} actifs · ${stats.users.verified} vérifiés`}
              />

              <StatCard
                title="Administrateurs"
                value={stats.users.admins}
                subtitle="Comptes administrateurs"
              />

              <StatCard
                title="Projets"
                value={stats.projects.total}
                subtitle="Tous les projets créés"
              />

              <StatCard
                title="Score moyen"
                value={stats.analyses.average_score ?? "-"}
                subtitle={`${stats.analyses.completed} analyses terminées`}
              />
            </div>

            <div className="mt-6">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
                <h2 className="text-lg font-semibold">Analyses IA</h2>

                <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <MiniStat label="Terminées" value={stats.analyses.completed} />
                  <MiniStat label="En cours" value={stats.analyses.running} />
                  <MiniStat label="Échouées" value={stats.analyses.failed} />
                  <MiniStat
                    label="Avec erreurs"
                    value={stats.analyses.with_errors ?? 0}
                  />
                </div>
              </div>

            {/* Navigation: the console sidebar (Sprint 7.3), no duplicate link panel. */}
            </div>

            <div className="mt-6 grid gap-6 lg:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
                <h2 className="text-lg font-semibold">Principaux secteurs</h2>

                <div className="mt-5 space-y-3">
                  {stats.top_sectors.map((sector) => (
                    <MiniStat
                      key={sector.industry}
                      label={sector.industry || "Non défini"}
                      value={sector.count}
                    />
                  ))}
                </div>
              </div>

              <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
                <h2 className="text-lg font-semibold">Principales régions</h2>

                <div className="mt-5 space-y-3">
                  {stats.top_regions.map((region) => (
                    <MiniStat
                      key={region.region}
                      label={region.region || "Non définie"}
                      value={region.count}
                    />
                  ))}
                </div>
              </div>
            </div>
          </>
        )}
      </section>
    </div>
  );
}

function StatCard({
  title,
  value,
  subtitle,
}: {
  title: string;
  value: string | number;
  subtitle: string;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-6 shadow-xl">
      <p className="text-sm text-white/50">{title}</p>
      <p className="mt-3 text-3xl font-bold">{value}</p>
      <p className="mt-2 text-sm text-white/50">{subtitle}</p>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-white/10 bg-white/5 px-4 py-3">
      <span className="text-sm text-white/70">{label}</span>
      <span className="font-semibold">{value}</span>
    </div>
  );
}
