"use client";

import type { AnalysisData, Project } from "../_types/project-detail.types";
import { normalizeList, riskLevelLabel, verdictLabel } from "../_lib/formatters";
import { getConcreteSolution } from "../_lib/analysis-helpers";
import {
  AnalysisBlock,
  EmptyState,
  ListBlock,
  MiniMetric,
  ScoreBar,
  WarningList,
} from "../_components/UIBlocks";

type FinalReportPreviewProps = {
  analysisData: AnalysisData | null;
  project: Project;
  copy: {
    reportTitle: string;
    reportSubtitle: string;
    noReport: string;
    summary: string;
    problem: string;
    solution: string;
    targetMarket: string;
    technologies: string;
    improvements: string;
    risks: string;
    startupScore: string;
    verdict: string;
    riskLevel: string;
    nextActions: string;
    limitations: string;
    marketStudy: string;
    swot: string;
    bmc: string;
    competitors: string;
    personas: string;
    debate: string;
    factCheck: string;
    available: string;
    missing: string;
  };
};

export default function FinalReportPreview({
  analysisData,
  project,
  copy,
}: FinalReportPreviewProps) {
  if (!analysisData) {
    return <EmptyState text={copy.noReport} />;
  }

  const judge = analysisData.debate_room?.judge;
  const startupScore = analysisData.startup_score;

  const sections = [
    {
      label: copy.marketStudy,
      available: Boolean(analysisData.market_study),
    },
    {
      label: copy.swot,
      available: Boolean(analysisData.swot),
    },
    {
      label: copy.bmc,
      available: Boolean(analysisData.business_model_canvas),
    },
    {
      label: copy.competitors,
      available: Boolean(analysisData.competitive_analysis),
    },
    {
      label: copy.personas,
      available: Boolean(analysisData.personas),
    },
    {
      label: copy.debate,
      available: Boolean(analysisData.debate_room),
    },
    {
      label: copy.factCheck,
      available: Boolean(analysisData.fact_check_report),
    },
  ];

  const limitations = [
    ...(analysisData.public_limitations || []),
    ...(analysisData.data_limitations ? [analysisData.data_limitations] : []),
    ...(analysisData.competitive_analysis?.limitations || []),
    ...(analysisData.forgecrawler?.limitations || []),
  ];

  return (
    <section className="space-y-6">
      <div className="forge-panel p-7">
        <p className="text-sm font-black text-sky-600">{copy.reportTitle}</p>
        <h2 className="mt-2 text-3xl font-black tracking-tight text-slate-950">
          {project.title}
        </h2>
        <p className="forge-subtitle">{copy.reportSubtitle}</p>

        <div className="mt-6 grid gap-3 md:grid-cols-3">
          <MiniMetric
            label="Secteur"
            value={analysisData.detected_sector || project.industry || "—"}
          />
          <MiniMetric
            label="Région"
            value={analysisData.target_region || project.market_region || "—"}
          />
          <MiniMetric
            label={copy.verdict}
            value={verdictLabel(judge?.verdict)}
          />
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <AnalysisBlock title={copy.summary} value={analysisData.summary} />
        <AnalysisBlock
          title={copy.problem}
          value={analysisData.problem || analysisData.problem_solved}
        />
        <AnalysisBlock
          title={copy.solution}
          value={getConcreteSolution(analysisData, project)}
        />
        <AnalysisBlock
          title={copy.targetMarket}
          value={
            analysisData.target_users ||
            analysisData.target_market ||
            analysisData.market_study?.target_market
          }
        />
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <ListBlock
          title={copy.technologies}
          items={analysisData.recommended_technologies || []}
        />
        <ListBlock
          title={copy.improvements}
          items={analysisData.improvement_suggestions || []}
        />
        <ListBlock
          title={copy.risks}
          items={normalizeList(analysisData.risks)}
        />
        <ListBlock
          title={copy.nextActions}
          items={judge?.next_actions || judge?.action_plan || []}
        />
      </div>

      {startupScore && (
        <div className="forge-card p-6">
          <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <h3 className="text-2xl font-black tracking-tight text-slate-950">
                {copy.startupScore}
              </h3>
              <p className="mt-1 text-sm font-semibold text-slate-500">
                {startupScore.score_explanation || "—"}
              </p>
            </div>

            <div className="rounded-3xl bg-gradient-to-br from-sky-400 via-violet-500 to-rose-400 px-6 py-4 text-center text-white shadow-lg shadow-violet-200">
              <p className="text-xs font-black uppercase opacity-80">
                Global
              </p>
              <p className="text-3xl font-black">
                {typeof startupScore.global_score === "number"
                  ? `${startupScore.global_score.toFixed(2)}/10`
                  : "—"}
              </p>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <ScoreBar label="Innovation" value={startupScore.innovation} />
            <ScoreBar label="Faisabilité" value={startupScore.feasibility} />
            <ScoreBar label="Rentabilité" value={startupScore.profitability} />
            <ScoreBar label="Scalabilité" value={startupScore.scalability} />
          </div>
        </div>
      )}

      <div className="forge-card p-6">
        <h3 className="text-2xl font-black tracking-tight text-slate-950">
          Modules du rapport
        </h3>

        <div className="mt-5 grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {sections.map((section) => (
            <div key={section.label} className="forge-status-row">
              <div className="flex items-center gap-3">
                <span className="forge-check">
                  {section.available ? "✓" : "•"}
                </span>
                <span className="text-sm font-bold text-slate-600">
                  {section.label}
                </span>
              </div>

              <strong
                className={
                  section.available
                    ? "text-sm font-black text-emerald-600"
                    : "text-sm font-black text-slate-400"
                }
              >
                {section.available ? copy.available : copy.missing}
              </strong>
            </div>
          ))}
        </div>
      </div>

      {judge && (
        <div className="grid gap-5 md:grid-cols-2">
          <AnalysisBlock
            title={copy.verdict}
            value={judge.final_recommendation}
          />
          <AnalysisBlock
            title={copy.riskLevel}
            value={riskLevelLabel(judge.risk_level)}
          />
        </div>
      )}

      {limitations.length > 0 && (
        <WarningList title={copy.limitations} items={limitations} />
      )}
    </section>
  );
}