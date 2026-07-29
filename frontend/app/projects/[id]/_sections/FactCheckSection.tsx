"use client";

import { useForgeLanguage, type ForgeLang } from "@/lib/language-context";

import type {
  FactCheckClaim,
  FactCheckReport,
} from "../_types/project-detail.types";

import { reportCopy } from "../_lib/report-copy";
import { cleanText } from "../_lib/text-cleaning";
import { getPriorityFactClaims } from "../_lib/analysis-helpers";

import { EmptyState } from "../_components/UIBlocks";

function resolveLanguage(
  language: ForgeLang | undefined,
  fallback: ForgeLang
): ForgeLang {
  return language === "en" || language === "fr" ? language : fallback;
}

function confidenceText(value?: string | null, language: ForgeLang = "fr"): string {
  const normalized = String(value || "").toLowerCase();

  if (language === "en") {
    if (normalized.includes("high") || normalized.includes("élev")) return "High";
    if (normalized.includes("medium") || normalized.includes("moy")) return "Medium";
    if (normalized.includes("low") || normalized.includes("faib")) return "Low";
    return cleanText(value || "—", language);
  }

  if (normalized.includes("high") || normalized.includes("élev")) return "Élevée";
  if (normalized.includes("medium") || normalized.includes("moy")) return "Moyenne";
  if (normalized.includes("low") || normalized.includes("faib")) return "Faible";

  return cleanText(value || "—", language);
}

function statusText(value?: string | null, language: ForgeLang = "fr"): string {
  const normalized = String(value || "").toLowerCase();

  if (language === "en") {
    if (normalized.includes("field_validation_required")) {
      return "Field validation required";
    }
    if (normalized.includes("not_confirmed")) return "Not confirmed";
    if (normalized.includes("estimated")) return "Estimated";
    if (normalized.includes("sourced")) return "Sourced";
    if (normalized.includes("verified")) return "Verified";
    return cleanText(value || "To verify", language);
  }

  if (normalized.includes("field_validation_required")) {
    return "Validation terrain requise";
  }
  if (normalized.includes("not_confirmed")) return "Non confirmé";
  if (normalized.includes("estimated")) return "Estimé";
  if (normalized.includes("sourced")) return "Sourcé";
  if (normalized.includes("verified")) return "Vérifié";

  return cleanText(value || "À vérifier", language);
}

function MetricCard({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">
        {label}
      </p>
      <p className="mt-2 text-lg font-black text-slate-900">{value}</p>
    </div>
  );
}

function TextBlock({
  title,
  value,
  language,
}: {
  title: string;
  value?: string | null;
  language: ForgeLang;
}) {
  const cleaned = cleanText(value || "", language);
  if (!cleaned) return null;

  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-black uppercase tracking-[0.2em] text-slate-400">
        {title}
      </p>
      <p className="mt-3 whitespace-pre-wrap text-sm font-semibold leading-7 text-slate-700">
        {cleaned}
      </p>
    </div>
  );
}

function ListPanel({
  title,
  items,
  language,
}: {
  title: string;
  items?: string[];
  language: ForgeLang;
}) {
  const cleanedItems = (items || [])
    .map((item) => cleanText(item, language))
    .filter(Boolean);

  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-black uppercase tracking-[0.2em] text-slate-400">
        {title}
      </p>

      {cleanedItems.length > 0 ? (
        <ul className="mt-3 space-y-2">
          {cleanedItems.map((item, index) => (
            <li
              key={`${title}-${index}`}
              className="rounded-2xl bg-slate-50 px-4 py-3 text-sm font-semibold leading-6 text-slate-700"
            >
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm font-semibold text-slate-400">—</p>
      )}
    </div>
  );
}

function ClaimCard({
  claim,
  index,
  language,
}: {
  claim: FactCheckClaim;
  index: number;
  language: ForgeLang;
}) {
  const label =
    claim.public_status ||
    claim.status ||
    (language === "en" ? "To verify" : "À vérifier");

  const confidence =
    claim.public_confidence ||
    claim.confidence ||
    (language === "en" ? "Medium" : "Moyenne");

  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.2em] text-sky-500">
            {language === "en" ? "Claim" : "Affirmation"} {index + 1}
          </p>

          <h4 className="mt-2 text-base font-black leading-7 text-slate-950">
            {cleanText(claim.claim || "—", language)}
          </h4>
        </div>

        <div className="flex flex-wrap gap-2">
          <span className="forge-badge">{statusText(label, language)}</span>
          <span className="forge-badge">
            {confidenceText(confidence, language)}
          </span>
          {claim.category && (
            <span className="forge-badge">
              {cleanText(claim.category.replaceAll("_", " "), language)}
            </span>
          )}
        </div>
      </div>

      {claim.evidence && claim.evidence.length > 0 && (
        <ListPanel
          title={language === "en" ? "Evidence" : "Éléments de preuve"}
          items={claim.evidence}
          language={language}
        />
      )}

      {claim.correction && (
        <div className="mt-4">
          <TextBlock
            title={language === "en" ? "Correction" : "Correction"}
            value={claim.correction}
            language={language}
          />
        </div>
      )}
    </div>
  );
}

export default function FactCheckSection({
  factCheckReport,
  language,
}: {
  factCheckReport?: FactCheckReport;
  language?: ForgeLang;
}) {
  const { lang } = useForgeLanguage();
  const reportLanguage = resolveLanguage(language, lang);
  const t = reportCopy[reportLanguage];

  if (!factCheckReport) {
    return (
      <EmptyState
        text={
          reportLanguage === "en"
            ? "Fact checking is not available."
            : "Vérification des affirmations non disponible."
        }
      />
    );
  }

  const claims = getPriorityFactClaims(factCheckReport.claims || [], 6);

  return (
    <div className="space-y-5">
      <div className="grid gap-3 md:grid-cols-4">
        <MetricCard
          label={reportLanguage === "en" ? "Status" : "Statut"}
          value={cleanText(factCheckReport.status || "—", reportLanguage)}
        />

        <MetricCard
          label={t.sourceConfidence}
          value={confidenceText(
            factCheckReport.global_confidence ||
              factCheckReport.confidence_level ||
              factCheckReport.source_summary?.source_confidence,
            reportLanguage
          )}
        />

        <MetricCard
          label={reportLanguage === "en" ? "Claims" : "Affirmations"}
          value={String(factCheckReport.claims?.length || 0)}
        />

        <MetricCard
          label={reportLanguage === "en" ? "Sources" : "Sources"}
          value={String(factCheckReport.source_summary?.total_sources || 0)}
        />
      </div>

      <TextBlock
        title={t.factCheck}
        value={
          factCheckReport.fact_check_summary ||
          factCheckReport.summary ||
          t.factCheckSummary
        }
        language={reportLanguage}
      />

      {claims.length > 0 ? (
        <div className="space-y-4">
          {claims.map((claim, index) => (
            <ClaimCard
              key={`${claim.category || "claim"}-${index}`}
              claim={claim}
              index={index}
              language={reportLanguage}
            />
          ))}
        </div>
      ) : (
        <EmptyState
          text={
            reportLanguage === "en"
              ? "No priority claim was identified."
              : "Aucune affirmation prioritaire identifiée."
          }
        />
      )}

      <div className="grid gap-5 md:grid-cols-2">
        <ListPanel
          title={t.warnings}
          items={factCheckReport.warnings || factCheckReport.red_flags || []}
          language={reportLanguage}
        />

        <ListPanel
          title={t.nextChecks}
          items={
            factCheckReport.recommended_next_checks ||
            factCheckReport.recommended_validation ||
            []
          }
          language={reportLanguage}
        />

        <ListPanel
          title={t.limitationsIdentified}
          items={factCheckReport.limitations || []}
          language={reportLanguage}
        />
      </div>
    </div>
  );
}
