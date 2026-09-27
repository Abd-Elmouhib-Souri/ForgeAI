"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { adminFetch, removeAdminToken } from "@/lib/admin-api";

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
  const router = useRouter();

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

  function handleLogout() {
    removeAdminToken();
    router.replace("/admin/login");
  }

  useEffect(() => {
    loadStats();
  }, []);

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <header className="border-b border-white/10 bg-white/5 px-6 py-4 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div>
            <p className="text-sm font-medium text-red-300">ForgeAI Admin</p>
            <h1 className="text-2xl font-bold">Dashboard administrateur</h1>
          </div>

          <nav className="flex flex-wrap items-center gap-3 text-sm">
            <Link
              href="/admin/users"
              className="rounded-lg border border-white/10 px-4 py-2 text-white/80 transition hover:bg-white/10"
            >
              Users
            </Link>

            <Link
              href="/admin/projects"
              className="rounded-lg border border-white/10 px-4 py-2 text-white/80 transition hover:bg-white/10"
            >
              Projects
            </Link>

            <Link
              href="/admin/analyses"
              className="rounded-lg border border-white/10 px-4 py-2 text-white/80 transition hover:bg-white/10"
            >
              Analyses
            </Link>

            <Link
              href="/admin/health"
              className="rounded-lg border border-white/10 px-4 py-2 text-white/80 transition hover:bg-white/10"
            >
              Health
            </Link>

            <Link
              href="/admin/errors"
              className="rounded-lg border border-white/10 px-4 py-2 text-white/80 transition hover:bg-white/10"
            >
              Errors
            </Link>

            <Link
              href="/admin/audit"
              className="rounded-lg border border-white/10 px-4 py-2 text-white/80 transition hover:bg-white/10"
            >
              Journal d&apos;audit
            </Link>

            <button
              onClick={handleLogout}
              className="rounded-lg border border-red-400/30 bg-red-500/10 px-4 py-2 text-red-200 transition hover:bg-red-500/20"
            >
              Déconnexion
            </button>
          </nav>
        </div>
      </header>

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
                title="Admins"
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

            <div className="mt-6 grid gap-6 lg:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
                <h2 className="text-lg font-semibold">Analyses IA</h2>

                <div className="mt-5 grid gap-3">
                  <MiniStat label="Terminées" value={stats.analyses.completed} />
                  <MiniStat label="En cours" value={stats.analyses.running} />
                  <MiniStat label="Échouées" value={stats.analyses.failed} />
                  <MiniStat
                    label="Avec erreurs"
                    value={stats.analyses.with_errors ?? 0}
                  />
                </div>
              </div>

              <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
                <h2 className="text-lg font-semibold">Navigation admin</h2>

                <div className="mt-5 grid gap-3">
                  <AdminLink label="Utilisateurs" href="/admin/users" />
                  <AdminLink label="Projets" href="/admin/projects" />
                  <AdminLink label="Analyses IA" href="/admin/analyses" />
                  <AdminLink label="Health système" href="/admin/health" />
                  <AdminLink label="Erreurs" href="/admin/errors" />
                </div>
              </div>
            </div>

            <div className="mt-6 grid gap-6 lg:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
                <h2 className="text-lg font-semibold">Top secteurs</h2>

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
                <h2 className="text-lg font-semibold">Top régions</h2>

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
    </main>
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

function AdminLink({ label, href }: { label: string; href: string }) {
  return (
    <Link
      href={href}
      className="rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-sm text-white/80 transition hover:bg-white/10"
    >
      {label}
    </Link>
  );
}