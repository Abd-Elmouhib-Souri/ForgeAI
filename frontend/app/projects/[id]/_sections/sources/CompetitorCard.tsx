"use client";

import { useForgeLanguage, type ForgeLang } from "@/lib/language-context";

import type { VerifiedCompetitor } from "../../_types/project-detail.types";

import { cleanText } from "../../_lib/text-cleaning";

function resolveLanguage(
  language: ForgeLang | undefined,
  fallback: ForgeLang
): ForgeLang {
  return language === "en" || language === "fr" ? language : fallback;
}

function regionText(value?: string | null, language: ForgeLang = "fr"): string {
  const normalized = String(value || "").toLowerCase();

  if (language === "en") {
    if (normalized === "local") return "Local";
    if (normalized === "regional") return "Regional";
    if (normalized === "international") return "International";
    return cleanText(value || "—", language);
  }

  if (normalized === "local") return "Local";
  if (normalized === "regional") return "Régional";
  if (normalized === "international") return "International";

  return cleanText(value || "—", language);
}

export default function CompetitorCard({
  competitor,
  language,
}: {
  competitor: VerifiedCompetitor;
  language?: ForgeLang;
}) {
  const { lang } = useForgeLanguage();
  const reportLanguage = resolveLanguage(language, lang);

  const title =
    competitor.name ||
    competitor.title ||
    (reportLanguage === "en" ? "Competitor" : "Concurrent");

  const evidence =
    competitor.evidence ||
    competitor.description ||
    competitor.why_relevant ||
    "";

  const url = competitor.source_url || competitor.url || "";

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="font-black text-slate-900">
        {cleanText(title, reportLanguage)}
      </p>

      <p className="mt-1 text-xs font-semibold text-slate-400">
        {reportLanguage === "en" ? "Region" : "Région"} :{" "}
        {regionText(competitor.region || competitor.region_match, reportLanguage)}
      </p>

      {evidence && (
        <p className="mt-3 text-sm font-semibold leading-6 text-slate-600">
          {cleanText(evidence, reportLanguage)}
        </p>
      )}

      {competitor.pricing && (
        <p className="mt-3 rounded-2xl border border-violet-200 bg-violet-50 p-3 text-xs font-bold text-violet-700">
          {reportLanguage === "en" ? "Pricing signal" : "Signal prix"} :{" "}
          {cleanText(competitor.pricing, reportLanguage)}
        </p>
      )}

      {url && (
        <a
          href={url}
          target="_blank"
          rel="noreferrer"
          className="mt-3 block break-all text-xs font-black text-sky-600 hover:underline"
        >
          {reportLanguage === "en" ? "Open source" : "Ouvrir la source"}
        </a>
      )}
    </div>
  );
}