"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { adminDownload, adminFetch } from "@/lib/admin-api";

// Sprint 7.2: read-only view of the admin audit log (who, what, when, from where).

type AuditEntry = {
  id: number;
  created_at: string | null;
  actor_email: string | null;
  action: string;
  action_label: string;
  target_type: string | null;
  target_id: string | null;
  target_label: string | null;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string | null;
  result: "success" | "failure" | "denied";
  detail: string | null;
};

type AuditPage = { items: AuditEntry[]; total: number; page: number; page_size: number };

type Filters = { action: string; result: string; actor: string; date_from: string; date_to: string };

const EMPTY_FILTERS: Filters = { action: "", result: "", actor: "", date_from: "", date_to: "" };
const PAGE_SIZE = 50;

const RESULTS: Record<string, { label: string; className: string }> = {
  success: { label: "Succès", className: "border-emerald-400/30 bg-emerald-500/10 text-emerald-200" },
  failure: { label: "Échec", className: "border-red-400/30 bg-red-500/10 text-red-200" },
  denied: { label: "Refusé", className: "border-amber-400/30 bg-amber-500/10 text-amber-200" },
};

// Reason codes written by the backend -> readable French.
const DETAILS: Record<string, string> = {
  bad_credentials: "E-mail ou mot de passe incorrect",
  not_admin: "Compte non administrateur",
  inactive: "Compte désactivé",
  email_unverified: "E-mail non vérifié",
  totp_invalid: "Code 2FA invalide",
  too_many_attempts: "Trop de tentatives",
  confirmation_invalid: "Code de confirmation invalide",
  "2fa_enrollment_required": "Première connexion : activation 2FA demandée",
};

function formatDate(value: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "medium" });
}

// Query string shared by the list and the CSV export (empty filters are dropped).
function buildQuery(filters: Filters, extra: Record<string, string> = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (!value) return;
    // <input type="date"> gives a day: cover the whole day for "date_to".
    if (key === "date_from") params.set(key, `${value}T00:00:00`);
    else if (key === "date_to") params.set(key, `${value}T23:59:59`);
    else params.set(key, value.trim());
  });
  Object.entries(extra).forEach(([key, value]) => params.set(key, value));
  const query = params.toString();
  return query ? `?${query}` : "";
}

function JsonBlock({ title, value }: { title: string; value: Record<string, unknown> | null }) {
  return (
    <div>
      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-white/50">{title}</p>
      <pre className="overflow-x-auto rounded-lg bg-black/40 p-3 text-xs text-white/80">
        {value ? JSON.stringify(value, null, 2) : "—"}
      </pre>
    </div>
  );
}

export default function AdminAuditPage() {
  const [actions, setActions] = useState<Record<string, string>>({});
  const [draft, setDraft] = useState<Filters>(EMPTY_FILTERS);
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<AuditPage | null>(null);
  const [openId, setOpenId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isExporting, setIsExporting] = useState(false);

  const load = useCallback(async () => {
    try {
      setIsLoading(true);
      setError("");
      const result = await adminFetch(
        `/admin/audit${buildQuery(filters, { page: String(page), page_size: String(PAGE_SIZE) })}`,
      );
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue.");
    } finally {
      setIsLoading(false);
    }
  }, [filters, page]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    adminFetch("/admin/audit/actions")
      .then((result) => setActions(result || {}))
      .catch(() => setActions({}));
  }, []);

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPage(1);
    setFilters(draft);
  }

  function resetFilters() {
    setDraft(EMPTY_FILTERS);
    setFilters(EMPTY_FILTERS);
    setPage(1);
  }

  async function exportCsv() {
    try {
      setIsExporting(true);
      setError("");
      const stamp = new Date().toISOString().slice(0, 10);
      await adminDownload(`/admin/audit/export.csv${buildQuery(filters)}`, `forgeai-audit-${stamp}.csv`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export impossible.");
    } finally {
      setIsExporting(false);
    }
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;
  const inputClass =
    "mt-1 w-full rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-sm text-white outline-none focus:border-red-300";

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <header className="border-b border-white/10 bg-white/5 px-6 py-4 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-red-300">ForgeAI Admin</p>
            <h1 className="text-2xl font-bold">Journal d&apos;audit</h1>
            <p className="text-sm text-white/50">
              Toutes les actions et connexions admin. Les entrées ne peuvent être ni modifiées ni supprimées.
            </p>
          </div>
          <nav className="flex flex-wrap items-center gap-3 text-sm">
            <Link
              href="/admin/dashboard"
              className="rounded-lg border border-white/10 px-4 py-2 text-white/80 transition hover:bg-white/10"
            >
              Dashboard
            </Link>
            <Link
              href="/admin/users"
              className="rounded-lg border border-white/10 px-4 py-2 text-white/80 transition hover:bg-white/10"
            >
              Users
            </Link>
            <button
              onClick={exportCsv}
              disabled={isExporting}
              className="rounded-lg bg-red-500 px-4 py-2 font-semibold text-white transition hover:bg-red-400 disabled:opacity-60"
            >
              {isExporting ? "Export..." : "Exporter en CSV"}
            </button>
          </nav>
        </div>
      </header>

      <section className="mx-auto max-w-7xl space-y-6 px-6 py-8">
        <form
          onSubmit={applyFilters}
          className="grid gap-4 rounded-xl border border-white/10 bg-white/5 p-4 md:grid-cols-3 lg:grid-cols-6"
        >
          <label className="text-sm text-white/70 lg:col-span-2">
            Action
            <select
              value={draft.action}
              onChange={(event) => setDraft({ ...draft, action: event.target.value })}
              className={inputClass}
            >
              <option value="">Toutes les actions</option>
              {Object.entries(actions).map(([code, label]) => (
                <option key={code} value={code} className="bg-slate-900">
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm text-white/70">
            Résultat
            <select
              value={draft.result}
              onChange={(event) => setDraft({ ...draft, result: event.target.value })}
              className={inputClass}
            >
              <option value="">Tous</option>
              {Object.entries(RESULTS).map(([code, { label }]) => (
                <option key={code} value={code} className="bg-slate-900">
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm text-white/70">
            Auteur (e-mail)
            <input
              value={draft.actor}
              onChange={(event) => setDraft({ ...draft, actor: event.target.value })}
              placeholder="alice@"
              className={inputClass}
            />
          </label>
          <label className="text-sm text-white/70">
            Du
            <input
              type="date"
              value={draft.date_from}
              onChange={(event) => setDraft({ ...draft, date_from: event.target.value })}
              className={inputClass}
            />
          </label>
          <label className="text-sm text-white/70">
            Au
            <input
              type="date"
              value={draft.date_to}
              onChange={(event) => setDraft({ ...draft, date_to: event.target.value })}
              className={inputClass}
            />
          </label>
          <div className="flex gap-3 md:col-span-3 lg:col-span-6">
            <button type="submit" className="rounded-lg bg-white/15 px-4 py-2 text-sm font-semibold hover:bg-white/25">
              Filtrer
            </button>
            <button
              type="button"
              onClick={resetFilters}
              className="rounded-lg border border-white/10 px-4 py-2 text-sm text-white/70 hover:bg-white/10"
            >
              Réinitialiser
            </button>
          </div>
        </form>

        {error && (
          <div className="rounded-xl border border-red-400/30 bg-red-500/10 p-4 text-sm text-red-200">{error}</div>
        )}

        <div className="overflow-hidden rounded-xl border border-white/10 bg-white/5">
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-3 text-sm text-white/60">
            <span>{data ? `${data.total} entrée${data.total > 1 ? "s" : ""}` : "—"}</span>
            {isLoading && <span>Chargement...</span>}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-white/5 text-xs uppercase tracking-wide text-white/50">
                <tr>
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Auteur</th>
                  <th className="px-4 py-3">Action</th>
                  <th className="px-4 py-3">Cible</th>
                  <th className="px-4 py-3">Résultat</th>
                  <th className="px-4 py-3">Adresse IP</th>
                </tr>
              </thead>
              <tbody>
                {data?.items.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-white/50">
                      Aucune entrée pour ces filtres.
                    </td>
                  </tr>
                )}
                {data?.items.map((entry) => {
                  const result = RESULTS[entry.result] ?? RESULTS.failure;
                  const isOpen = openId === entry.id;
                  return [
                    <tr
                      key={entry.id}
                      onClick={() => setOpenId(isOpen ? null : entry.id)}
                      className="cursor-pointer border-t border-white/5 hover:bg-white/5"
                    >
                      <td className="whitespace-nowrap px-4 py-3 text-white/70">{formatDate(entry.created_at)}</td>
                      <td className="px-4 py-3">{entry.actor_email || "—"}</td>
                      <td className="px-4 py-3">
                        {entry.action_label}
                        {entry.detail && (
                          <span className="block text-xs text-white/50">{DETAILS[entry.detail] ?? entry.detail}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-white/70">{entry.target_label || entry.target_id || "—"}</td>
                      <td className="px-4 py-3">
                        <span className={`rounded-full border px-2 py-0.5 text-xs ${result.className}`}>
                          {result.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-white/60">{entry.ip_address || "—"}</td>
                    </tr>,
                    isOpen && (
                      <tr key={`${entry.id}-detail`} className="border-t border-white/5 bg-black/20">
                        <td colSpan={6} className="space-y-3 px-4 py-4">
                          <div className="grid gap-4 md:grid-cols-2">
                            <JsonBlock title="Avant" value={entry.before} />
                            <JsonBlock title="Après" value={entry.after} />
                          </div>
                          <p className="text-xs text-white/50">
                            Navigateur : <span className="text-white/70">{entry.user_agent || "—"}</span>
                          </p>
                          <p className="text-xs text-white/50">
                            Code action : <span className="font-mono text-white/70">{entry.action}</span>
                            {entry.target_type && (
                              <>
                                {" "}· cible {entry.target_type} #{entry.target_id}
                              </>
                            )}
                          </p>
                        </td>
                      </tr>
                    ),
                  ];
                })}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between border-t border-white/10 px-4 py-3 text-sm">
            <button
              onClick={() => setPage((current) => Math.max(1, current - 1))}
              disabled={page <= 1 || isLoading}
              className="rounded-lg border border-white/10 px-3 py-1.5 hover:bg-white/10 disabled:opacity-40"
            >
              Précédent
            </button>
            <span className="text-white/60">
              Page {page} / {totalPages}
            </span>
            <button
              onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
              disabled={page >= totalPages || isLoading}
              className="rounded-lg border border-white/10 px-3 py-1.5 hover:bg-white/10 disabled:opacity-40"
            >
              Suivant
            </button>
          </div>
        </div>
      </section>
    </main>
  );
}
