"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import api from "@/lib/api";
import { useForgeLanguage } from "@/lib/language-context";
import ForgeAppNavbar from "@/components/forge/ForgeAppNavbar";

import type {
  AnalysisData,
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
    loadAnalysisError: "Erreur lors du chargement de lâ€™analyse.",
    deleteConfirm: "Voulez-vous vraiment supprimer ce projet ?",
    deleteError: "Erreur lors de la suppression.",
    startAnalysisError: "Erreur lors du lancement de lâ€™analyse.",
    clarificationTitle: "Précisions nécessaires avant l’analyse",
    clarificationIntro:
      "ForgeAI a arrêté l’analyse avant les recherches externes et les agents afin d’éviter des conclusions basées sur des hypothèses.",
    contextScore: "Score de contexte",
    blockingFields: "Champs bloquants",
    missingFields: "Informations manquantes",
    ambiguousFields: "Informations ambiguës",
    clarificationQuestions: "Questions à compléter",
    editProject: "Modifier le projet",
    rerunContextCheck: "Relancer la vérification",
    rerunningContextCheck: "Vérification...",
    clarificationReadyHint:
      "Modifiez la description avec les réponses ci-dessous, puis relancez l’analyse.",
    analysisLaunched: "Analyse lancÃ©e. ForgeAI prÃ©pare le rapport...",
    backProjects: "Retour aux projets",
    report: "Rapport ForgeAI",
    edit: "Modifier",
    delete: "Supprimer",
    deleting: "Suppression...",
    unknownSector: "Secteur non spÃ©cifiÃ©",
    defaultRegion: "Non définie",
    description: "Description du projet",
    startupScore: "Score de potentiel",
    analysis: "Analyse",
    step: "Ã‰tape",
    progress: "Progression",
    start: "DÃ©but",
    end: "Fin",
    targetRegion: "Pays/RÃ©gion cible",
    running: "Analyse en cours...",
    launching: "Lancement...",
    relaunch: "Relancer lâ€™analyse",
    launch: "Lancer lâ€™analyse",
    reportTitle: "Rapport utilisateur final",
    reportSubtitle:
      "AperÃ§u structurÃ© du rapport. Les sections dÃ©taillÃ©es sont sÃ©parÃ©es dans des composants dÃ©diÃ©s.",
    noReport:
      "Aucune analyse disponible. Lancez lâ€™analyse IA pour gÃ©nÃ©rer le rapport.",
    summary: "RÃ©sumÃ© exÃ©cutif",
    problem: "ProblÃ¨me identifiÃ©",
    solution: "Solution proposÃ©e",
    targetMarket: "MarchÃ© cible",
    technologies: "Technologies recommandÃ©es",
    improvements: "Suggestions dâ€™amÃ©lioration",
    risks: "Risques",
    startupScoreReport: "Ã‰valuation startup",
    verdict: "Verdict final",
    riskLevel: "Niveau de risque",
    nextActions: "Actions recommandÃ©es",
    limitations: "Limites de lâ€™analyse",
    marketStudy: "Ã‰tude de marchÃ©",
    swot: "Analyse SWOT",
    bmc: "Business Model Canvas",
    competitors: "Analyse concurrentielle",
    personas: "Personas clients",
    debate: "Debate Room Pro",
    factCheck: "Fact Checker",
    available: "Disponible",
    missing: "Ã€ complÃ©ter",
  },
  en: {
    loadingProject: "Loading project...",
    projectNotFound: "Project not found.",
    loadAnalysisError: "Error while loading the analysis.",
    deleteConfirm: "Do you really want to delete this project?",
    deleteError: "Error while deleting the project.",
    startAnalysisError: "Error while starting the analysis.",
    clarificationTitle: "More details are required before analysis",
    clarificationIntro:
      "ForgeAI stopped before external searches and analysis agents to avoid conclusions based on unsupported assumptions.",
    contextScore: "Context score",
    blockingFields: "Blocking fields",
    missingFields: "Missing information",
    ambiguousFields: "Ambiguous information",
    clarificationQuestions: "Questions to complete",
    editProject: "Edit project",
    rerunContextCheck: "Rerun context check",
    rerunningContextCheck: "Checking...",
    clarificationReadyHint:
      "Update the project description with the answers below, then relaunch the analysis.",
    analysisLaunched: "Analysis started. ForgeAI is preparing the report...",
    backProjects: "Back to projects",
    report: "ForgeAI report",
    edit: "Edit",
    delete: "Delete",
    deleting: "Deleting...",
    unknownSector: "Unspecified sector",
    defaultRegion: "Not defined",
    description: "Project description",
    startupScore: "Potential score",
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
    startupScoreReport: "Startup assessment",
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


const ACTIVE_ANALYSIS_STATUSES = new Set([
  "queued",
  "pending",
  "running",
]);

const TERMINAL_ANALYSIS_STATUSES = new Set([
  "completed",
  "failed",
  "needs_clarification",
]);

type ContextReadinessView = {
  status: string;
  score: number | null;
  readyForAgents: boolean | null;
  missingFields: string[];
  ambiguousFields: string[];
  blockers: string[];
  questions: string[];
  recommendation: string;
};

function normalizedStatus(value: unknown): string {
  return String(value || "").trim().toLowerCase();
}

function isActiveAnalysisStatus(value: unknown): boolean {
  return ACTIVE_ANALYSIS_STATUSES.has(normalizedStatus(value));
}

function isTerminalAnalysisStatus(value: unknown): boolean {
  return TERMINAL_ANALYSIS_STATUSES.has(normalizedStatus(value));
}

function uniqueTextItems(values: unknown[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];

  for (const value of values) {
    if (!Array.isArray(value)) continue;

    for (const item of value) {
      const text = String(item || "").trim();
      const key = text.toLocaleLowerCase();

      if (!text || seen.has(key)) continue;

      seen.add(key);
      result.push(text);
    }
  }

  return result;
}

function resolveContextReadiness(
  analysisData: AnalysisData | null
): ContextReadinessView {
  const readiness = analysisData?.idea_readiness;
  const packetConfidence = analysisData?.project_context_packet?.confidence;
  const confidence =
    analysisData?.context_confidence ||
    readiness?.context_confidence ||
    packetConfidence;

  const rawScore =
    typeof readiness?.score === "number"
      ? readiness.score
      : typeof confidence?.score === "number"
        ? confidence.score
        : null;

  const readyForAgents =
    typeof readiness?.ready_for_agents === "boolean"
      ? readiness.ready_for_agents
      : typeof confidence?.ready_for_agents === "boolean"
        ? confidence.ready_for_agents
        : null;

  return {
    status: normalizedStatus(readiness?.status || confidence?.status),
    score: rawScore,
    readyForAgents,
    missingFields: uniqueTextItems([
      readiness?.missing_fields,
      confidence?.missing_fields,
    ]),
    ambiguousFields: uniqueTextItems([
      readiness?.ambiguous_fields,
      confidence?.ambiguous_fields,
    ]),
    blockers: uniqueTextItems([
      readiness?.blockers,
      confidence?.blockers,
    ]),
    questions: uniqueTextItems([
      readiness?.questions,
      readiness?.clarification_questions,
      confidence?.clarification_questions,
    ]),
    recommendation: String(readiness?.recommendation || "").trim(),
  };
}

function fieldLabel(field: string, language: "fr" | "en"): string {
  const labels: Record<string, { fr: string; en: string }> = {
    project_name: {
      fr: "Nom du projet",
      en: "Project name",
    },
    problem: {
      fr: "Problème",
      en: "Problem",
    },
    solution: {
      fr: "Solution",
      en: "Solution",
    },
    actors: {
      fr: "Utilisateurs, acheteurs et opérateurs",
      en: "Users, buyers, and operators",
    },
    priority_workflow: {
      fr: "Workflow principal",
      en: "Primary workflow",
    },
    target_region: {
      fr: "Pays ou région cible",
      en: "Target country or region",
    },
    project_archetype: {
      fr: "Type de projet",
      en: "Project archetype",
    },
    business_model: {
      fr: "Modèle économique",
      en: "Business model",
    },
    mvp_scope: {
      fr: "Périmètre du MVP",
      en: "MVP scope",
    },
    constraints: {
      fr: "Contraintes",
      en: "Constraints",
    },
    success_metrics: {
      fr: "Indicateurs de succès",
      en: "Success metrics",
    },
    domain_integrity: {
      fr: "Périmètre métier",
      en: "Domain integrity",
    },
  };

  return (
    labels[field]?.[language] ||
    field
      .replace(/_/g, " ")
      .replace(/^\w/, (character) => character.toUpperCase())
  );
}

function ContextClarificationPanel({
  language,
  readiness,
  editHref,
  isStartingAnalysis,
  onStartAnalysis,
  copy,
}: {
  language: "fr" | "en";
  readiness: ContextReadinessView;
  editHref: string;
  isStartingAnalysis: boolean;
  onStartAnalysis: () => void;
  copy: {
    title: string;
    intro: string;
    contextScore: string;
    blockingFields: string;
    missingFields: string;
    ambiguousFields: string;
    questions: string;
    editProject: string;
    rerun: string;
    rerunning: string;
    hint: string;
  };
}) {
  const scorePercent =
    typeof readiness.score === "number"
      ? Math.round(Math.max(0, Math.min(1, readiness.score)) * 100)
      : null;

  const groups = [
    {
      title: copy.blockingFields,
      fields: readiness.blockers,
      className: "border-red-200 bg-red-50 text-red-800",
    },
    {
      title: copy.missingFields,
      fields: readiness.missingFields,
      className: "border-amber-200 bg-amber-50 text-amber-900",
    },
    {
      title: copy.ambiguousFields,
      fields: readiness.ambiguousFields,
      className: "border-violet-200 bg-violet-50 text-violet-900",
    },
  ].filter((group) => group.fields.length > 0);

  return (
    <section className="overflow-hidden rounded-[2rem] border border-amber-200 bg-white shadow-sm">
      <div className="border-b border-amber-100 bg-gradient-to-r from-amber-50 via-orange-50 to-rose-50 p-6 md:p-8">
        <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-black uppercase tracking-[0.18em] text-amber-700">
              {language === "en" ? "Context gate" : "Validation du contexte"}
            </p>

            <h2 className="mt-2 text-2xl font-black tracking-tight text-slate-950">
              {copy.title}
            </h2>

            <p className="mt-3 text-sm font-semibold leading-7 text-slate-600">
              {copy.intro}
            </p>
          </div>

          <div className="min-w-36 rounded-3xl border border-white/80 bg-white/90 px-5 py-4 text-center shadow-sm">
            <p className="text-xs font-black uppercase tracking-wide text-slate-400">
              {copy.contextScore}
            </p>
            <p className="mt-1 text-3xl font-black text-amber-700">
              {scorePercent === null ? "—" : `${scorePercent}%`}
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-6 p-6 md:p-8">
        {readiness.recommendation && (
          <p className="rounded-2xl border border-sky-100 bg-sky-50 p-4 text-sm font-semibold leading-6 text-sky-900">
            {cleanText(readiness.recommendation, language)}
          </p>
        )}

        {groups.length > 0 && (
          <div className="grid gap-4 md:grid-cols-3">
            {groups.map((group) => (
              <div
                key={group.title}
                className={`rounded-3xl border p-5 ${group.className}`}
              >
                <p className="text-sm font-black">{group.title}</p>

                <ul className="mt-3 space-y-2 text-sm font-semibold">
                  {group.fields.map((field) => (
                    <li key={field} className="flex gap-2">
                      <span aria-hidden="true">•</span>
                      <span>{fieldLabel(field, language)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}

        {readiness.questions.length > 0 && (
          <div>
            <h3 className="text-lg font-black text-slate-950">
              {copy.questions}
            </h3>

            <ol className="mt-4 grid gap-3 md:grid-cols-2">
              {readiness.questions.map((question, index) => (
                <li
                  key={`${question}-${index}`}
                  className="rounded-3xl border border-slate-200 bg-slate-50/80 p-5"
                >
                  <div className="flex gap-3">
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-950 text-xs font-black text-white">
                      {index + 1}
                    </span>

                    <p className="text-sm font-semibold leading-6 text-slate-700">
                      {cleanText(question, language)}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        )}

        <div className="flex flex-col gap-4 rounded-3xl border border-slate-200 bg-slate-50 p-5 md:flex-row md:items-center md:justify-between">
          <p className="max-w-2xl text-sm font-semibold leading-6 text-slate-600">
            {copy.hint}
          </p>

          <div className="flex flex-col gap-3 sm:flex-row">
            <Link
              href={editHref}
              className="inline-flex items-center justify-center rounded-2xl bg-slate-950 px-5 py-3 text-sm font-black text-white transition hover:bg-slate-800"
            >
              {copy.editProject}
            </Link>

            <button
              type="button"
              onClick={onStartAnalysis}
              disabled={isStartingAnalysis}
              className="inline-flex items-center justify-center rounded-2xl border border-slate-300 bg-white px-5 py-3 text-sm font-black text-slate-800 transition hover:border-sky-300 hover:text-sky-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isStartingAnalysis ? copy.rerunning : copy.rerun}
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

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
  const analysisRequestInFlight = useRef(false);
  const activeAnalysisRunId = useRef<string | null>(null);
  const analysisStatusRef = useRef<string | null>(null);
  const analysisSnapshotRef = useRef<ProjectAnalysisResponse | null>(null);

  const fetchProject = useCallback(async () => {
    if (!id) return;

    try {
      const res = await api.get<Project>(`/projects/${id}`, {
        params: { _ts: Date.now() },
        headers: { "Cache-Control": "no-cache" },
      });
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
        analysis_run_id: loadedProject.analysis_run_id || null,
        analysis_heartbeat_at: loadedProject.analysis_heartbeat_at || null,
        analysis_attempt: loadedProject.analysis_attempt || null,
      });

      if (loadedProject.analysis_run_id) {
        activeAnalysisRunId.current = loadedProject.analysis_run_id;
      }

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
        `/projects/${id}/analysis`,
        {
          params: { _ts: Date.now() },
          headers: { "Cache-Control": "no-cache" },
        }
      );

      const nextAnalysis = res.data;
      const expectedRunId = activeAnalysisRunId.current;
      const nextRunId = nextAnalysis.analysis_run_id || null;

      if (
        expectedRunId &&
        nextRunId &&
        expectedRunId !== nextRunId &&
        ["queued", "pending", "running"].includes(
          analysisStatusRef.current || ""
        )
      ) {
        return analysisSnapshotRef.current;
      }

      if (nextRunId) {
        activeAnalysisRunId.current = nextRunId;
      }

      setAnalysis((previous) => {
        if (
          previous?.analysis_run_id &&
          nextRunId &&
          previous.analysis_run_id === nextRunId
        ) {
          return {
            ...nextAnalysis,
            analysis_progress: Math.max(
              previous.analysis_progress ?? 0,
              nextAnalysis.analysis_progress ?? 0
            ),
          };
        }
        return nextAnalysis;
      });

      if (isTerminalAnalysisStatus(nextAnalysis.analysis_status)) {
        const projectRes = await api.get<Project>(`/projects/${id}`, {
          params: { _ts: Date.now() },
          headers: { "Cache-Control": "no-cache" },
        });
        const loadedProject = projectRes.data;
        const loadedStatus =
          loadedProject.analysis_status ||
          nextAnalysis.analysis_status ||
          "not_started";

        setProject(loadedProject);

        if (
          loadedProject.output_language === "fr" ||
          loadedProject.output_language === "en"
        ) {
          setLang(loadedProject.output_language);
        }

        const fallbackStep =
          loadedStatus === "completed"
            ? loadedProject.output_language === "en"
              ? "Analysis completed"
              : "Analyse terminée"
            : loadedStatus === "needs_clarification"
              ? loadedProject.output_language === "en"
                ? "Project clarification required"
                : "Clarification du projet requise"
              : loadedProject.output_language === "en"
                ? "Analysis failed"
                : "Analyse échouée";

        setAnalysis({
          project_id: loadedProject.id,
          analysis_status: loadedStatus,
          analysis_step:
            loadedProject.analysis_step ||
            nextAnalysis.analysis_step ||
            fallbackStep,
          analysis_progress:
            loadedProject.analysis_progress ??
            nextAnalysis.analysis_progress ??
            (loadedStatus === "completed" ? 100 : 0),
          analysis_data:
            loadedProject.analysis_data ||
            nextAnalysis.analysis_data ||
            null,
          analysis_error:
            loadedProject.analysis_error ||
            nextAnalysis.analysis_error ||
            null,
          analysis_started_at:
            loadedProject.analysis_started_at ||
            nextAnalysis.analysis_started_at ||
            null,
          analysis_completed_at:
            loadedProject.analysis_completed_at ||
            nextAnalysis.analysis_completed_at ||
            null,
          analysis_run_id:
            loadedProject.analysis_run_id ||
            nextAnalysis.analysis_run_id ||
            nextRunId,
          analysis_heartbeat_at:
            loadedProject.analysis_heartbeat_at ||
            nextAnalysis.analysis_heartbeat_at ||
            null,
          analysis_attempt:
            loadedProject.analysis_attempt ||
            nextAnalysis.analysis_attempt ||
            null,
        });

        if (loadedStatus === "needs_clarification") {
          setAnalysisMessage("");
        }
      }

      setError("");
      return nextAnalysis;
    } catch (err) {
      setError(getErrorMessage(err, t.loadAnalysisError));
      return null;
    }
  }, [id, setLang, t.loadAnalysisError]);

  useEffect(() => {
    analysisStatusRef.current = analysis?.analysis_status || null;
    analysisSnapshotRef.current = analysis;
  }, [analysis]);

  useEffect(() => {
    const load = async () => {
      setIsLoading(true);
      await fetchProject();
      await fetchAnalysis();
      setIsLoading(false);
    };

    void load();
  }, [fetchAnalysis, fetchProject]);

  useEffect(() => {
    if (!isActiveAnalysisStatus(analysis?.analysis_status)) {
      return;
    }

    let cancelled = false;
    let timer: number | undefined;
    let delay = 2500;

    const poll = async () => {
      if (cancelled || document.visibilityState === "hidden") {
        timer = window.setTimeout(poll, 5000);
        return;
      }
      if (analysisRequestInFlight.current) {
        timer = window.setTimeout(poll, 1000);
        return;
      }
      analysisRequestInFlight.current = true;
      try {
        const result = await fetchAnalysis();

        if (
          cancelled ||
          isTerminalAnalysisStatus(result?.analysis_status)
        ) {
          return;
        }

        delay = Math.min(10000, Math.round(delay * 1.25));
      } finally {
        analysisRequestInFlight.current = false;
      }
      if (!cancelled) timer = window.setTimeout(poll, delay);
    };

    timer = window.setTimeout(poll, 1200);
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [analysis?.analysis_status, fetchAnalysis]);

  useEffect(() => {
    if (!id) return;

    const reconcile = () => {
      if (document.visibilityState === "hidden") return;
      if (analysisRequestInFlight.current) return;

      analysisRequestInFlight.current = true;
      void fetchAnalysis().finally(() => {
        analysisRequestInFlight.current = false;
      });
    };

    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        reconcile();
      }
    };

    window.addEventListener("focus", reconcile);
    window.addEventListener("online", reconcile);
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      window.removeEventListener("focus", reconcile);
      window.removeEventListener("online", reconcile);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [fetchAnalysis, id]);

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
      activeAnalysisRunId.current = res.data.analysis_run_id || null;
      setAnalysisMessage(t.analysisLaunched);

      // The recursive polling effect owns all follow-up requests.
      // Avoid a second parallel fetch here.
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
              â† {t.backProjects}
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

  const analysisIsRunning = isActiveAnalysisStatus(currentStatus);

  const contextReadiness = resolveContextReadiness(analysisData);

  const needsClarification =
    currentStatus === "needs_clarification" ||
    analysisData?.needs_clarification === true ||
    ["needs_clarification", "insufficient_context"].includes(
      contextReadiness.status
    );

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

        {needsClarification ? (
          <ContextClarificationPanel
            language={reportLanguage}
            readiness={contextReadiness}
            editHref={`/projects/${id}/edit`}
            isStartingAnalysis={isStartingAnalysis}
            onStartAnalysis={handleStartAnalysis}
            copy={{
              title: t.clarificationTitle,
              intro: t.clarificationIntro,
              contextScore: t.contextScore,
              blockingFields: t.blockingFields,
              missingFields: t.missingFields,
              ambiguousFields: t.ambiguousFields,
              questions: t.clarificationQuestions,
              editProject: t.editProject,
              rerun: t.rerunContextCheck,
              rerunning: t.rerunningContextCheck,
              hint: t.clarificationReadyHint,
            }}
          />
        ) : (
          <>
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
          </>
        )}
      </section>
    </main>
  );
}