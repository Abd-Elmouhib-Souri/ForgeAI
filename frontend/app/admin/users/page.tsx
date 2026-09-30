"use client";

import { FormEvent, useCallback, useState } from "react";
import { Download, Eye, Mail, Plus, Power, Search, Trash2, X } from "lucide-react";
import { Button, ButtonLink } from "@/app/admin/_components/Button";
import FilterTabs from "@/app/admin/_components/FilterTabs";
import { adminDownload, adminFetch, isAdminActionCancelled } from "@/lib/admin-api";
import { buildListQuery, type Page } from "@/app/admin/_components/listQuery";
import Pagination from "@/app/admin/_components/Pagination";
import type { AdminStats } from "@/app/admin/_components/stats";
import { useAdminResource } from "@/app/admin/_components/useAdminResource";
import { ROLE_LABELS, roleLabel } from "@/app/admin/_components/labels";
import AdminPageHeader from "@/app/admin/_components/AdminPageHeader";

type AdminUser = {
  id: number;
  email: string;
  full_name: string;
  role: "admin" | "entrepreneur" | "student" | "consultant" | string;
  is_active: boolean;
  is_email_verified: boolean;
  is_two_factor_enabled: boolean;
  created_at: string;
  project_count: number;
};

type CurrentAdmin = {
  id: number;
  email: string;
  full_name: string;
  role: string;
};

const roles = ["admin", "entrepreneur", "student", "consultant"];

// Sprint 7.4: each quick filter is a query sent to the API (no browser filtering).
type QuickFilter = "all" | "verified" | "unverified" | "inactive" | "admins";
const QUICK_FILTER_TABS: { value: QuickFilter; label: string }[] = [
  { value: "all", label: "Tous" },
  { value: "admins", label: "Administrateurs" },
  { value: "verified", label: "Vérifiés" },
  { value: "unverified", label: "Non vérifiés" },
  { value: "inactive", label: "Inactifs" },
];
const QUICK_FILTERS: Record<QuickFilter, Record<string, string>> = {
  all: {},
  admins: { role: "admin" },
  verified: { verified: "true" },
  unverified: { verified: "false" },
  inactive: { status: "inactive" },
};

const SORTS: Record<string, { label: string; sort: string; order: "asc" | "desc" }> = {
  recent: { label: "Plus récents", sort: "created_at", order: "desc" },
  oldest: { label: "Plus anciens", sort: "created_at", order: "asc" },
  email: { label: "E-mail (A → Z)", sort: "email", order: "asc" },
  name: { label: "Nom (A → Z)", sort: "full_name", order: "asc" },
  projects: { label: "Plus de projets", sort: "project_count", order: "desc" },
};

const PAGE_SIZE = 25;

export default function AdminUsersPage() {
  // The signed-in admin (to lock their own role / status controls).
  const me = useAdminResource<CurrentAdmin>("/admin/me");
  const currentAdmin = me.data;
  const reloadMe = me.reload;

  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const [filter, setFilter] = useState<QuickFilter>("all");
  const [searchDraft, setSearchDraft] = useState("");
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState("recent");
  const [page, setPage] = useState(1);

  // The screen's filters: the same object drives the list and the CSV export.
  const filters = {
    ...QUICK_FILTERS[filter],
    search,
    sort: SORTS[sortKey].sort,
    order: SORTS[sortKey].order,
  };
  const list = useAdminResource<Page<AdminUser>>(
    `/admin/users${buildListQuery({ ...filters, page, page_size: PAGE_SIZE })}`,
  );
  const stats = useAdminResource<AdminStats>("/admin/stats");
  const users = list.data?.items ?? [];
  const reloadList = list.reload;
  const reloadStats = stats.reload;

  const [showCreateAdmin, setShowCreateAdmin] = useState(false);
  const [newAdminEmail, setNewAdminEmail] = useState("");
  const [newAdminName, setNewAdminName] = useState("");
  const [newAdminPassword, setNewAdminPassword] = useState("");

  // After an action: reload the current page and the counters.
  const loadUsers = useCallback(async () => {
    reloadList();
    reloadStats();
  }, [reloadList, reloadStats]);

  const refreshPageData = useCallback(async () => {
    reloadMe();
    await loadUsers();
  }, [reloadMe, loadUsers]);

  function changeFilter(next: QuickFilter) {
    setFilter(next);
    setPage(1); // a new filter starts at the first page
  }

  function applySearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSearch(searchDraft);
    setPage(1);
  }

  async function exportCsv() {
    try {
      setError("");
      await adminDownload(`/admin/users/export.csv${buildListQuery(filters)}`, "forgeai-utilisateurs.csv");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export impossible.");
    }
  }

  async function toggleUserStatus(user: AdminUser) {
    try {
      setActionLoadingId(user.id);
      setError("");
      setMessage("");

      // Sensitive: the admin API requires a fresh 2FA code (Sprint 7.1).
      await adminFetch(`/admin/users/${user.id}/status`, {
        confirm: user.is_active
          ? `Désactiver le compte ${user.email} ?\nLa personne ne pourra plus se connecter.`
          : `Réactiver le compte ${user.email} ?`,
        method: "PATCH",
        body: JSON.stringify({
          is_active: !user.is_active,
        }),
      });

      setMessage(
        user.is_active
          ? `Compte ${user.email} désactivé.`
          : `Compte ${user.email} activé.`
      );

      await loadUsers();
    } catch (err) {
      if (isAdminActionCancelled(err)) return;
      setError(err instanceof Error ? err.message : "Erreur action utilisateur.");
    } finally {
      setActionLoadingId(null);
    }
  }

  async function updateUserRole(user: AdminUser, newRole: string) {
    try {
      setActionLoadingId(user.id);
      setError("");
      setMessage("");

      await adminFetch(`/admin/users/${user.id}/role`, {
        confirm: `Changer le rôle de ${user.email} : ${roleLabel(user.role)} → ${roleLabel(newRole)} ?`,
        method: "PATCH",
        body: JSON.stringify({
          role: newRole,
        }),
      });

      setMessage(`Rôle de ${user.email} mis à jour.`);
      await loadUsers();
    } catch (err) {
      if (isAdminActionCancelled(err)) return;
      setError(err instanceof Error ? err.message : "Erreur changement rôle.");
    } finally {
      setActionLoadingId(null);
    }
  }

  async function resendVerification(user: AdminUser) {
    try {
      setActionLoadingId(user.id);
      setError("");
      setMessage("");

      const data = await adminFetch(
        `/admin/users/${user.id}/resend-verification`,
        {
          method: "POST",
        }
      );

      setMessage(data.message || `Email de vérification renvoyé à ${user.email}.`);
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur envoi email.");
    } finally {
      setActionLoadingId(null);
    }
  }

  async function deleteUser(user: AdminUser) {
    try {
      setActionLoadingId(user.id);
      setError("");
      setMessage("");

      // One dialog: what is deleted + the 2FA code (no window.confirm).
      await adminFetch(`/admin/users/${user.id}`, {
        confirm: `Supprimer définitivement le compte ${user.email} ?\nCette action est irréversible.`,
        method: "DELETE",
      });

      setMessage(`Compte ${user.email} supprimé avec succès.`);
      await refreshPageData();
    } catch (err) {
      if (isAdminActionCancelled(err)) return;
      setError(
        err instanceof Error ? err.message : "Erreur suppression utilisateur."
      );
    } finally {
      setActionLoadingId(null);
    }
  }

  async function createAdmin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    try {
      setError("");
      setMessage("");
      setActionLoadingId(-1);

      const data = await adminFetch("/admin/users/create-admin", {
        confirm: `Créer le compte administrateur ${newAdminEmail} ?\nIl aura accès à toute la console.`,
        method: "POST",
        body: JSON.stringify({
          email: newAdminEmail,
          full_name: newAdminName,
          password: newAdminPassword,
        }),
      });

      setMessage(
        data.message ||
          `Compte admin ${newAdminEmail} créé. Email de vérification envoyé.`
      );

      setNewAdminEmail("");
      setNewAdminName("");
      setNewAdminPassword("");
      setShowCreateAdmin(false);

      await loadUsers();
    } catch (err) {
      if (isAdminActionCancelled(err)) return;
      setError(err instanceof Error ? err.message : "Erreur création admin.");
    } finally {
      setActionLoadingId(null);
    }
  }

  return (
    <div>
      <AdminPageHeader title="Utilisateurs" subtitle="Comptes clients et administrateurs." />

      <section className="mx-auto max-w-7xl px-6 py-8">
        <div className="grid gap-4 md:grid-cols-5">
          {/* Counters of the whole platform, computed by the database. */}
          <StatCard title="Total" value={stats.data?.users.total ?? 0} />
          <StatCard title="Administrateurs" value={stats.data?.users.admins ?? 0} />
          <StatCard title="Vérifiés" value={stats.data?.users.verified ?? 0} />
          <StatCard title="Non vérifiés" value={stats.data?.users.unverified ?? 0} />
          <StatCard title="Inactifs" value={stats.data?.users.inactive ?? 0} />
        </div>

        <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-lg font-semibold">Liste des utilisateurs</h2>
              <p className="mt-1 text-sm text-white/50">
                Gestion des comptes, admins, vérification email, rôles et statut.
              </p>
            </div>

            {/* Actions first, then the filters on their own line. */}
            <div className="flex flex-col items-start gap-3 md:items-end">
              <div className="flex flex-wrap items-center gap-2">
                <Button variant="primary" size="sm" icon={Plus} onClick={() => setShowCreateAdmin(true)}>
                  Ajouter un admin
                </Button>
                <Button size="sm" icon={Download} onClick={exportCsv}>
                  Exporter en CSV
                </Button>
              </div>
              <FilterTabs label="Filtrer les utilisateurs" options={QUICK_FILTER_TABS} value={filter} onChange={changeFilter} />
            </div>
          </div>

          {/* Search and sort run on the server (Sprint 7.4). */}
          <form onSubmit={applySearch} className="mt-5 flex flex-col gap-3 md:flex-row">
            <input
              value={searchDraft}
              onChange={(event) => setSearchDraft(event.target.value)}
              placeholder="Rechercher par e-mail ou nom..."
              className="w-full rounded-lg border border-white/10 bg-slate-900 px-4 py-2.5 text-sm outline-none focus:border-red-300 md:max-w-md"
            />
            <Button type="submit" icon={Search}>
              Rechercher
            </Button>
            <select
              value={sortKey}
              onChange={(event) => {
                setSortKey(event.target.value);
                setPage(1);
              }}
              aria-label="Trier"
              className="rounded-lg border border-white/10 bg-slate-900 px-3 py-2.5 text-sm md:ml-auto"
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

          {showCreateAdmin && (
            <div className="mt-5 rounded-2xl border border-red-400/20 bg-red-500/10 p-5">
              <div className="mb-4 flex items-center justify-between gap-4">
                <div>
                  <h3 className="text-lg font-semibold">
                    Ajouter un administrateur
                  </h3>
                  <p className="mt-1 text-sm text-white/50">
                    Le nouvel admin devra vérifier son email avant de se connecter.
                  </p>
                </div>

                <Button variant="ghost" size="sm" icon={X} onClick={() => setShowCreateAdmin(false)}>
                  Fermer
                </Button>
              </div>

              <form onSubmit={createAdmin} className="grid gap-4 md:grid-cols-4">
                <div>
                  <label className="text-xs text-white/60">Nom complet</label>
                  <input
                    type="text"
                    value={newAdminName}
                    onChange={(event) => setNewAdminName(event.target.value)}
                    required
                    minLength={2}
                    placeholder="Admin ForgeAI"
                    className="mt-1 w-full rounded-lg border border-white/10 bg-slate-900 px-4 py-3 text-sm outline-none focus:border-red-300"
                  />
                </div>

                <div>
                  <label className="text-xs text-white/60">Email admin</label>
                  <input
                    type="email"
                    value={newAdminEmail}
                    onChange={(event) => setNewAdminEmail(event.target.value)}
                    required
                    placeholder="admin@example.com"
                    className="mt-1 w-full rounded-lg border border-white/10 bg-slate-900 px-4 py-3 text-sm outline-none focus:border-red-300"
                  />
                </div>

                <div>
                  <label className="text-xs text-white/60">
                    Mot de passe temporaire
                  </label>
                  <input
                    type="password"
                    value={newAdminPassword}
                    onChange={(event) => setNewAdminPassword(event.target.value)}
                    required
                    minLength={12}
                    placeholder="Minimum 12 caractères"
                    className="mt-1 w-full rounded-lg border border-white/10 bg-slate-900 px-4 py-3 text-sm outline-none focus:border-red-300"
                  />
                </div>

                <div className="flex items-end">
                  <Button type="submit" variant="primary" block loading={actionLoadingId === -1}>
                    {actionLoadingId === -1 ? "Création..." : "Créer admin"}
                  </Button>
                </div>
              </form>
            </div>
          )}

          {!list.data ? (
            <div className="mt-6 rounded-xl border border-white/10 bg-white/5 p-6 text-white/60">
              Chargement des utilisateurs...
            </div>
          ) : (
            <div className="mt-6 overflow-x-auto">
              <table className="w-full min-w-[960px] border-separate border-spacing-y-3 text-left text-sm">
                <thead className="text-white/50">
                  <tr>
                    <th className="px-3 py-2">Utilisateur</th>
                    <th className="px-3 py-2">Rôle</th>
                    <th className="px-3 py-2">Email</th>
                    <th className="px-3 py-2">Statut</th>
                    <th className="px-3 py-2">Projets</th>
                    <th className="px-3 py-2">Créé le</th>
                    <th className="px-3 py-2 text-right">Actions</th>
                  </tr>
                </thead>

                <tbody>
                  {users.map((user) => {
                    const isBusy = actionLoadingId === user.id;
                    const isCurrentAdmin = currentAdmin?.id === user.id;
                    const canDelete = user.project_count === 0 && !isCurrentAdmin;

                    return (
                      <tr key={user.id} className="rounded-xl bg-white/5">
                        <td className="rounded-l-xl px-3 py-4">
                          <div className="font-medium">{user.full_name}</div>
                          <div className="text-xs text-white/50">{user.email}</div>

                          {isCurrentAdmin && (
                            <div className="mt-1 text-xs text-red-300">
                              Vous
                            </div>
                          )}
                        </td>

                        <td className="px-3 py-4">
                          <select
                            value={user.role}
                            // An admin cannot change their own role from here.
                            disabled={isBusy || isCurrentAdmin}
                            onChange={(event) =>
                              updateUserRole(user, event.target.value)
                            }
                            className="rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-xs text-white outline-none"
                          >
                            {roles.map((role) => (
                              <option key={role} value={role}>
                                {ROLE_LABELS[role] ?? role}
                              </option>
                            ))}
                          </select>
                        </td>

                        <td className="px-3 py-4">
                          {user.is_email_verified ? (
                            <Badge color="green">Vérifié</Badge>
                          ) : (
                            <Badge color="yellow">Non vérifié</Badge>
                          )}
                        </td>

                        <td className="px-3 py-4">
                          {user.is_active ? (
                            <Badge color="green">Actif</Badge>
                          ) : (
                            <Badge color="red">Désactivé</Badge>
                          )}

                          {user.is_two_factor_enabled && (
                            <span className="ml-2">
                              <Badge color="blue">2FA</Badge>
                            </span>
                          )}
                        </td>

                        <td className="px-3 py-4 font-semibold">
                          {user.project_count}
                        </td>

                        <td className="px-3 py-4 text-white/60">
                          {formatDate(user.created_at)}
                        </td>

                        <td className="rounded-r-xl px-3 py-4">
                          {/* Flex + gap: buttons wrap cleanly, never on top of each other. */}
                          <div className="flex flex-wrap justify-end gap-2">
                            <ButtonLink href={`/admin/users/${user.id}`} size="sm" icon={Eye}>
                              Voir
                            </ButtonLink>

                            {!user.is_email_verified && (
                              <Button variant="info" size="sm" icon={Mail} disabled={isBusy} onClick={() => resendVerification(user)}>
                                Renvoyer l&apos;e-mail
                              </Button>
                            )}

                            {canDelete && (
                              <Button variant="danger" size="sm" icon={Trash2} disabled={isBusy} onClick={() => deleteUser(user)}>
                                Supprimer
                              </Button>
                            )}

                            <Button
                              variant={user.is_active ? "danger" : "success"}
                              size="sm"
                              icon={Power}
                              disabled={isBusy || isCurrentAdmin}
                              title={isCurrentAdmin ? "Vous ne pouvez pas désactiver votre propre compte." : undefined}
                              onClick={() => toggleUserStatus(user)}
                            >
                              {user.is_active ? "Désactiver" : "Activer"}
                            </Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              {list.data.total === 0 && (
                <div className="rounded-xl border border-white/10 bg-white/5 p-6 text-center text-white/50">
                  Aucun utilisateur trouvé.
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

function StatCard({ title, value }: { title: string; value: number }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
      <p className="text-sm text-white/50">{title}</p>
      <p className="mt-2 text-3xl font-bold">{value}</p>
    </div>
  );
}

function Badge({
  children,
  color,
}: {
  children: React.ReactNode;
  color: "green" | "red" | "yellow" | "blue";
}) {
  const classes = {
    green: "border-emerald-400/30 bg-emerald-500/10 text-emerald-200",
    red: "border-red-400/30 bg-red-500/10 text-red-200",
    yellow: "border-yellow-400/30 bg-yellow-500/10 text-yellow-200",
    blue: "border-cyan-400/30 bg-cyan-500/10 text-cyan-200",
  };

  return (
    <span className={`rounded-full border px-3 py-1 text-xs ${classes[color]}`}>
      {children}
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