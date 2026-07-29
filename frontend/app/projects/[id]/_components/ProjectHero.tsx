"use client";

import Link from "next/link";

import type {
  AnalysisStatus,
  Project,
} from "../_types/project-detail.types";

import { cleanText } from "../_lib/text-cleaning";
import { Badge, AnalysisStatusBadge } from "./Badges";

type ProjectHeroProps = {
  project: Project;
  currentStatus: AnalysisStatus;
  isDeleting: boolean;
  onDelete: () => void;
  copy: {
    backProjects: string;
    report: string;
    edit: string;
    delete: string;
    deleting: string;
    unknownSector: string;
    defaultRegion: string;
  };
};

function getProjectLanguage(project: Project): "fr" | "en" {
  return project.output_language === "en" ? "en" : "fr";
}

export default function ProjectHero({
  project,
  currentStatus,
  isDeleting,
  onDelete,
  copy,
}: ProjectHeroProps) {
  const language = getProjectLanguage(project);

  const title = cleanText(project.title || "Untitled project", language);
  const status = cleanText(project.status || "ideation", language);
  const industry = cleanText(project.industry || copy.unknownSector, language);
  const region = cleanText(project.market_region || copy.defaultRegion, language);

  return (
    <section className="forge-panel p-8">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <Link
            href="/projects"
            className="text-sm font-black text-sky-600 hover:underline"
          >
            ← {cleanText(copy.backProjects, language)}
          </Link>

          <p className="mt-5 text-sm font-black text-sky-600">
            {cleanText(copy.report, language)}
          </p>

          <h1 className="forge-title mt-2">
            <span className="forge-gradient-text">{title}</span>
          </h1>

          <div className="mt-5 flex flex-wrap gap-2">
            <Badge label={status} />
            <Badge label={industry} />
            <Badge label={region} />

            {project.output_language && (
              <Badge label={project.output_language.toUpperCase()} />
            )}

            <AnalysisStatusBadge status={currentStatus} />
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          <Link
            href={`/projects/${project.id}/edit`}
            className="forge-btn forge-btn-secondary"
          >
            {cleanText(copy.edit, language)}
          </Link>

          <button
            type="button"
            onClick={onDelete}
            disabled={isDeleting}
            className="forge-btn border border-red-200 bg-red-50 text-red-600 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isDeleting
              ? cleanText(copy.deleting, language)
              : cleanText(copy.delete, language)}
          </button>
        </div>
      </div>
    </section>
  );
}