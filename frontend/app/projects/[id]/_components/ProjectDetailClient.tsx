"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import api from "@/lib/api";
import { useForgeLanguage } from "@/lib/language-context";
import ForgeAppNavbar from "@/components/forge/ForgeAppNavbar";

import type {
  Project,
  ProjectAnalysisResponse,
} from "../_types/project-detail.types";

import {
  clampProgress,
  getErrorMessage,
} from "../_lib/formatters";

import {
  getOfficialStartupScore,
  getPublicAnalysisWarning,
  getReportLanguage,
  publicAnalysisStep,
} from "../_lib/analysis-helpers";

import { cleanText } from "../_lib/text-cleaning";

import ProjectHero from "./ProjectHero";
import ProjectStatusCards from "./ProjectStatusCards";
import AnalysisActionCard from "./AnalysisActionCard";
import { Panel } from "./UIBlocks";
import FinalReportSection from "../_sections/FinalReportSection";

const content = {
  fr: {
    loadingProject: "Chargement du projet...",
    projectNotFound: "Projet introuvable.",
    loadAnalysisError: "Erreur lors du chargement de l’analyse.",
    deleteConfirm: "Voulez-vous vraiment supprimer ce projet ?",
    deleteError: "Erreur lors de la suppression.",
    startAnalysisError: "Erreur lors du lancement de l’analyse.",
    analysisLaunched: "Analyse lancée. ForgeAI prépare le rapport...",
    backProjects: "Retour aux projets",
    report: "Rapport ForgeAI",
    edit: "Modifier",
    delete: "Supprimer",
    deleting: "Suppression...",
    unknownSector: "Secteur non spécifié",
    defaultRegion: "Tunisie",
    description: "Description du projet",
    startupScore: "Startup Score",
    analysis: "Analyse",
    step: "Étape",
    progress: "Progression",
    start: "Début",
    end: "Fin",
    targetRegion: "Pays/Région cible",
    running: "Analyse en cours...",
    launching: "Lancement...",
    relaunch: "Relancer l’analyse",
    launch: "Lancer l’analyse",
    reportTitle: "Rapport utilisateur final",
    reportSubtitle:
      "Aperçu structuré du rapport. Les sections détaillées sont séparées dans des composants dédiés.",
    noReport:
      "Aucune analyse disponible. Lancez l’analyse IA pour générer le rapport.",
    summary: "Résumé exécutif",
    problem: "Problème identifié",
    solution: "Solution proposée",
    targetMarket: "Marché cible",
    technologies: "Technologies recommandées",
    improvements: "Suggestions d’amélioration",
    risks: "Risques",
    startupScoreReport: "Startup Score",
    verdict: "Verdict final",
    riskLevel: "Niveau de risque",
    nextActions: "Actions recommandées",
    limitations: "Limites de l’analyse",
    marketStudy: "Étude de marché",
    swot: "Analyse SWOT",
    bmc: "Business Model Canvas",
    competitors: "Analyse concurrentielle",
    personas: "Personas clients",
    debate: "Debate Room Pro",
    factCheck: "Fact Checker",
    available: "Disponible",
    missing: "À compléter",
  },
  en: {
    loadingProject: "Loading project...",
    projectNotFound: "Project not found.",
    loadAnalysisError: "Error while loading the analysis.",
    deleteConfirm: "Do you really want to delete this project?",
    deleteError: "Error while deleting the project.",
    startAnalysisError: "Error while starting the analysis.",
    analysisLaunched: "Analysis started. ForgeAI is preparing the report...",
    backProjects: "Back to projects",
    report: "ForgeAI report",
    edit: "Edit",
    delete: "Delete",
    deleting: "Deleting...",
    unknownSector: "Unspecified sector",
    defaultRegion: "Tunisia",
    description: "Project description",
    startupScore: "Startup Score",
    analysis: "Analysis",
    step: "Step",
    progress: "Progress",
    start: "Start",
    end: "End",
    targetRegion: "Target country/region",
    running: "Analysis running...",
    launching: "Launching...",
    relaunch: "Relaunch analysis",
    launch: "Launch analysis",
    reportTitle: "Final user report",
    reportSubtitle:
      "Structured report preview. Detailed sections are separated into dedicated components.",
    noReport:
      "No analysis available. Launch the AI analysis to generate the report.",
    summary: "Executive summary",
    problem: "Identified problem",
    solution: "Proposed solution",
    targetMarket: "Target market",
    technologies: "Recommended technologies",
    improvements: "Improvement suggestions",
    risks: "Risks",
    startupScoreReport: "Startup Score",
    verdict: "Final verdict",
    riskLevel: "Risk level",
    nextActions: "Recommended actions",
    limitations: "Analysis limitations",
    marketStudy: "Market study",
    swot: "SWOT analysis",
    bmc: "Business Model Canvas",
    competitors: "Competitive analysis",
    personas: "Customer personas",
    debate: "Debate Room Pro",
    factCheck: "Fact Checker",
    available: "Available",
    missing: "Missing",
  },
};

export default function ProjectDetailClient() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const { lang, setLang } = useForgeLanguage();
  const t = content[lang];

  const [project, setProject] = useState<Project | null>(null);
  const [analysis, setAnalysis] = useState<ProjectAnalysisResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isStartingAnalysis, setIsStartingAnalysis] = useState(false);
  const [error, setError] = useState("");
  const [analysisMessage, setAnalysisMessage] = useState("");

  const fetchProject = useCallback(async () => {
    if (!id) return;

    try {
      const res = await api.get<Project>(`/projects/${id}`);
      const loadedProject = res.data;

      setProject(loadedProject);

      if (
        loadedProject.output_language === "fr" ||
        loadedProject.output_language === "en"
      ) {
        setLang(loadedProject.output_language);
      }

      setAnalysis({
        project_id: loadedProject.id,
        analysis_status: loadedProject.analysis_status || "not_started",
        analysis_step: loadedProject.analysis_step || "idle",
        analysis_progress: loadedProject.analysis_progress ?? 0,
        analysis_data: loadedProject.analysis_data || null,
        analysis_error: loadedProject.analysis_error || null,
        analysis_started_at: loadedProject.analysis_started_at || null,
        analysis_completed_at: loadedProject.analysis_completed_at || null,
      });

      setError("");
    } catch (err) {
      setProject(null);
      setAnalysis(null);
      setError(getErrorMessage(err, t.projectNotFound));
    }
  }, [id, setLang, t.projectNotFound]);

  const fetchAnalysis = useCallback(async () => {
    if (!id) return null;

    try {
      const res = await api.get<ProjectAnalysisResponse>(
        `/projects/${id}/analysis`
      );

      setAnalysis(res.data);

      if (res.data.analysis_status === "completed") {
        const projectRes = await api.get<Project>(`/projects/${id}`);
        const loadedProject = projectRes.data;

        setProject(loadedProject);

        if (
          loadedProject.output_language === "fr" ||
          loadedProject.output_language === "en"
        ) {
          setLang(loadedProject.output_language);
        }

        setAnalysis({
          project_id: loadedProject.id,
          analysis_status: loadedProject.analysis_status || "completed",
          analysis_step:
            loadedProject.analysis_step ||
            (loadedProject.output_language === "en"
              ? "Analysis completed"
              : "Analyse terminée"),
          analysis_progress: loadedProject.analysis_progress ?? 100,
          analysis_data: loadedProject.analysis_data || null,
          analysis_error: loadedProject.analysis_error || null,
          analysis_started_at: loadedProject.analysis_started_at || null,
          analysis_completed_at: loadedProject.analysis_completed_at || null,
        });
      }

      setError("");
      return res.data;
    } catch (err) {
      setError(getErrorMessage(err, t.loadAnalysisError));
      return null;
    }
  }, [id, setLang, t.loadAnalysisError]);

  useEffect(() => {
    const load = async () => {
      setIsLoading(true);
      await fetchProject();
      setIsLoading(false);
    };

    void load();
  }, [fetchProject]);

  useEffect(() => {
    if (analysis?.analysis_status !== "running") return;

    const interval = window.setInterval(() => {
      void fetchAnalysis();
    }, 3000);

    return () => window.clearInterval(interval);
  }, [analysis?.analysis_status, fetchAnalysis]);

  async function handleDelete() {
    const confirmed = window.confirm(t.deleteConfirm);
    if (!confirmed) return;

    try {
      setIsDeleting(true);
      await api.delete(`/projects/${id}`);
      router.replace("/projects");
    } catch (err) {
      setError(getErrorMessage(err, t.deleteError));
      setIsDeleting(false);
    }
  }

  async function handleStartAnalysis() {
    try {
      setError("");
      setAnalysisMessage("");
      setIsStartingAnalysis(true);

      const res = await api.post<ProjectAnalysisResponse>(
        `/projects/${id}/analyze/start`
      );

      setAnalysis(res.data);
      setAnalysisMessage(t.analysisLaunched);

      window.setTimeout(() => {
        void fetchAnalysis();
      }, 1500);
    } catch (err) {
      setError(getErrorMessage(err, t.startAnalysisError));
    } finally {
      setIsStartingAnalysis(false);
    }
  }

  if (isLoading) {
    return (
      <main className="forge-page min-h-screen">
        <ForgeAppNavbar active="projects" />

        <section className="forge-section-sm">
          <div className="forge-card p-6">
            <p className="animate-pulse text-sm font-bold text-slate-500">
              {t.loadingProject}
            </p>
          </div>
        </section>
      </main>
    );
  }

  if (!project) {
    return (
      <main className="forge-page min-h-screen">
        <ForgeAppNavbar active="projects" />

        <section className="forge-section-sm">
          <div className="rounded-3xl border border-red-200 bg-red-50 p-6">
            <p className="font-semibold text-red-700">
              {error || t.projectNotFound}
            </p>

            <Link
              href="/projects"
              className="mt-4 inline-block text-sm font-black text-sky-600 hover:underline"
            >
              ← {t.backProjects}
            </Link>
          </div>
        </section>
      </main>
    );
  }

  const analysisData = analysis?.analysis_data || project.analysis_data || null;

  const reportLanguage = getReportLanguage(project, analysisData, lang);

  const currentStatus =
    analysis?.analysis_status || project.analysis_status || "not_started";

  const currentStep = publicAnalysisStep(
    analysis?.analysis_step || project.analysis_step || "idle",
    reportLanguage
  );

  const progress = clampProgress(
    analysis?.analysis_progress ?? project.analysis_progress ?? 0
  );

  const analysisIsRunning =
    currentStatus === "running" || currentStatus === "pending";

  const publicAnalysisWarning = getPublicAnalysisWarning(
    analysis?.analysis_error,
    currentStatus,
    reportLanguage
  );

  const finalStartupScore = getOfficialStartupScore(
    analysisData,
    project.startup_score
  );

  return (
    <main className="forge-page min-h-screen">
      <ForgeAppNavbar active="projects" />

      <section className="forge-section-sm space-y-8">
        {error && (
          <p className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">
            {cleanText(error, reportLanguage)}
          </p>
        )}

        <ProjectHero
          project={project}
          currentStatus={currentStatus}
          isDeleting={isDeleting}
          onDelete={handleDelete}
          copy={{
            backProjects: t.backProjects,
            report: t.report,
            edit: t.edit,
            delete: t.delete,
            deleting: t.deleting,
            unknownSector: t.unknownSector,
            defaultRegion: t.defaultRegion,
          }}
        />

        <Panel title={t.description}>
          <p className="whitespace-pre-wrap text-sm font-semibold leading-7 text-slate-600">
            {cleanText(project.description, reportLanguage)}
          </p>
        </Panel>

        <ProjectStatusCards
          project={project}
          analysis={analysis}
          currentStatus={currentStatus}
          currentStep={currentStep}
          progress={progress}
          finalStartupScore={finalStartupScore}
          copy={{
            startupScore: t.startupScore,
            analysis: t.analysis,
            step: t.step,
            progress: t.progress,
            start: t.start,
            end: t.end,
            targetRegion: t.targetRegion,
            defaultRegion: t.defaultRegion,
          }}
        />

        <AnalysisActionCard
          currentStatus={currentStatus}
          progress={progress}
          currentStep={currentStep}
          isStartingAnalysis={isStartingAnalysis}
          analysisIsRunning={analysisIsRunning}
          analysisMessage={analysisMessage}
          publicAnalysisWarning={publicAnalysisWarning}
          onStartAnalysis={handleStartAnalysis}
          copy={{
            running: t.running,
            launching: t.launching,
            relaunch: t.relaunch,
            launch: t.launch,
          }}
        />

        <FinalReportSection
          analysisData={analysisData}
          project={project}
          copy={{
            reportTitle: t.reportTitle,
            reportSubtitle: t.reportSubtitle,
            noReport: t.noReport,
            summary: t.summary,
            problem: t.problem,
            solution: t.solution,
            targetMarket: t.targetMarket,
            technologies: t.technologies,
            improvements: t.improvements,
            risks: t.risks,
            startupScore: t.startupScoreReport,
            verdict: t.verdict,
            riskLevel: t.riskLevel,
            nextActions: t.nextActions,
            limitations: t.limitations,
            marketStudy: t.marketStudy,
            swot: t.swot,
            bmc: t.bmc,
            competitors: t.competitors,
            personas: t.personas,
            debate: t.debate,
            factCheck: t.factCheck,
            available: t.available,
            missing: t.missing,
          }}
        />
      </section>
    </main>
  );
}