"use client";

import { useState } from "react";
import { RefreshCw } from "lucide-react";

import AdminPageHeader from "@/app/admin/_components/AdminPageHeader";
import { Button } from "@/app/admin/_components/Button";
import { healthStatusLabel } from "@/app/admin/_components/labels";
import { useAdminResource } from "@/app/admin/_components/useAdminResource";

// Sprint 7.7: every service is really contacted by the admin API
// (services/health_checks.py). This page only displays the report.
type HealthService = {
  key: string;
  name: string;
  type: string;
  status: "healthy" | "degraded" | "down" | "not_configured" | string;
  latency_ms: number;
  message: string;
  details: {
    missing_models?: string[];
    configured_models?: string[];
    database?: string[];
    code?: string[];
    waiting_over_60s?: number;
    stalled?: number;
    free_gb?: number;
    tested?: boolean;
  };
};

type HealthReport = {
  overall_status: string;
  checked_at: string;
  cache_seconds: number;
  services: HealthService[];
};

// Most urgent first: what is down, then degraded, then the rest.
const SEVERITY: Record<string, number> = { down: 0, degraded: 1, not_configured: 2, healthy: 3 };

const TONE: Record<string, string> = {
  healthy: "border-emerald-400/30 bg-emerald-500/10 text-emerald-200",
  degraded: "border-amber-400/30 bg-amber-500/10 text-amber-200",
  down: "border-red-400/30 bg-red-500/10 text-red-200",
  not_configured: "border-white/15 bg-white/5 text-white/60",
};

const OVERALL_TEXT: Record<string, string> = {
  healthy: "Tous les services testés répondent correctement.",
  degraded: "La plateforme fonctionne, mais certains services demandent une action.",
  down: "Au moins un service est hors service : des fonctions de la plateforme sont bloquées.",
};

export default function AdminHealthPage() {
  // 0 = cached report; each click on "Tester maintenant" asks a fresh test.
  const [run, setRun] = useState(0);
  const report = useAdminResource<HealthReport>(
    run === 0 ? "/admin/health" : `/admin/health?refresh=true&run=${run}`,
  );
  const data = report.data;
  const services = [...(data?.services ?? [])].sort(
    (a, b) => (SEVERITY[a.status] ?? 9) - (SEVERITY[b.status] ?? 9),
  );

  return (
    <div>
      <AdminPageHeader
        title="Santé du système"
        subtitle="Chaque service est réellement contacté (délai maximal 5 s par service)."
        actions={
          <Button
            variant="primary"
            icon={RefreshCw}
            loading={report.isLoading}
            onClick={() => setRun((current) => current + 1)}
          >
            {report.isLoading ? "Test en cours..." : "Tester maintenant"}
          </Button>
        }
      />

      <section className="mx-auto max-w-7xl px-6 py-8">
        {report.error && (
          <div className="mb-6 rounded-xl border border-red-400/30 bg-red-500/10 p-4 text-sm text-red-200">
            {report.error}
          </div>
        )}

        {!data ? (
          <p className="text-white/60">Test des services en cours...</p>
        ) : (
          <>
            <div className={`mb-6 rounded-2xl border p-6 ${TONE[data.overall_status] ?? TONE.not_configured}`}>
              <p className="text-sm opacity-80">Statut global</p>
              <p className="mt-1 text-3xl font-bold">{healthStatusLabel(data.overall_status)}</p>
              <p className="mt-2 text-sm opacity-90">{OVERALL_TEXT[data.overall_status] ?? ""}</p>
              <p className="mt-2 text-xs opacity-70">
                Vérifié le {formatDate(data.checked_at)} · résultat conservé {data.cache_seconds} s
              </p>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              {services.map((service) => (
                <div key={service.key} className="rounded-2xl border border-white/10 bg-white/5 p-5">
                  <div className="flex items-start justify-between gap-3">
                    <h2 className="text-lg font-semibold">{service.name}</h2>
                    <span
                      className={`whitespace-nowrap rounded-full border px-3 py-1 text-xs ${TONE[service.status] ?? TONE.not_configured}`}
                    >
                      {healthStatusLabel(service.status)}
                    </span>
                  </div>

                  <p className="mt-3 text-sm text-white/75">{service.message}</p>

                  {service.details.missing_models && service.details.missing_models.length > 0 && (
                    <p className="mt-2 text-sm text-amber-200">
                      Modèles introuvables : {service.details.missing_models.join(", ")}
                    </p>
                  )}
                  {service.details.configured_models && service.details.configured_models.length > 0 && (
                    <p className="mt-1 text-xs text-white/50">
                      Modèles configurés : {service.details.configured_models.join(", ")}
                    </p>
                  )}
                  {service.details.database && (
                    <p className="mt-1 text-xs text-white/50">
                      Version de la base : {service.details.database.join(", ") || "—"} · version du code :{" "}
                      {(service.details.code ?? []).join(", ")}
                    </p>
                  )}

                  <p className="mt-3 text-xs text-white/40">Temps de réponse : {formatLatency(service.latency_ms)}</p>
                </div>
              ))}
            </div>
          </>
        )}
      </section>
    </div>
  );
}

function formatLatency(ms: number) {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${Math.round(ms)} ms`;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "medium" }).format(new Date(value));
}
