"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useForgeLanguage } from "@/lib/language-context";
import { forgeCommonCopy } from "@/components/forge/forge-copy";
import ForgeLanguageSwitch from "@/components/forge/ForgeLanguageSwitch";

type ForgeNavbarProps = {
  active?: "dashboard" | "projects" | "new-project" | "none";
  showAuthActions?: boolean;
};

export default function ForgeNavbar({
  active = "none",
  showAuthActions = true,
}: ForgeNavbarProps) {
  const router = useRouter();
  const { logout } = useAuth();
  const { lang } = useForgeLanguage();

  const t = forgeCommonCopy[lang];

  const handleLogout = async () => {
    await logout();
    router.replace("/login");
  };

  return (
    <nav className="forge-navbar">
      <Link href="/" className="forge-brand">
        <span className="forge-logo">✦</span>
        <span>{t.brand}</span>
      </Link>

      <div className="forge-nav-pill">
        <Link
          href="/dashboard"
          className={
            active === "dashboard"
              ? "forge-btn forge-btn-primary"
              : "forge-btn forge-btn-secondary"
          }
        >
          {t.dashboard}
        </Link>

        <Link
          href="/projects"
          className={
            active === "projects"
              ? "forge-btn forge-btn-primary"
              : "forge-btn forge-btn-secondary"
          }
        >
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

        {showAuthActions && (
          <button
            type="button"
            onClick={handleLogout}
            className="forge-btn border border-red-200 bg-red-50 text-red-600 hover:bg-red-100"
          >
            {t.logout}
          </button>
        )}
      </div>
    </nav>
  );
}