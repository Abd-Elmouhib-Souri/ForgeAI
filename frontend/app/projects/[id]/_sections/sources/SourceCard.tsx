"use client";

import { useForgeLanguage, type ForgeLang } from "@/lib/language-context";

import type {
  SourceDisplayContext,
  SourceItem,
} from "../../_types/project-detail.types";

import { reportCopy } from "../../_lib/report-copy";
import {
  getPublicSourceReason,
  getPublicSourceSnippet,
} from "../../_lib/analysis-helpers";
import { cleanText } from "../../_lib/text-cleaning";

function resolveLanguage(
  language: ForgeLang | undefined,
  fallback: ForgeLang
): ForgeLang {
  return language === "en" || language === "fr" ? language : fallback;
}

function sourceTypeText(value?: string | null, language: ForgeLang = "fr"): string {
  const normalized = String(value || "").toLowerCase();

  const en: Record<string, string> = {
    competitor: "Competitor",
    pricing_page: "Pricing page",
    adjacent_solution: "Adjacent solution",
    market_article: "Market source",
    directory: "Directory",
    regulation: "Regulation",
    official_source: "Official source",
    local_ecosystem: "Local ecosystem",
    technology_benchmark: "Technology benchmark",
    benchmark: "Benchmark",
  };

  const fr: Record<string, string> = {
    competitor: "Concurrent",
    pricing_page: "Page tarifaire",
    adjacent_solution: "Solution adjacente",
    market_article: "Source marché",
    directory: "Annuaire",
    regulation: "Réglementation",
    official_source: "Source officielle",
    local_ecosystem: "Écosystème local",
    technology_benchmark: "Benchmark technologique",
    benchmark: "Benchmark",
  };

  const map = language === "en" ? en : fr;

  return map[normalized] || cleanText(value || "Source", language);
}

function regionText(
  value: string | null | undefined,
  language: ForgeLang,
  context: SourceDisplayContext
): string {
  const normalized = String(value || "").toLowerCase();

  if (context.isGlobal && normalized === "local") {
    return language === "en" ? "Market to define" : "Marché à préciser";
  }

  if (language === "en") {
    if (normalized === "local") return "Local";
    if (normalized === "regional") return "Regional";
    if (normalized === "international") return "International";
    return "Unknown region";
  }

  if (normalized === "local") return "Local";
  if (normalized === "regional") return "Régional";
  if (normalized === "international") return "International";
  return "Région inconnue";
}

function SummaryBlock({
  title,
  value,
  language,
}: {
  title: string;
  value: string;
  language: ForgeLang;
}) {
  if (!value) return null;

  return (
    <div className="mt-3 rounded-2xl border border-slate-200 bg-slate-50 p-3">
      <p className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">
        {title}
      </p>
      <p className="mt-2 text-xs font-semibold leading-5 text-slate-600">
        {cleanText(value, language)}
      </p>
    </div>
  );
}

export default function SourceCard({
  source,
  index,
  context,
  language,
}: {
  source: SourceItem;
  index: number;
  context: SourceDisplayContext;
  language?: ForgeLang;
}) {
  const { lang } = useForgeLanguage();
  const reportLanguage = resolveLanguage(language, lang);
  const t = reportCopy[reportLanguage];

  if (source.rejected || source.internal_only) {
    return null;
  }

  const reason = getPublicSourceReason(source, reportLanguage);
  const snippet = getPublicSourceSnippet(source, reportLanguage);

  const title = cleanText(
    source.title ||
      (reportLanguage === "en" ? "External source" : "Source externe"),
    reportLanguage
  );

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-sm font-black text-slate-900">
            {index + 1}. {title}
          </p>

          {source.url && (
            <a
              href={source.url}
              target="_blank"
              rel="noreferrer"
              className="mt-1 block break-all text-xs font-black text-sky-600 hover:underline"
            >
              {t.openSource}
            </a>
          )}
        </div>

        <div className="flex flex-wrap gap-2">
          <span className="forge-badge">
            {sourceTypeText(source.source_type, reportLanguage)}
          </span>

          <span className="forge-badge">
            {regionText(source.region_match, reportLanguage, context)}
          </span>

          {source.confidence && (
            <span className="forge-badge">
              {cleanText(source.confidence, reportLanguage)}
            </span>
          )}

          {typeof source.source_relevance_score === "number" && (
            <span className="forge-badge">
              {Math.round(source.source_relevance_score * 100)}%
            </span>
          )}
        </div>
      </div>

      {reason && (
        <SummaryBlock
          title={reportLanguage === "en" ? "Why relevant" : "Pourquoi pertinent"}
          value={reason}
          language={reportLanguage}
        />
      )}

      {snippet && (
        <SummaryBlock
          title={reportLanguage === "en" ? "Source summary" : "Résumé source"}
          value={snippet}
          language={reportLanguage}
        />
      )}
    </div>
  );
}