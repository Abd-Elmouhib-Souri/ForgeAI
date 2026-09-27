"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { adminFetch, removeAdminToken } from "@/lib/admin-api";

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

export default function AdminUsersPage() {
  const router = useRouter();

  const [users, setUsers] = useState<AdminUser[]>([]);
  const [currentAdmin, setCurrentAdmin] = useState<CurrentAdmin | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const [filter, setFilter] = useState<
    "all" | "verified" | "unverified" | "inactive" | "admins"
  >("all");

  const [showCreateAdmin, setShowCreateAdmin] = useState(false);
  const [newAdminEmail, setNewAdminEmail] = useState("");
  const [newAdminName, setNewAdminName] = useState("");
  const [newAdminPassword, setNewAdminPassword] = useState("");

  const loadCurrentAdmin = useCallback(async () => {
    try {
      const data = await adminFetch("/admin/me");
      setCurrentAdmin(data);
    } catch {
      setCurrentAdmin(null);
    }
  }, []);

  const loadUsers = useCallback(async () => {
    try {
      setIsLoading(true);
      setError("");

      const data = await adminFetch("/admin/users");
      setUsers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const refreshPageData = useCallback(async () => {
    await Promise.all([loadCurrentAdmin(), loadUsers()]);
  }, [loadCurrentAdmin, loadUsers]);

  async function toggleUserStatus(user: AdminUser) {
    try {
      setActionLoadingId(user.id);
      setError("");
      setMessage("");

      // Sensitive: the admin API requires a fresh 2FA code (Sprint 7.1).
      await adminFetch(`/admin/users/${user.id}/status`, {
        confirm: true,
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
        confirm: true,
        method: "PATCH",
        body: JSON.stringify({
          role: newRole,
        }),
      });

      setMessage(`Rôle de ${user.email} mis à jour.`);
      await loadUsers();
    } catch (err) {
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
    const confirmed = window.confirm(
      `Supprimer définitivement le compte ${user.email} ?\n\nCette action est irréversible.`
    );

    if (!confirmed) return;

    try {
      setActionLoadingId(user.id);
      setError("");
      setMessage("");

      await adminFetch(`/admin/users/${user.id}`, {
        confirm: true,
        method: "DELETE",
      });

      setMessage(`Compte ${user.email} supprimé avec succès.`);
      await refreshPageData();
    } catch (err) {
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
        confirm: true,
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
      setError(err instanceof Error ? err.message : "Erreur création admin.");
    } finally {
      setActionLoadingId(null);
    }
  }

  function handleLogout() {
    removeAdminToken();
    router.replace("/admin/login");
  }

  useEffect(() => {
    void refreshPageData();
  }, [refreshPageData]);

  const filteredUsers = useMemo(() => {
    if (filter === "verified") {
      return users.filter((user) => user.is_email_verified);
    }

    if (filter === "unverified") {
      return users.filter((user) => !user.is_email_verified);
    }

    if (filter === "inactive") {
      return users.filter((user) => !user.is_active);
    }

    if (filter === "admins") {
      return users.filter((user) => user.role === "admin");
    }

    return users;
  }, [users, filter]);

  const stats = useMemo(() => {
    return {
      total: users.length,
      verified: users.filter((user) => user.is_email_verified).length,
      unverified: users.filter((user) => !user.is_email_verified).length,
      inactive: users.filter((user) => !user.is_active).length,
      admins: users.filter((user) => user.role === "admin").length,
    };
  }, [users]);

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <header className="border-b border-white/10 bg-white/5 px-6 py-4 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-medium text-red-300">ForgeAI Admin</p>
            <h1 className="text-2xl font-bold">Gestion utilisateurs</h1>
            {currentAdmin && (
              <p className="mt-1 text-xs text-white/40">
                Connecté : {currentAdmin.email}
              </p>
            )}
          </div>

          <nav className="flex flex-wrap items-center gap-3 text-sm">
            <button
              type="button"
              onClick={() => router.back()}
              className="rounded-lg border border-white/10 px-4 py-2 text-white/80 transition hover:bg-white/10"
            >
              Retour
            </button>

            <Link
              href="/admin/dashboard"
              className="rounded-lg border border-white/10 px-4 py-2 text-white/80 transition hover:bg-white/10"
            >
              Dashboard
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

            <button
              type="button"
              onClick={handleLogout}
              className="rounded-lg border border-red-400/30 bg-red-500/10 px-4 py-2 text-red-200 transition hover:bg-red-500/20"
            >
              Déconnexion
            </button>
          </nav>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-6 py-8">
        <div className="grid gap-4 md:grid-cols-5">
          <StatCard title="Total" value={stats.total} />
          <StatCard title="Admins" value={stats.admins} />
          <StatCard title="Vérifiés" value={stats.verified} />
          <StatCard title="Non vérifiés" value={stats.unverified} />
          <StatCard title="Inactifs" value={stats.inactive} />
        </div>

        <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-lg font-semibold">Liste des utilisateurs</h2>
              <p className="mt-1 text-sm text-white/50">
                Gestion des comptes, admins, vérification email, rôles et statut.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => setShowCreateAdmin(true)}
                className="rounded-lg bg-red-500 px-4 py-2 text-xs font-semibold text-white transition hover:bg-red-400"
              >
                + Ajouter admin
              </button>

              <FilterButton
                label="Tous"
                active={filter === "all"}
                onClick={() => setFilter("all")}
              />

              <FilterButton
                label="Admins"
                active={filter === "admins"}
                onClick={() => setFilter("admins")}
              />

              <FilterButton
                label="Vérifiés"
                active={filter === "verified"}
                onClick={() => setFilter("verified")}
              />

              <FilterButton
                label="Non vérifiés"
                active={filter === "unverified"}
                onClick={() => setFilter("unverified")}
              />

              <FilterButton
                label="Inactifs"
                active={filter === "inactive"}
                onClick={() => setFilter("inactive")}
              />
            </div>
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

                <button
                  type="button"
                  onClick={() => setShowCreateAdmin(false)}
                  className="rounded-lg border border-white/10 px-3 py-2 text-xs text-white/70 transition hover:bg-white/10"
                >
                  Fermer
                </button>
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
                  <button
                    type="submit"
                    disabled={actionLoadingId === -1}
                    className="w-full rounded-lg bg-red-500 px-4 py-3 text-sm font-semibold text-white transition hover:bg-red-400 disabled:opacity-50"
                  >
                    {actionLoadingId === -1 ? "Création..." : "Créer admin"}
                  </button>
                </div>
              </form>
            </div>
          )}

          {isLoading ? (
            <div className="mt-6 rounded-xl border border-white/10 bg-white/5 p-6 text-white/60">
              Chargement des utilisateurs...
            </div>
          ) : (
            <div className="mt-6 overflow-x-auto">
              <table className="w-full min-w-[1250px] border-separate border-spacing-y-3 text-left text-sm">
                <thead className="text-white/50">
                  <tr>
                    <th className="px-4 py-2">Utilisateur</th>
                    <th className="px-4 py-2">Rôle</th>
                    <th className="px-4 py-2">Email</th>
                    <th className="px-4 py-2">Statut</th>
                    <th className="px-4 py-2">Projets</th>
                    <th className="px-4 py-2">Créé le</th>
                    <th className="px-4 py-2 text-right">Actions</th>
                  </tr>
                </thead>

                <tbody>
                  {filteredUsers.map((user) => {
                    const isBusy = actionLoadingId === user.id;
                    const isCurrentAdmin = currentAdmin?.id === user.id;
                    const canDelete = user.project_count === 0 && !isCurrentAdmin;

                    return (
                      <tr key={user.id} className="rounded-xl bg-white/5">
                        <td className="rounded-l-xl px-4 py-4">
                          <div className="font-medium">{user.full_name}</div>
                          <div className="text-xs text-white/50">{user.email}</div>

                          {isCurrentAdmin && (
                            <div className="mt-1 text-xs text-red-300">
                              Vous
                            </div>
                          )}
                        </td>

                        <td className="px-4 py-4">
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
                                {role}
                              </option>
                            ))}
                          </select>
                        </td>

                        <td className="px-4 py-4">
                          {user.is_email_verified ? (
                            <Badge color="green">Vérifié</Badge>
                          ) : (
                            <Badge color="yellow">Non vérifié</Badge>
                          )}
                        </td>

                        <td className="px-4 py-4">
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

                        <td className="px-4 py-4 font-semibold">
                          {user.project_count}
                        </td>

                        <td className="px-4 py-4 text-white/60">
                          {formatDate(user.created_at)}
                        </td>

                        <td className="rounded-r-xl px-4 py-4">
                          <div className="flex justify-end gap-2">
                            <Link
                              href={`/admin/users/${user.id}`}
                              className="rounded-lg border border-white/10 px-3 py-2 text-xs text-white/80 transition hover:bg-white/10"
                            >
                              Voir
                            </Link>

                            {!user.is_email_verified && (
                              <button
                                disabled={isBusy}
                                onClick={() => resendVerification(user)}
                                className="rounded-lg border border-cyan-400/30 bg-cyan-500/10 px-3 py-2 text-xs text-cyan-200 transition hover:bg-cyan-500/20 disabled:opacity-50"
                              >
                                Renvoyer email
                              </button>
                            )}

                            {canDelete && (
                              <button
                                disabled={isBusy}
                                onClick={() => deleteUser(user)}
                                className="rounded-lg border border-red-500/40 bg-red-600/10 px-3 py-2 text-xs text-red-200 transition hover:bg-red-600/20 disabled:opacity-50"
                              >
                                Supprimer
                              </button>
                            )}

                            <button
                              disabled={isBusy || isCurrentAdmin}
                              onClick={() => toggleUserStatus(user)}
                              className={
                                user.is_active
                                  ? "rounded-lg border border-red-400/30 bg-red-500/10 px-3 py-2 text-xs text-red-200 transition hover:bg-red-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                                  : "rounded-lg border border-emerald-400/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-200 transition hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                              }
                            >
                              {user.is_active ? "Désactiver" : "Activer"}
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              {filteredUsers.length === 0 && (
                <div className="rounded-xl border border-white/10 bg-white/5 p-6 text-center text-white/50">
                  Aucun utilisateur trouvé.
                </div>
              )}
            </div>
          )}
        </div>
      </section>
    </main>
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