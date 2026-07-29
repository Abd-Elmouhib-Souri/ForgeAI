"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ProtectedPage from "@/components/auth/ProtectedPage";
import api from "@/lib/api";
import { getApiErrorMessage } from "@/lib/api-error";
import { useAuth } from "@/lib/auth-context";
import { useForgeLanguage } from "@/lib/language-context";
import ForgeAppNavbar from "@/components/forge/ForgeAppNavbar";

interface Project {
  id: number;
  title: string;
  description: string;
  industry?: string | null;
  market_region?: string | null;
  status: string;
  startup_score?: number | null;
  created_at?: string;
}

const content = {
  fr: {
    eyebrow: "Espace projets",
    title: "Mes projets",
    subtitle:
      "Suivez vos idées, lancez vos analyses IA et consultez vos rapports en un seul endroit.",
    connected: "Connecté",
    project: "projet",
    projects: "projets",
    listTitle: "Liste des projets",
    listText: "Créez, consultez et analysez vos idées startup.",
    newProject: "+ Nouveau projet",
    loading: "Chargement des projets...",
    error: "Impossible de charger les projets.",
    emptyTitle: "Aucun projet pour le moment",
    emptyText:
      "Créez votre première idée avec ForgeAI et générez une analyse stratégique complète.",
    createProject: "Créer un projet",
    sector: "Secteur",
    region: "Pays/Région",
    startupScore: "Startup Score",
  },
  en: {
    eyebrow: "Projects workspace",
    title: "My projects",
    subtitle:
      "Track your ideas, launch AI analyses and access your reports in one place.",
    connected: "Connected",
    project: "project",
    projects: "projects",
    listTitle: "Project list",
    listText: "Create, review and analyze your startup ideas.",
    newProject: "+ New project",
    loading: "Loading projects...",
    error: "Unable to load projects.",
    emptyTitle: "No projects yet",
    emptyText:
      "Create your first idea with ForgeAI and generate a complete strategic analysis.",
    createProject: "Create project",
    sector: "Sector",
    region: "Country/Region",
    startupScore: "Startup Score",
  },
};

function ProjectsContent() {
  const { user } = useAuth();
  const { lang } = useForgeLanguage();
  const t = content[lang];

  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchProjects = async () => {
      try {
        setError("");
        const res = await api.get<Project[]>("/projects");
        setProjects(res.data);
      } catch (err: unknown) {
        setError(getApiErrorMessage(err, t.error));
      } finally {
        setIsLoading(false);
      }
    };

    fetchProjects();
  }, [t.error]);

  const projectCountLabel =
    projects.length > 1 ? t.projects : t.project;

  return (
    <main className="forge-page min-h-screen">
      <ForgeAppNavbar active="projects" />

      <section className="forge-section-sm">
        <div className="forge-panel p-8">
          <span className="forge-eyebrow">{"\u2728"} {t.eyebrow}</span>
          <h1 className="forge-title mt-2">{t.title}</h1>
          <p className="forge-subtitle">{t.subtitle}</p>

          <div className="mt-6 flex flex-wrap gap-3">
            <span className="forge-badge forge-badge-blue">
              {t.connected} : {user?.email}
            </span>
            <span className="forge-badge forge-badge-violet">
              {projects.length} {projectCountLabel}
            </span>
          </div>
        </div>

        <div className="mt-10 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-3xl font-black tracking-tight text-slate-950">
              {t.listTitle}
            </h2>
            <p className="mt-2 text-sm font-semibold text-slate-500">
              {t.listText}
            </p>
          </div>

          <Link href="/projects/new" className="forge-btn forge-btn-primary">
            {t.newProject}
          </Link>
        </div>

        {isLoading && (
          <div className="forge-card mt-10 p-6">
            <p className="animate-pulse text-sm font-bold text-slate-500">
              {t.loading}
            </p>
          </div>
        )}

        {error && (
          <p className="mt-10 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">
            {error}
          </p>
        )}

        {!isLoading && !error && projects.length === 0 && (
          <div className="forge-empty-state mt-10">
            <h3>{t.emptyTitle}</h3>
            <p>{t.emptyText}</p>

            <Link
              href="/projects/new"
              className="forge-btn forge-btn-primary mt-6"
            >
              {t.createProject}
            </Link>
          </div>
        )}

        {!isLoading && !error && projects.length > 0 && (
          <div className="mt-10 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {projects.map((project) => (
              <Link
                key={project.id}
                href={`/projects/${project.id}`}
                className="forge-card forge-card-hover flex min-h-[320px] flex-col p-7"
              >
                <div className="flex items-start justify-between gap-4">
                  <h2 className="text-2xl font-black leading-tight tracking-tight text-slate-950">
                    {project.title}
                  </h2>

                  <span className="forge-badge forge-badge-blue shrink-0">
                    {project.status}
                  </span>
                </div>

                <p className="mt-4 line-clamp-4 text-sm font-semibold leading-6 text-slate-500">
                  {project.description}
                </p>

                <div className="mt-auto pt-6">
                  {project.industry && (
                    <p className="text-sm font-bold text-slate-500">
                      {t.sector} :{" "}
                      <span className="font-black text-slate-700">
                        {project.industry}
                      </span>
                    </p>
                  )}

                  {project.market_region && (
                    <p className="mt-1 text-sm font-bold text-slate-500">
                      {t.region} :{" "}
                      <span className="font-black text-slate-700">
                        {project.market_region}
                      </span>
                    </p>
                  )}

                  {project.startup_score !== null &&
                    project.startup_score !== undefined && (
                      <div className="mt-4 flex items-center justify-between rounded-2xl bg-emerald-50 px-4 py-3 text-sm">
                        <span className="font-black text-emerald-700">
                          {t.startupScore}
                        </span>
                        <strong className="text-emerald-700">
                          {project.startup_score}/10
                        </strong>
                      </div>
                    )}
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}

export default function ProjectsPage() {
  return (
    <ProtectedPage>
      <ProjectsContent />
    </ProtectedPage>
  );
}





