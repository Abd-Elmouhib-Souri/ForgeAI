"use client";

import { useEffect, useState } from "react";
import { adminFetch } from "@/lib/admin-api";
import AdminPageHeader from "@/app/admin/_components/AdminPageHeader";
import { analysisStatusLabel } from "@/app/admin/_components/labels";

type AdminError = {
  id: string;
  source: string;
  level: string;
  status: string;
  message: string;
  project_id: number;
  project_title: string;
  owner_email: string;
  owner_name: string;
  analysis_status: string;
  created_at: string;
};

export default function AdminErrorsPage() {
  const [errors, setErrors] = useState<AdminError[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadErrors() {
    try {
      setIsLoading(true);
      setError("");

      const data = await adminFetch("/admin/errors");
      setErrors(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadErrors();
  }, []);

  return (
    <div>
      <AdminPageHeader title="Erreurs" subtitle="Analyses en échec ou avec anomalies." />

      <section className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-6 rounded-2xl border border-white/10 bg-white/5 p-6">
          <p className="text-sm text-white/50">Erreurs ouvertes</p>
          <p className="mt-2 text-3xl font-bold">{errors.length}</p>

          <button
            onClick={loadErrors}
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

        {!isLoading && errors.length === 0 && (
          <div className="rounded-2xl border border-emerald-400/30 bg-emerald-500/10 p-6 text-emerald-200">
            Aucune erreur détectée actuellement.
          </div>
        )}

        <div className="space-y-4">
          {errors.map((item) => (
            <div
              key={item.id}
              className="rounded-2xl border border-red-400/20 bg-red-500/10 p-6"
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold">{item.project_title}</h2>
                  <p className="text-sm text-white/50">{item.owner_email}</p>
                </div>

                <span className="rounded-full border border-red-400/30 bg-red-500/10 px-3 py-1 text-xs text-red-200">
                  {item.level}
                </span>
              </div>

              <p className="mt-4 text-sm text-red-100">{item.message}</p>

              <div className="mt-4 grid gap-3 text-sm md:grid-cols-3">
                <Info label="Source" value={item.source} />
                <Info label="Statut de l'analyse" value={analysisStatusLabel(item.analysis_status)} />
                <Info label="Date" value={formatDate(item.created_at)} />
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/5 px-4 py-3">
      <p className="text-xs text-white/40">{label}</p>
      <p className="mt-1 font-medium">{value || "-"}</p>
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