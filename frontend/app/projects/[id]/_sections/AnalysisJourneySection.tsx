"use client";

import { useForgeLanguage, type ForgeLang } from "@/lib/language-context";

import type { AnalysisData, Project } from "../_types/project-detail.types";

import {
  getPersonaBuilderData,
  getReportLanguage,
} from "../_lib/analysis-helpers";
import { cleanText } from "../_lib/text-cleaning";

type JourneyStep = {
  title: string;
  description: string;
  done: boolean;
  doneLabel?: string;
  pendingLabel?: string;
  warning?: boolean;
};

function resolveLanguage(
  project: Project,
  analysisData: AnalysisData,
  fallback: ForgeLang
): ForgeLang {
  return getReportLanguage(project, analysisData, fallback);
}

function hasPersonaData(analysisData: AnalysisData): boolean {
  const personaBuilder = getPersonaBuilderData(analysisData);
  if (!personaBuilder) return false;
  return Boolean(
    (personaBuilder.personas?.length || 0) > 0 || personaBuilder.primary_persona
  );
}

function hasStrategicDecision(analysisData: AnalysisData): boolean {
  const debateRoom = analysisData.debate_room;
  const startupScore = analysisData.startup_score;

  return Boolean(
    debateRoom?.rounds?.length ||
      debateRoom?.judge?.verdict ||
      debateRoom?.judge?.final_recommendation ||
      debateRoom?.judge?.go_no_go_conditions?.length ||
      debateRoom?.judge?.next_actions?.length ||
      debateRoom?.judge?.action_plan?.length ||
      startupScore?.verdict ||
      startupScore?.summary ||
      startupScore?.next_actions?.length
  );
}

function hasSourceData(analysisData: AnalysisData): boolean {
  const crawler = analysisData.forgecrawler;
  const competitive = analysisData.competitive_analysis;

  const crawlerFinished = Boolean(
    crawler &&
      ["completed", "limited", "no_verified_sources"].includes(
        String(crawler.status || "").toLowerCase()
      ) &&
      (typeof crawler.sources_count === "number" ||
        typeof crawler.no_verified_relevant_source_found === "boolean")
  );

  const competitiveFinished = Boolean(
    competitive &&
      ["completed", "limited", "no_verified_sources"].includes(
        String(competitive.status || "").toLowerCase()
      )
  );

  return crawlerFinished || competitiveFinished;
}

function retainedSourceCount(analysisData: AnalysisData): number {
  const crawler = analysisData.forgecrawler;
  const competitive = analysisData.competitive_analysis;

  const candidates = [
    crawler?.sources_count,
    crawler?.sources?.length,
    crawler?.public_sources?.length,
    competitive?.sources_count,
    competitive?.sources?.length,
    competitive?.public_sources?.length,
  ].filter((value): value is number => typeof value === "number");

  return candidates.length > 0 ? Math.max(...candidates) : 0;
}

function hasFinalVerification(analysisData: AnalysisData): boolean {
  const report = analysisData.fact_check_report;
  if (!report) return false;

  const status = String(report.status || "").toLowerCase();
  return Boolean(
    ["completed", "fallback_completed"].includes(status) &&
      Array.isArray(report.claims) &&
      report.claims.some((claim) => String(claim.claim || "").trim().length > 0)
  );
}


function contextReadinessState(analysisData: AnalysisData): {
  hasContract: boolean;
  ready: boolean;
  blocked: boolean;
  scorePercent: number | null;
} {
  const readiness = analysisData.idea_readiness;
  const confidence =
    analysisData.context_confidence ||
    readiness?.context_confidence ||
    analysisData.project_context_packet?.confidence;

  const status = String(
    readiness?.status || confidence?.status || ""
  )
    .trim()
    .toLowerCase();

  const readyForAgents =
    typeof readiness?.ready_for_agents === "boolean"
      ? readiness.ready_for_agents
      : typeof confidence?.ready_for_agents === "boolean"
        ? confidence.ready_for_agents
        : null;

  const score =
    typeof readiness?.score === "number"
      ? readiness.score
      : typeof confidence?.score === "number"
        ? confidence.score
        : null;

  return {
    hasContract: Boolean(
      readiness ||
        confidence ||
        analysisData.project_context_packet ||
        analysisData.needs_clarification
    ),
    ready:
      readyForAgents === true ||
      ["ready", "ready_cautious"].includes(status),
    blocked:
      analysisData.needs_clarification === true ||
      ["needs_clarification", "insufficient_context"].includes(status),
    scorePercent:
      score === null
        ? null
        : Math.round(Math.max(0, Math.min(1, score)) * 100),
  };
}

function buildSteps(
  analysisData: AnalysisData,
  language: ForgeLang
): JourneyStep[] {
  const hasMarket = Boolean(
    analysisData.market_study ||
      analysisData.swot ||
      analysisData.business_model_canvas
  );
  const sourceSearchCompleted = hasSourceData(analysisData);
  const sourcesRetained = retainedSourceCount(analysisData);
  const context = contextReadinessState(analysisData);

  const legacyIdeaStructured = Boolean(
    analysisData.summary ||
      analysisData.problem ||
      analysisData.problem_solved ||
      analysisData.target_market ||
      analysisData.target_users
  );

  const contextDone = context.hasContract
    ? context.ready
    : legacyIdeaStructured;

  const contextDescription = context.blocked
    ? language === "en"
      ? "The analysis is paused until the missing or ambiguous project details are clarified."
      : "L’analyse est suspendue jusqu’à la clarification des informations manquantes ou ambiguës."
    : context.ready
      ? language === "en"
        ? `The canonical project context is ready for agents${
            context.scorePercent === null
              ? "."
              : ` with a ${context.scorePercent}% context score.`
          }`
        : `Le contexte canonique du projet est prêt pour les agents${
            context.scorePercent === null
              ? "."
              : ` avec un score de contexte de ${context.scorePercent} %.`
          }`
      : language === "en"
        ? "Summary, sector, problem, target users, solution, workflow, and MVP scope."
        : "Résumé, secteur, problème, cibles, solution, workflow et périmètre MVP.";

  return [
    {
      title:
        language === "en"
          ? "Project context validated"
          : "Contexte projet validé",
      description: contextDescription,
      done: contextDone,
      pendingLabel: context.blocked
        ? language === "en"
          ? "Clarification required"
          : "Clarification requise"
        : undefined,
      warning: context.blocked,
    },
    {
      title: language === "en" ? "Market analyzed" : "Marché analysé",
      description:
        language === "en"
          ? "Market study, SWOT and Business Model Canvas."
          : "Étude de marché, SWOT et Business Model Canvas.",
      done: hasMarket,
    },
    {
      title:
        sourcesRetained > 0
          ? language === "en"
            ? "Sources checked"
            : "Sources vérifiées"
          : language === "en"
            ? "Source search completed"
            : "Recherche de sources terminée",
      description:
        sourcesRetained > 0
          ? language === "en"
            ? `${sourcesRetained} compatible external source(s) retained for evidence and competition.`
            : `${sourcesRetained} source(s) externe(s) compatible(s) retenue(s) pour les preuves et la concurrence.`
          : language === "en"
            ? "No compatible external evidence was retained; manual verification and field validation remain required."
            : "Aucune preuve externe compatible n’a été retenue ; une vérification manuelle et une validation terrain restent nécessaires.",
      done: sourceSearchCompleted,
      doneLabel:
        sourceSearchCompleted && sourcesRetained === 0
          ? language === "en"
            ? "Completed — insufficient evidence"
            : "Terminée — preuves insuffisantes"
          : undefined,
    },
    {
      title: language === "en" ? "Personas generated" : "Personas générés",
      description:
        language === "en"
          ? "Customer profiles and field validation questions."
          : "Profils clients et questions de validation terrain.",
      done: hasPersonaData(analysisData),
    },
    {
      title: language === "en" ? "Strategic decision" : "Décision stratégique",
      description:
        language === "en"
          ? "Strategic debate, verdict and action plan."
          : "Débat stratégique, verdict et plan d’action.",
      done: hasStrategicDecision(analysisData),
    },
    {
      title: language === "en" ? "Final verification" : "Vérification finale",
      description:
        language === "en"
          ? "Sourced, estimated or field-validation-required claims."
          : "Affirmations sourcées, estimées ou à valider.",
      done: hasFinalVerification(analysisData),
    },
  ];
}

export default function AnalysisJourneySection({
  analysisData,
  project,
}: {
  analysisData: AnalysisData;
  project: Project;
}) {
  const { lang } = useForgeLanguage();
  const reportLanguage = resolveLanguage(project, analysisData, lang);

  const steps = buildSteps(analysisData, reportLanguage);
  const completed = steps.filter((step) => step.done).length;
  const progress = Math.round((completed / steps.length) * 100);

  return (
    <section className="forge-card p-6">
      <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-sm font-black text-sky-600">
            {reportLanguage === "en"
              ? "Validation journey"
              : "Parcours de validation"}
          </p>

          <h2 className="mt-2 text-2xl font-black tracking-tight text-slate-950">
            {reportLanguage === "en"
              ? "Strategic project progress"
              : "Progression stratégique du projet"}
          </h2>

          <p className="mt-2 text-sm font-semibold leading-6 text-slate-500">
            {cleanText(project.title, reportLanguage)} {"\u2014"}{" "}
            {reportLanguage === "en"
              ? "ForgeAI turns the idea into a decision-ready report step by step."
              : "ForgeAI transforme l’idée en rapport décisionnel étape par étape."}
          </p>
        </div>

        <div className="rounded-3xl bg-gradient-to-br from-sky-400 via-violet-500 to-rose-400 px-6 py-4 text-center text-white shadow-lg shadow-violet-200">
          <p className="text-xs font-black uppercase opacity-80">
            {reportLanguage === "en" ? "Completion" : "Complétion"}
          </p>
          <p className="text-3xl font-black">{progress}%</p>
        </div>
      </div>

      <div className="mt-6 h-2 overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-gradient-to-r from-sky-400 via-violet-500 to-rose-400 transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-3">
        {steps.map((step, index) => (
          <div
            key={step.title}
            className={
              step.warning
                ? "rounded-3xl border border-amber-200 bg-amber-50/80 p-5"
                : step.done
                  ? "rounded-3xl border border-emerald-200 bg-emerald-50/80 p-5"
                  : "rounded-3xl border border-slate-200/70 bg-white/70 p-5"
            }
          >
            <div className="flex items-center gap-3">
              <div
                className={
                  step.warning
                    ? "flex h-9 w-9 items-center justify-center rounded-full bg-amber-500 text-sm font-black text-white"
                    : step.done
                      ? "flex h-9 w-9 items-center justify-center rounded-full bg-emerald-500 text-sm font-black text-white"
                      : "flex h-9 w-9 items-center justify-center rounded-full bg-slate-100 text-sm font-black text-slate-400"
                }
              >
                {step.warning ? "!" : step.done ? "\u2713" : index + 1}
              </div>

              <div>
                <p className="font-black text-slate-900">{step.title}</p>
                <p className="text-xs font-semibold text-slate-400">
                  {step.done
                    ? step.doneLabel ||
                      (reportLanguage === "en" ? "Completed" : "Terminé")
                    : step.pendingLabel ||
                      (reportLanguage === "en" ? "Pending" : "En attente")}
                </p>
              </div>
            </div>

            <p className="mt-3 text-sm font-semibold leading-6 text-slate-500">
              {step.description}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}