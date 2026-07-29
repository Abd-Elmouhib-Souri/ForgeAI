"use client";

import type {
  AnalysisStatus,
  Project,
  ProjectAnalysisResponse,
} from "../_types/project-detail.types";
import { formatDate } from "../_lib/formatters";
import { AnalysisStatusBadge } from "./Badges";
import { MetricCard } from "./UIBlocks";

type ProjectStatusCardsProps = {
  project: Project;
  analysis: ProjectAnalysisResponse | null;
  currentStatus: AnalysisStatus;
  currentStep: string;
  progress: number;
  finalStartupScore: number | null;
  copy: {
    startupScore: string;
    analysis: string;
    step: string;
    progress: string;
    start: string;
    end: string;
    targetRegion: string;
    defaultRegion: string;
  };
};

export default function ProjectStatusCards({
  project,
  analysis,
  currentStatus,
  currentStep,
  progress,
  finalStartupScore,
  copy,
}: ProjectStatusCardsProps) {
  return (
    <div className="grid gap-5 md:grid-cols-3">
      <MetricCard
        title={copy.startupScore}
        value={
          typeof finalStartupScore === "number"
            ? `${finalStartupScore.toFixed(2)}/10`
            : "—"
        }
      />

      <div className="forge-stat-card">
        <span>{copy.analysis}</span>

        <div className="mt-3">
          <AnalysisStatusBadge status={currentStatus} />
        </div>

        <p className="mt-4 text-sm font-semibold leading-6 text-slate-500">
          {copy.step}: {currentStep}
        </p>

        <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full rounded-full bg-gradient-to-r from-sky-400 via-violet-500 to-rose-400 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>

        <p className="mt-3 text-sm font-black text-slate-500">
          {copy.progress}: {progress}%
        </p>

        <p className="mt-4 text-xs font-semibold text-slate-400">
          {copy.start}: {formatDate(analysis?.analysis_started_at)}
        </p>

        <p className="mt-1 text-xs font-semibold text-slate-400">
          {copy.end}: {formatDate(analysis?.analysis_completed_at)}
        </p>
      </div>

      <MetricCard
        title={copy.targetRegion}
        value={project.market_region || copy.defaultRegion}
        small
      />
    </div>
  );
}