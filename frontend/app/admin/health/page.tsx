"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { adminFetch } from "@/lib/admin-api";

type HealthService = {
  name: string;
  type: string;
  status: string;
  configured: boolean;
  model?: string;
  message: string;
};

export default function AdminHealthPage() {
  const [services, setServices] = useState<HealthService[]>([]);
  const [overallStatus, setOverallStatus] = useState("");
  const [checkedAt, setCheckedAt] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  async function loadHealth() {
    try {
      setIsLoading(true);
      setError("");

      const data = await adminFetch("/admin/health");

      setServices(data.services || []);
      setOverallStatus(data.overall_status);
      setCheckedAt(data.checked_at);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadHealth();
  }, []);

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <header className="border-b border-white/10 bg-white/5 px-6 py-4">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div>
            <p className="text-sm font-medium text-red-300">ForgeAI Admin</p>
            <h1 className="text-2xl font-bold">Health système</h1>
          </div>

          <nav className="flex gap-3 text-sm">
            <Link
              href="/admin/dashboard"
              className="rounded-lg border border-white/10 px-4 py-2 hover:bg-white/10"
            >
              Dashboard
            </Link>
            <Link
              href="/admin/users"
              className="rounded-lg border border-white/10 px-4 py-2 hover:bg-white/10"
            >
              Users
            </Link>
            <Link
              href="/admin/errors"
              className="rounded-lg border border-white/10 px-4 py-2 hover:bg-white/10"
            >
              Errors
            </Link>
          </nav>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-6 rounded-2xl border border-white/10 bg-white/5 p-6">
          <p className="text-sm text-white/50">Statut global</p>
          <p className="mt-2 text-3xl font-bold">{overallStatus || "-"}</p>
          <p className="mt-2 text-sm text-white/40">
            Dernière vérification : {checkedAt ? formatDate(checkedAt) : "-"}
          </p>

          <button
            onClick={loadHealth}
            className="mt-4 rounded-lg bg-red-500 px-4 py-2 text-sm font-medium hover:bg-red-400"
          >
            Rafraîchir
          </button>
        </div>

        {isLoading && <p className="text-white/60">Chargement...</p>}

        {error && (
          <div className="rounded-xl border border-red-400/30 bg-red-500/10 p-6 text-red-200">
            {error}
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-2">
          {services.map((service) => (
            <div
              key={service.name}
              className="rounded-2xl border border-white/10 bg-white/5 p-6"
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold">{service.name}</h2>
                  <p className="text-sm text-white/50">{service.type}</p>
                </div>

                <span className={badgeClass(service.status)}>
                  {service.status}
                </span>
              </div>

              {service.model && (
                <p className="mt-4 text-sm text-cyan-200">
                  Model: {service.model}
                </p>
              )}

              <p className="mt-4 text-sm text-white/60">{service.message}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}

function badgeClass(status: string) {
  if (status === "healthy") {
    return "rounded-full border border-emerald-400/30 bg-emerald-500/10 px-3 py-1 text-xs text-emerald-200";
  }

  if (status === "down") {
    return "rounded-full border border-red-400/30 bg-red-500/10 px-3 py-1 text-xs text-red-200";
  }

  if (status === "warning") {
    return "rounded-full border border-yellow-400/30 bg-yellow-500/10 px-3 py-1 text-xs text-yellow-200";
  }

  return "rounded-full border border-cyan-400/30 bg-cyan-500/10 px-3 py-1 text-xs text-cyan-200";
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}