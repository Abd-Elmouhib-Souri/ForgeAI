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

  const personasCount = personaBuilder.personas?.length || 0;
  const hasPrimaryPersona = Boolean(personaBuilder.primary_persona);

  return personasCount > 0 || hasPrimaryPersona;
}

function hasStrategicDecision(analysisData: AnalysisData): boolean {
  const debateRoom = analysisData.debate_room;
  const startupScore = analysisData.startup_score;

  const hasDebateRounds = Boolean(debateRoom?.rounds?.length);
  const hasJudge = Boolean(debateRoom?.judge);
  const hasJudgeDecision = Boolean(
    debateRoom?.judge?.verdict ||
      debateRoom?.judge?.final_recommendation ||
      debateRoom?.judge?.go_no_go_conditions?.length ||
      debateRoom?.judge?.next_actions?.length ||
      debateRoom?.judge?.action_plan?.length
  );

  const hasStartupDecision = Boolean(
    startupScore?.verdict ||
      startupScore?.summary ||
      startupScore?.next_actions?.length
  );

  return hasDebateRounds || hasJudge || hasJudgeDecision || hasStartupDecision;
}

function hasSourceData(analysisData: AnalysisData): boolean {
  if (analysisData.forgecrawler) return true;

  const competitiveAnalysis = analysisData.competitive_analysis;
  if (!competitiveAnalysis) return false;

  const record = competitiveAnalysis as Record<string, unknown>;

  const sourceKeys = [
    "market_gap",
    "coverage_status",
    "source_confidence",
    "confidence_level",
    "verified_competitors",
    "local_competitors",
    "direct_competitors",
    "adjacent_solutions",
    "local_adjacent_solutions",
    "regional_benchmarks",
    "international_benchmarks",
    "market_sources",
    "close_solutions",
    "indirect_competitors",
    "competitive_advantages",
    "external_sources",
    "sources",
  ];

  return sourceKeys.some((key) => {
    const value = record[key];

    if (Array.isArray(value)) {
      return value.length > 0;
    }

    if (typeof value === "string") {
      return value.trim().length > 0;
    }

    if (typeof value === "number") {
      return value > 0;
    }

    return Boolean(value);
  });
}

function buildSteps(
  analysisData: AnalysisData,
  language: ForgeLang
): JourneyStep[] {
  const hasMarket =
    Boolean(analysisData.market_study) ||
    Boolean(analysisData.swot) ||
    Boolean(analysisData.business_model_canvas);

  return [
    {
      title: language === "en" ? "Idea structured" : "Idée structurée",
      description:
        language === "en"
          ? "Summary, sector, problem, target and solution."
          : "Résumé, secteur, problème, cible et solution.",
      done: Boolean(
        analysisData.summary ||
          analysisData.problem ||
          analysisData.problem_solved ||
          analysisData.target_market ||
          analysisData.target_users
      ),
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
      title: language === "en" ? "Sources checked" : "Sources vérifiées",
      description:
        language === "en"
          ? "External sources, benchmarks and competition."
          : "Sources externes, benchmarks et concurrence.",
      done: hasSourceData(analysisData),
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
      done: Boolean(analysisData.fact_check_report),
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
              step.done
                ? "rounded-3xl border border-emerald-200 bg-emerald-50/80 p-5"
                : "rounded-3xl border border-slate-200/70 bg-white/70 p-5"
            }
          >
            <div className="flex items-center gap-3">
              <div
                className={
                  step.done
                    ? "flex h-9 w-9 items-center justify-center rounded-full bg-emerald-500 text-sm font-black text-white"
                    : "flex h-9 w-9 items-center justify-center rounded-full bg-slate-100 text-sm font-black text-slate-400"
                }
              >
                {step.done ? "\u2713" : index + 1}
              </div>

              <div>
                <p className="font-black text-slate-900">{step.title}</p>
                <p className="text-xs font-semibold text-slate-400">
                  {step.done
                    ? reportLanguage === "en"
                      ? "Completed"
                      : "Terminé"
                    : reportLanguage === "en"
                      ? "Pending"
                      : "En attente"}
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