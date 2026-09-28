"use client";

import { type ReactNode, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { adminFetch, adminLogout, getAdminToken, getAdminTokenExpiry } from "@/lib/admin-api";

import ConfirmDialog from "./ConfirmDialog";

// Sprint 7.3: the single frame of the admin console (sidebar + account),
// shared by every page except the login screen.
type NavItem = { href: string; label: string };
type NavSection = { title: string; items: NavItem[] };

export const NAV_SECTIONS: NavSection[] = [
  { title: "Pilotage", items: [{ href: "/admin/dashboard", label: "Tableau de bord" }] },
  {
    title: "Clients",
    items: [
      { href: "/admin/users", label: "Utilisateurs" },
      { href: "/admin/projects", label: "Projets" },
    ],
  },
  {
    title: "Intelligence",
    items: [
      { href: "/admin/analyses", label: "Analyses IA" },
      { href: "/admin/errors", label: "Erreurs" },
    ],
  },
  {
    title: "Plateforme",
    items: [
      { href: "/admin/health", label: "Santé du système" },
      { href: "/admin/audit", label: "Journal d'audit" },
    ],
  },
];

type CurrentAdmin = { email: string; full_name: string };

export default function AdminShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  // The login screen has no console around it (and no session yet).
  if (pathname === "/admin/login") return <>{children}</>;
  return <ConsoleFrame pathname={pathname}>{children}</ConsoleFrame>;
}

function ConsoleFrame({ pathname, children }: { pathname: string; children: ReactNode }) {
  const [admin, setAdmin] = useState<CurrentAdmin | null>(null);
  const [minutesLeft, setMinutesLeft] = useState<number | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  // Session guard: no token -> login; otherwise show who is signed in.
  useEffect(() => {
    if (!getAdminToken()) {
      adminLogout();
      return;
    }
    adminFetch("/admin/me")
      .then((data) => setAdmin(data))
      .catch(() => setAdmin(null)); // 401/403 already redirects to login
  }, []);

  // 15-minute admin token, no silent refresh: count down, then end the session.
  useEffect(() => {
    const tick = () => {
      const expiresAt = getAdminTokenExpiry();
      const left = expiresAt ? expiresAt - Date.now() : 0;
      if (left <= 0) {
        adminLogout();
        return;
      }
      setMinutesLeft(Math.ceil(left / 60_000));
    };
    const first = window.setTimeout(tick, 0);
    const timer = window.setInterval(tick, 15_000);
    return () => {
      window.clearTimeout(first);
      window.clearInterval(timer);
    };
  }, []);

  const isActive = (href: string) => pathname === href || pathname.startsWith(`${href}/`);

  const sidebar = (
    <nav aria-label="Navigation de la console" className="flex h-full flex-col gap-6 p-5 text-sm">
      <Link href="/admin/dashboard" className="block">
        <p className="text-xs font-semibold uppercase tracking-wide text-red-300">Console</p>
        <p className="text-lg font-bold">ForgeAI Admin</p>
      </Link>

      {NAV_SECTIONS.map((section) => (
        <div key={section.title}>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-white/40">{section.title}</p>
          <ul className="space-y-1">
            {section.items.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  onClick={() => setMenuOpen(false)}
                  aria-current={isActive(item.href) ? "page" : undefined}
                  className={`block rounded-lg px-3 py-2 transition ${
                    isActive(item.href) ? "bg-red-500/15 text-white" : "text-white/70 hover:bg-white/10 hover:text-white"
                  }`}
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      ))}

      <div className="mt-auto border-t border-white/10 pt-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-white/40">Mon compte</p>
        <p className="truncate text-white/80">{admin?.full_name || "Administrateur"}</p>
        <p className="truncate text-xs text-white/50">{admin?.email || "…"}</p>
        {minutesLeft !== null && (
          <p className={`mt-2 text-xs ${minutesLeft <= 2 ? "text-amber-300" : "text-white/40"}`}>
            Session : {minutesLeft} min restante{minutesLeft > 1 ? "s" : ""}
          </p>
        )}
        <button
          type="button"
          onClick={() => adminLogout()}
          className="mt-3 w-full rounded-lg border border-red-400/30 bg-red-500/10 px-3 py-2 text-red-200 transition hover:bg-red-500/20"
        >
          Déconnexion
        </button>
      </div>
    </nav>
  );

  return (
    <div className="min-h-screen bg-slate-950 text-white lg:flex">
      {/* Desktop: fixed sidebar. */}
      <aside className="hidden w-64 shrink-0 border-r border-white/10 bg-white/[0.03] lg:sticky lg:top-0 lg:block lg:h-screen">
        {sidebar}
      </aside>

      {/* Mobile: top bar + drawer. */}
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3 lg:hidden">
        <p className="font-bold">ForgeAI Admin</p>
        <button
          type="button"
          onClick={() => setMenuOpen((open) => !open)}
          aria-expanded={menuOpen}
          className="rounded-lg border border-white/10 px-3 py-1.5 text-sm"
        >
          Menu
        </button>
      </div>
      {menuOpen && <aside className="border-b border-white/10 bg-slate-900 lg:hidden">{sidebar}</aside>}

      <main className="min-w-0 flex-1">{children}</main>
      <ConfirmDialog />
    </div>
  );
}
