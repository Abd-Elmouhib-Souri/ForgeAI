"use client";

import { useForgeLanguage, type ForgeLang } from "@/lib/language-context";

import type {
  FactCheckClaim,
  FactCheckEvidence,
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

function confidenceText(
  value?: string | null,
  language: ForgeLang = "fr"
): string {
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

function statusText(
  value?: string | null,
  language: ForgeLang = "fr"
): string {
  const normalized = String(value || "").toLowerCase();

  if (language === "en") {
    if (normalized.includes("field_validation_required")) {
      return "Field validation required";
    }
    if (normalized.includes("not_confirmed")) return "Not confirmed";
    if (normalized.includes("recommendation")) return "Recommendation";
    if (normalized.includes("audit_conclusion")) return "Audit conclusion";
    if (normalized.includes("project_input")) return "Provided by the project";
    if (normalized.includes("estimated")) return "Estimated";
    if (normalized.includes("sourced")) return "Sourced";
    if (normalized.includes("verified")) return "Verified";
    return cleanText(value || "To verify", language);
  }

  if (normalized.includes("field_validation_required")) {
    return "Validation terrain requise";
  }
  if (normalized.includes("not_confirmed")) return "Non confirmé";
  if (normalized.includes("recommendation")) return "Recommandation";
  if (normalized.includes("audit_conclusion")) return "Conclusion d’audit";
  if (normalized.includes("project_input")) return "Fourni par le projet";
  if (normalized.includes("estimated")) return "Estimé";
  if (normalized.includes("sourced")) return "Sourcé";
  if (normalized.includes("verified")) return "Vérifié";

  return cleanText(value || "À vérifier", language);
}

function formatEvidenceCategory(
  value: string,
  language: ForgeLang
): string {
  const labels: Record<string, Record<ForgeLang, string>> = {
    market_size: { fr: "Taille du marché", en: "Market size" },
    market_demand: { fr: "Demande marché", en: "Market demand" },
    problem_context: { fr: "Contexte problème", en: "Problem context" },
    solution_benchmark: { fr: "Benchmark solution", en: "Solution benchmark" },
    competitor_product: { fr: "Produit concurrent", en: "Competitor product" },
    pricing: { fr: "Tarification", en: "Pricing" },
    regulation: { fr: "Réglementation", en: "Regulation" },
    regional_context: { fr: "Contexte régional", en: "Regional context" },
    sector_context: { fr: "Contexte sectoriel", en: "Sector context" },
    local_market_signal: { fr: "Signal de marché local", en: "Local market signal" },
    technology_benchmark: { fr: "Benchmark technologique", en: "Technology benchmark" },
    current_alternatives: { fr: "Alternatives actuelles", en: "Current alternatives" },
    ecosystem_signal: { fr: "Signal d’écosystème", en: "Ecosystem signal" },
    local_ecosystem: { fr: "Écosystème local", en: "Local ecosystem" },
  };

  return labels[value]?.[language] || cleanText(value.replaceAll("_", " "), language);
}

function sourceTypeText(value: string, language: ForgeLang): string {
  const labels: Record<string, Record<ForgeLang, string>> = {
    source: { fr: "Source de preuve", en: "Evidence source" },
    market_article: { fr: "Source de marché", en: "Market source" },
    market_evidence: { fr: "Preuve de marché", en: "Market evidence" },
    adjacent_solution: { fr: "Solution adjacente", en: "Adjacent solution" },
    technology_benchmark: { fr: "Benchmark technologique", en: "Technology benchmark" },
    local_ecosystem: { fr: "Écosystème local", en: "Local ecosystem" },
    competitor: { fr: "Produit concurrent", en: "Competitor product" },
    direct_competitor: { fr: "Concurrent direct", en: "Direct competitor" },
    official_source: { fr: "Source officielle", en: "Official source" },
    regulation: { fr: "Source réglementaire", en: "Regulatory source" },
    directory: { fr: "Annuaire sectoriel", en: "Sector directory" },
  };
  const key = String(value || "").trim().toLowerCase();
  return labels[key]?.[language] || cleanText(key.replaceAll("_", " "), language);
}

function regionText(value: string, language: ForgeLang): string {
  const labels: Record<string, Record<ForgeLang, string>> = {
    local: { fr: "Local", en: "Local" },
    regional: { fr: "Régional", en: "Regional" },
    international: { fr: "International", en: "International" },
    unknown: { fr: "Région non confirmée", en: "Region not confirmed" },
  };
  const key = String(value || "").trim().toLowerCase();
  return labels[key]?.[language] || cleanText(value, language);
}

function claimCategoryText(value: string, language: ForgeLang): string {
  const labels: Record<string, Record<ForgeLang, string>> = {
    finance: { fr: "Finance", en: "Finance" },
    solution: { fr: "Solution", en: "Solution" },
    solution_hypothesis: { fr: "Hypothèse de solution", en: "Solution hypothesis" },
    problem: { fr: "Problème", en: "Problem" },
    market_size: { fr: "Taille du marché", en: "Market size" },
    market_demand: { fr: "Demande du marché", en: "Market demand" },
    market_context: { fr: "Contexte de marché", en: "Market context" },
    recommendation: { fr: "Recommandation stratégique", en: "Strategic recommendation" },
    evidence_audit: { fr: "Audit des preuves", en: "Evidence audit" },
    project_input: { fr: "Contexte fourni", en: "Provided context" },
    local_competition: { fr: "Concurrence locale", en: "Local competition" },
    general: { fr: "Général", en: "General" },
  };
  const key = String(value || "").trim().toLowerCase();
  return labels[key]?.[language] || cleanText(key.replaceAll("_", " "), language);
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
    .filter((item): item is string => typeof item === "string")
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

function normalizeEvidence(
  value: FactCheckEvidence | string
): FactCheckEvidence {
  if (typeof value === "string") {
    return { title: value };
  }
  return value || {};
}

function isGenericEvidenceTitle(value?: string | null): boolean {
  const normalized = String(value || "")
    .trim()
    .toLowerCase();

  return [
    "",
    "source",
    "external source",
    "source externe",
    "evidence source",
    "source de preuve",
  ].includes(normalized);
}

function domainLabel(url?: string | null): string {
  if (!url) return "";

  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}

function evidenceTitle(
  item: FactCheckEvidence,
  language: ForgeLang
): string {
  const candidates = [
    item.source_title,
    item.title,
    item.name,
    item.vendor_name,
  ];

  for (const candidate of candidates) {
    if (!isGenericEvidenceTitle(candidate)) {
      return cleanText(String(candidate), language);
    }
  }

  const domain = domainLabel(item.url);
  if (domain) return domain;

  return language === "en" ? "Evidence source" : "Source de preuve";
}

function EvidenceCard({
  evidence,
  language,
}: {
  evidence: FactCheckEvidence | string;
  language: ForgeLang;
}) {
  const item = normalizeEvidence(evidence);
  const title = evidenceTitle(item, language);
  const reason = cleanText(
    item.why_relevant || item.public_reason || "",
    language
  );
  const categories = (item.evidence_categories || []).filter(Boolean);
  const score =
    typeof item.source_relevance_score === "number" &&
    Number.isFinite(item.source_relevance_score)
      ? `${Math.round(item.source_relevance_score * 100)}%`
      : null;

  return (
    <article className="rounded-2xl border border-sky-100 bg-sky-50/60 p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          <p className="break-words text-sm font-black leading-6 text-slate-900">
            {title}
          </p>
          {reason && (
            <p className="mt-2 text-xs font-semibold leading-5 text-slate-600">
              {reason}
            </p>
          )}
        </div>

        {item.url && (
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 rounded-xl bg-white px-3 py-2 text-xs font-black text-sky-700 shadow-sm transition hover:bg-sky-100"
          >
            {language === "en" ? "Open source" : "Ouvrir la source"}
          </a>
        )}
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {item.source_type && (
          <span className="forge-badge">
            {sourceTypeText(item.source_type, language)}
          </span>
        )}
        {item.region_match && (
          <span className="forge-badge">
            {regionText(item.region_match, language)}
          </span>
        )}
        {item.confidence && (
          <span className="forge-badge">
            {confidenceText(item.confidence, language)}
          </span>
        )}
        {score && <span className="forge-badge">{score}</span>}
        {item.is_direct_competitor && (
          <span className="forge-badge">
            {language === "en" ? "Verified direct competitor" : "Concurrent direct vérifié"}
          </span>
        )}
        {categories.map((category) => (
          <span key={category} className="forge-badge">
            {formatEvidenceCategory(category, language)}
          </span>
        ))}
      </div>
    </article>
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

  const rawEvidence = (claim.evidence || []).filter(Boolean);
  const normalizedStatus = String(claim.status || "").toLowerCase();
  const consultedEvidence =
    normalizedStatus === "not_confirmed" ||
    normalizedStatus === "field_validation_required" ||
    claim.evidence_kind === "consulted_insufficient";

  const evidence = consultedEvidence ? [] : rawEvidence;
  const consultedCandidates = [
    ...(claim.consulted_sources || []),
    ...(consultedEvidence ? rawEvidence : []),
  ].filter(Boolean);

  const consultedSources = consultedCandidates.filter((item, index, all) => {
    const normalized = normalizeEvidence(item);
    const key = `${
      normalized.url || ""
    }|${normalized.display_title || normalized.source_title || normalized.title || ""}`;
    return (
      all.findIndex((candidate) => {
        const current = normalizeEvidence(candidate);
        const currentKey = `${
          current.url || ""
        }|${current.display_title || current.source_title || current.title || ""}`;
        return currentKey === key;
      }) === index
    );
  });

  const evidenceHeading =
    normalizedStatus === "estimated"
      ? language === "en"
        ? "Context sources"
        : "Sources de contexte"
      : language === "en"
        ? "Evidence"
        : "Éléments de preuve";

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
              {claimCategoryText(claim.category, language)}
            </span>
          )}
        </div>
      </div>

      {evidence.length > 0 && (
        <div className="mt-4 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-black uppercase tracking-[0.2em] text-slate-400">
            {evidenceHeading}
          </p>
          <div className="mt-3 space-y-3">
            {evidence.map((item, evidenceIndex) => (
              <EvidenceCard
                key={`${claim.category || "claim"}-${evidenceIndex}`}
                evidence={item}
                language={language}
              />
            ))}
          </div>
        </div>
      )}

      {consultedSources.length > 0 && (
        <div className="mt-4 rounded-3xl border border-amber-200 bg-amber-50/60 p-5 shadow-sm">
          <p className="text-xs font-black uppercase tracking-[0.2em] text-amber-700">
            {language === "en"
              ? "Sources consulted, but insufficient"
              : "Sources consultées, mais insuffisantes"}
          </p>
          <div className="mt-3 space-y-3">
            {consultedSources.map((item, evidenceIndex) => (
              <EvidenceCard
                key={`consulted-${claim.category || "claim"}-${evidenceIndex}`}
                evidence={item}
                language={language}
              />
            ))}
          </div>
        </div>
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

  const claims = getPriorityFactClaims(factCheckReport.claims || []);
  const totalSources =
    factCheckReport.source_summary?.total_sources ??
    factCheckReport.source_count ??
    0;
  const relevantSources =
    factCheckReport.source_summary?.relevant_sources ??
    factCheckReport.relevant_source_count ??
    0;

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
          label={reportLanguage === "en" ? "Relevant sources" : "Sources pertinentes"}
          value={`${relevantSources}/${totalSources}`}
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
          <p className="text-sm font-semibold text-slate-500">
            {reportLanguage === "en"
              ? `${claims.length} claim(s) displayed.`
              : `${claims.length} affirmation(s) affichée(s).`}
          </p>
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