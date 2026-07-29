"use client";

import Link from "next/link";
import ProtectedPage from "@/components/auth/ProtectedPage";
import { useAuth } from "@/lib/auth-context";
import { useForgeLanguage } from "@/lib/language-context";
import ForgeAppNavbar from "@/components/forge/ForgeAppNavbar";

const content = {
  fr: {
    welcome: "Bienvenue",
    hello: "Bonjour",
    user: "Utilisateur",
    subtitle:
      "Gérez vos projets, lancez vos analyses IA et consultez vos rapports ForgeAI depuis un seul espace.",
    connected: "Connecté",
    secure: "Espace personnel sécurisé",
    projects: "Mes projets",
    projectsText:
      "Consultez uniquement vos idées, rapports et analyses sauvegardés.",
    newIdea: "Nouvelle idée",
    newIdeaText: "Créez une idée startup et lancez une analyse IA complète.",
    personal: "Espace personnel",
    personalText:
      "Chaque compte voit seulement ses propres projets grâce à l’isolation utilisateur.",
    modules: "Modules",
    agents: "Agents IA",
    deliverables: "Livrables",
    languages: "Langues",
  },
  en: {
    welcome: "Welcome",
    hello: "Hello",
    user: "User",
    subtitle:
      "Manage your projects, launch AI analyses and access ForgeAI reports from one workspace.",
    connected: "Connected",
    secure: "Secure personal workspace",
    projects: "My projects",
    projectsText: "Access only your saved ideas, reports and analyses.",
    newIdea: "New idea",
    newIdeaText: "Create a startup idea and launch a complete AI analysis.",
    personal: "Personal space",
    personalText:
      "Each account only sees its own projects thanks to user isolation.",
    modules: "Modules",
    agents: "AI Agents",
    deliverables: "Deliverables",
    languages: "Languages",
  },
};

export default function DashboardPage() {
  const { user } = useAuth();
  const { lang } = useForgeLanguage();
  const t = content[lang];

  return (
    <ProtectedPage>
      <main className="forge-page min-h-screen">
        <ForgeAppNavbar active="dashboard" />

        <section className="forge-section-sm">
          <div className="forge-panel p-8">
            <span className="forge-eyebrow">👋 {t.welcome}</span>
            <h1 className="forge-title mt-2">
              {t.hello},{" "}
              <span className="forge-gradient-text">
                {user?.full_name || t.user}
              </span>
            </h1>
            <p className="forge-subtitle">{t.subtitle}</p>

            <div className="mt-6 flex flex-wrap gap-3">
              <span className="forge-badge forge-badge-blue">
                {t.connected} : {user?.email}
              </span>
              <span className="forge-badge forge-badge-green">{t.secure}</span>
            </div>
          </div>

          <section className="mt-8 grid gap-6 md:grid-cols-3">
            <Link href="/projects" className="forge-card forge-card-hover p-7">
              <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-sky-100 text-2xl">
                📁
              </div>
              <h2 className="text-2xl font-black tracking-tight text-slate-950">
                {t.projects}
              </h2>
              <p className="mt-3 text-sm font-semibold leading-6 text-slate-500">
                {t.projectsText}
              </p>
            </Link>

            <Link
              href="/projects/new"
              className="forge-card forge-card-hover p-7"
            >
              <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-violet-100 text-2xl">
                🚀
              </div>
              <h2 className="text-2xl font-black tracking-tight text-slate-950">
                {t.newIdea}
              </h2>
              <p className="mt-3 text-sm font-semibold leading-6 text-slate-500">
                {t.newIdeaText}
              </p>
            </Link>

            <div className="forge-card p-7">
              <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-rose-100 text-2xl">
                🔐
              </div>
              <h2 className="text-2xl font-black tracking-tight text-slate-950">
                {t.personal}
              </h2>
              <p className="mt-3 text-sm font-semibold leading-6 text-slate-500">
                {t.personalText}
              </p>
            </div>
          </section>

          <section className="mt-8 grid gap-6 md:grid-cols-4">
            <div className="forge-stat-card">
              <span>{t.modules}</span>
              <strong>6</strong>
            </div>
            <div className="forge-stat-card">
              <span>{t.agents}</span>
              <strong>5+</strong>
            </div>
            <div className="forge-stat-card">
              <span>{t.deliverables}</span>
              <strong>10+</strong>
            </div>
            <div className="forge-stat-card">
              <span>{t.languages}</span>
              <strong>FR/EN</strong>
            </div>
          </section>
        </section>
      </main>
    </ProtectedPage>
  );
}