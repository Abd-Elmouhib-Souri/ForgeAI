"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useForgeLanguage } from "@/lib/language-context";
import ForgeLanguageSwitch from "@/components/forge/ForgeLanguageSwitch";

type ActivePage = "dashboard" | "projects" | "new-project" | "none";

type ForgeAppNavbarProps = {
  active?: ActivePage;
};

const copy = {
  fr: {
    dashboard: "Dashboard",
    projects: "Mes projets",
    newProject: "Nouveau projet",
    logout: "Déconnexion",
  },
  en: {
    dashboard: "Dashboard",
    projects: "My projects",
    newProject: "New project",
    logout: "Logout",
  },
};

export default function ForgeAppNavbar({
  active = "none",
}: ForgeAppNavbarProps) {
  const router = useRouter();
  const { logout } = useAuth();
  const { lang } = useForgeLanguage();

  const t = copy[lang];

  const handleLogout = async () => {
    await logout();
    router.replace("/login");
  };

  const navButtonClass = (page: ActivePage) =>
    active === page
      ? "forge-btn forge-btn-primary"
      : "forge-btn forge-btn-secondary";

  return (
    <nav className="forge-navbar">
      <Link href="/" className="forge-brand">
        <span className="forge-logo">✦</span>
        <span>ForgeAI</span>
      </Link>

      <div className="forge-nav-pill">
        <Link href="/dashboard" className={navButtonClass("dashboard")}>
          {t.dashboard}
        </Link>

        <Link href="/projects" className={navButtonClass("projects")}>
          {t.projects}
        </Link>

        <Link
          href="/projects/new"
          className={
            active === "new-project"
              ? "forge-btn forge-btn-primary"
              : "forge-btn forge-btn-dark"
          }
        >
          {t.newProject}
        </Link>

        <ForgeLanguageSwitch />

        <button
          type="button"
          onClick={handleLogout}
          className="forge-btn border border-red-200 bg-red-50 text-red-600 hover:bg-red-100"
        >
          {t.logout}
        </button>
      </div>
    </nav>
  );
}