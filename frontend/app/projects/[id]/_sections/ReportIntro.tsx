"use client";

import { useForgeLanguage, type ForgeLang } from "@/lib/language-context";

import type { AnalysisData, Project } from "../_types/project-detail.types";

import { reportCopy } from "../_lib/report-copy";
import { formatScore } from "../_lib/formatters";
import {
  getOfficialStartupScore,
  getReportLanguage,
} from "../_lib/analysis-helpers";
import { cleanText } from "../_lib/text-cleaning";

import { MiniMetric } from "../_components/UIBlocks";

function verdictText(value?: string | null, language: ForgeLang = "fr"): string {
  const normalized = String(value || "").toLowerCase();

  if (language === "en") {
    if (normalized.includes("conditional")) return "Continue with conditions";
    if (normalized.includes("pivot")) return "Pivot";
    if (normalized.includes("continue") || normalized.includes("poursuivre")) {
      return "Continue";
    }
    if (normalized.includes("stop") || normalized.includes("abandon")) {
      return "Stop";
    }
    return cleanText(
      value || "Decision pending",
      language
    );
  }

  if (normalized.includes("conditional")) return "Poursuivre sous conditions";
  if (normalized.includes("pivot")) return "Pivoter";
  if (normalized.includes("continue") || normalized.includes("poursuivre")) {
    return "Poursuivre";
  }
  if (normalized.includes("stop") || normalized.includes("abandon")) {
    return "Abandonner";
  }

  return cleanText(
    value || "Décision en attente",
    language
  );
}

export default function ReportIntro({
  analysisData,
  project,
}: {
  analysisData: AnalysisData;
  project: Project;
}) {
  const { lang } = useForgeLanguage();
  const reportLanguage = getReportLanguage(project, analysisData, lang);
  const t = reportCopy[reportLanguage];

  const finalReport =
    analysisData.final_report;

  const decision =
    finalReport?.decision;

  const score = getOfficialStartupScore(
    analysisData,
    project.startup_score ?? null
  );

  const verdict =
    decision?.verdict_code ||
    decision?.verdict;

  return (
    <section className="forge-panel p-7">
      <p className="text-sm font-black text-sky-600">{t.finalUserReport}</p>

      <h2 className="mt-2 text-3xl font-black tracking-tight text-slate-950">
        {t.completeReport}
      </h2>

      <p className="forge-subtitle">{t.completeReportText}</p>

      <div className="mt-6 grid gap-3 md:grid-cols-4">
        <MiniMetric
          label={t.sector}
          value={cleanText(
            finalReport?.context?.sector ||
              project.industry ||
              "\u2014",
            reportLanguage
          )}
        />
        <MiniMetric
          label={t.region}
          value={cleanText(
            finalReport?.context?.target_region ||
              project.market_region ||
              "\u2014",
            reportLanguage
          )}
        />
        <MiniMetric label={t.startupScore} value={formatScore(
            score ?? null
          )} />
        <MiniMetric
          label={t.verdict}
          value={verdictText(verdict, reportLanguage)}
        />
      </div>
    </section>
  );
}
