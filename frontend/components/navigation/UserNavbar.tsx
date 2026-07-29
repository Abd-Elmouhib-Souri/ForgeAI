"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

type UserNavbarProps = {
  title: string;
  subtitle?: string;
  showBack?: boolean;
};

export default function UserNavbar({
  title,
  subtitle,
  showBack = true,
}: UserNavbarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  const isProjectsActive =
    pathname === "/projects" ||
    (pathname.startsWith("/projects/") && pathname !== "/projects/new");

  return (
    <header className="border-b border-white/10 bg-white/5 px-6 py-4 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-sm font-medium text-cyan-300">DotJcom ForgeAI</p>
          <h1 className="text-2xl font-bold text-white">{title}</h1>

          {subtitle && <p className="mt-1 text-sm text-white/50">{subtitle}</p>}

          {user?.email && (
            <p className="mt-1 text-xs text-white/40">
              Connecté : {user.email}
            </p>
          )}
        </div>

        <nav className="flex flex-wrap items-center gap-3 text-sm">
          {showBack && (
            <button
              type="button"
              onClick={() => router.back()}
              className="rounded-lg border border-white/10 px-4 py-2 text-white/80 transition hover:bg-white/10"
            >
              Retour
            </button>
          )}

          <NavLink href="/dashboard" active={pathname === "/dashboard"}>
            Dashboard
          </NavLink>

          <NavLink href="/projects" active={isProjectsActive}>
            Mes projets
          </NavLink>

          <NavLink href="/projects/new" active={pathname === "/projects/new"}>
            Nouveau projet
          </NavLink>

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
  );
}

function NavLink({
  href,
  active,
  children,
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={
        active
          ? "rounded-lg bg-cyan-500 px-4 py-2 font-medium text-white"
          : "rounded-lg border border-white/10 px-4 py-2 text-white/80 transition hover:bg-white/10"
      }
    >
      {children}
    </Link>
  );
}