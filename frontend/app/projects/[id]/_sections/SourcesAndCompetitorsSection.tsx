"use client";

import { useForgeLanguage, type ForgeLang } from "@/lib/language-context";

import type {
  AnalysisData,
  Project,
  SourceDisplayContext,
  SourceItem,
  VerifiedCompetitor,
} from "../_types/project-detail.types";

import { reportCopy } from "../_lib/report-copy";
import {
  getPublicDisplaySources,
  getPublicTextItems,
  getSourceDisplayContext,
} from "../_lib/analysis-helpers";
import { cleanText } from "../_lib/text-cleaning";

import { EmptyState } from "../_components/UIBlocks";
import CompetitorCard from "./sources/CompetitorCard";
import SourceCard from "./sources/SourceCard";

function resolveLanguage(
  language: ForgeLang | undefined,
  fallback: ForgeLang,
  project: Project,
  analysisData: AnalysisData
): ForgeLang {
  if (language === "en" || language === "fr") return language;
  if (project.output_language === "en") return "en";
  if (project.output_language === "fr") return "fr";
  if (analysisData.output_language === "en") return "en";
  if (analysisData.output_language === "fr") return "fr";
  return fallback;
}

function asArray<T = unknown>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

function canonicalSourceKey(source: SourceItem): string {
  const rawUrl = String(source.url || "").trim();
  if (rawUrl) {
    try {
      const parsed = new URL(rawUrl);
      const host = parsed.hostname.toLowerCase().replace(/^www\./, "");
      const path = parsed.pathname.replace(/\/{2,}/g, "/").replace(/\/$/, "");
      return `url:https://${host}${path}`;
    } catch {
      // Fall through to stable non-URL identifiers.
    }
  }

  const sourceType = String(source.source_type || "").toLowerCase();
  const sourceRole = String(source.source_role || "").toLowerCase();
  const vendorKey = String(source.vendor_key || "").trim().toLowerCase();
  const vendorScoped =
    ["competitor", "pricing_page", "adjacent_solution", "technology_benchmark"].includes(sourceType) ||
    [
      "direct_competitor",
      "adjacent_solution",
      "regional_benchmark",
      "international_benchmark",
      "technology_provider",
    ].includes(sourceRole);

  if (vendorScoped && vendorKey) return `vendor:${vendorKey}`;

  const canonicalId = String(source.canonical_source_id || "").trim().toLowerCase();
  if (canonicalId) return `id:${canonicalId}`;

  return String(source.title || "").trim().toLowerCase();
}

function uniqueSources(sources: SourceItem[]): SourceItem[] {
  const result: SourceItem[] = [];
  const seen = new Set<string>();

  for (const source of sources) {
    const key = canonicalSourceKey(source);
    if (!key || seen.has(key)) continue;
    seen.add(key);
    result.push(source);
  }

  return result;
}

function uniqueCompetitors(items: VerifiedCompetitor[]): VerifiedCompetitor[] {
  const result: VerifiedCompetitor[] = [];
  const seen = new Set<string>();

  for (const item of items) {
    const key = String(
      item.vendor_key ||
        item.canonical_vendor_domain ||
        item.url ||
        item.source_url ||
        item.name ||
        item.title ||
        ""
    )
      .trim()
      .toLowerCase();

    if (!key) continue;
    if (seen.has(key)) continue;

    seen.add(key);
    result.push(item);
  }

  return result;
}

function confidenceText(value?: string | null, language: ForgeLang = "fr"): string {
  const normalized = String(value || "").toLowerCase();

  if (language === "en") {
    if (normalized.includes("high") || normalized.includes("élev") || normalized.includes("elev")) return "High";
    if (normalized.includes("medium") || normalized.includes("moy")) return "Medium";
    if (normalized.includes("low") || normalized.includes("faib")) return "Low";
    return cleanText(value || "—", language);
  }

  if (normalized.includes("high") || normalized.includes("élev") || normalized.includes("elev")) return "Élevée";
  if (normalized.includes("medium") || normalized.includes("moy")) return "Moyenne";
  if (normalized.includes("low") || normalized.includes("faib")) return "Faible";

  return cleanText(value || "—", language);
}

function sourceToCompetitor(source: SourceItem): VerifiedCompetitor {
  return {
    name: source.vendor_name || source.title,
    title: source.title,
    region: source.region_match,
    region_match: source.region_match,
    source_type: source.source_type,
    source_role: source.source_role,
    comparison_scope: source.comparison_scope,
    technology_supplier: source.technology_supplier,
    canonical_source_id: source.canonical_source_id,
    evidence: source.why_relevant || source.snippet,
    source_url: source.url,
    url: source.url,
    pricing: source.pricing_found ? "Pricing signal detected" : undefined,
    why_relevant: source.why_relevant,
    vendor_key: source.vendor_key,
    canonical_vendor_domain: source.canonical_vendor_domain,
    sector_mismatch: source.sector_mismatch,
    mismatch_terms: source.mismatch_terms,
  };
}

function MiniMetricLocal({
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

function AnalysisBlockLocal({
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

function ListBlockLocal({
  title,
  items,
  language,
}: {
  title: string;
  items?: string[];
  language: ForgeLang;
}) {
  const cleanedItems = getPublicTextItems(items || [], language);

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

export default function SourcesAndCompetitorsSection({
  analysisData,
  project,
  language,
}: {
  analysisData: AnalysisData;
  project: Project;
  language?: ForgeLang;
}) {
  const { lang } = useForgeLanguage();
  const reportLanguage = resolveLanguage(language, lang, project, analysisData);
  const t = reportCopy[reportLanguage];

  const sourcesData = analysisData.forgecrawler;
  const competitiveAnalysis = analysisData.competitive_analysis;

  const sourcesRecord = (sourcesData || {}) as Record<string, unknown>;
  const competitiveRecord = (competitiveAnalysis || {}) as Record<string, unknown>;

  const context = getSourceDisplayContext(project, analysisData, reportLanguage);

  if (!sourcesData && !competitiveAnalysis) {
    return <EmptyState text={t.noSources} />;
  }

  const canonicalLedger = (
    competitiveRecord.canonical_source_ledger ||
    sourcesRecord.canonical_source_ledger ||
    {}
  ) as Record<string, unknown>;
  const canonicalLedgerRoles = (canonicalLedger.roles || {}) as Record<string, unknown>;
  const canonicalLedgerSources = getPublicDisplaySources(
    asArray<SourceItem>(canonicalLedger.sources)
  );

  const fallbackSourceCandidates = getPublicDisplaySources([
    ...asArray<SourceItem>(sourcesRecord.sources),
    ...asArray<SourceItem>(sourcesRecord.public_sources),
    ...asArray<SourceItem>(sourcesRecord.technology_provider_sources),
    ...asArray<SourceItem>(sourcesRecord.adjacent_solution_sources),
    ...asArray<SourceItem>(sourcesRecord.local_competitor_sources),
    ...asArray<SourceItem>(sourcesRecord.regional_competitor_sources),
    ...asArray<SourceItem>(sourcesRecord.international_benchmark_sources),
    ...asArray<SourceItem>(sourcesRecord.market_context_sources),
    ...asArray<SourceItem>(sourcesRecord.market_sources),

    ...asArray<SourceItem>(competitiveRecord.sources),
    ...asArray<SourceItem>(competitiveRecord.public_sources),
    ...asArray<SourceItem>(competitiveRecord.technology_provider_sources),
    ...asArray<SourceItem>(competitiveRecord.adjacent_solution_sources),
    ...asArray<SourceItem>(competitiveRecord.local_competitor_sources),
    ...asArray<SourceItem>(competitiveRecord.regional_competitor_sources),
    ...asArray<SourceItem>(competitiveRecord.international_benchmark_sources),
    ...asArray<SourceItem>(competitiveRecord.market_context_sources),
    ...asArray<SourceItem>(competitiveRecord.market_sources),
  ]);

  const hasCanonicalLedger = canonicalLedgerSources.length > 0;
  const allSources = uniqueSources(
    hasCanonicalLedger ? canonicalLedgerSources : fallbackSourceCandidates
  );

  const numericSourceCounts = [
    competitiveRecord.canonical_sources_count,
    sourcesRecord.canonical_sources_count,
    canonicalLedger.sources_count,
  ]
    .map((value) => Number(value))
    .filter((value) => Number.isFinite(value) && value >= 0);
  const retainedCount =
    numericSourceCounts.length > 0 ? numericSourceCounts[0] : allSources.length;

  const localSourceItems = uniqueSources(
    getPublicDisplaySources(
      hasCanonicalLedger
        ? asArray<SourceItem>(canonicalLedgerRoles.direct_competitor)
        : [
            ...asArray<SourceItem>(sourcesRecord.local_competitor_sources),
            ...asArray<SourceItem>(competitiveRecord.local_competitor_sources),
          ]
    ).filter((source) => String(source.region_match || "").toLowerCase() === "local")
  );

  const regionalSourceItems = uniqueSources(
    getPublicDisplaySources(
      hasCanonicalLedger
        ? asArray<SourceItem>(canonicalLedgerRoles.regional_benchmark)
        : [
            ...asArray<SourceItem>(sourcesRecord.regional_competitor_sources),
            ...asArray<SourceItem>(competitiveRecord.regional_competitor_sources),
          ]
    )
  );

  const internationalSourceItems = uniqueSources(
    getPublicDisplaySources(
      hasCanonicalLedger
        ? asArray<SourceItem>(canonicalLedgerRoles.international_benchmark)
        : [
            ...asArray<SourceItem>(sourcesRecord.international_benchmark_sources),
            ...asArray<SourceItem>(competitiveRecord.international_benchmark_sources),
          ]
    ).filter(
      (source) => String(source.source_role || "").toLowerCase() !== "technology_provider"
    )
  );

  const technologySourceItems = uniqueSources(
    getPublicDisplaySources(
      hasCanonicalLedger
        ? asArray<SourceItem>(canonicalLedgerRoles.technology_provider)
        : [
            ...asArray<SourceItem>(sourcesRecord.technology_provider_sources),
            ...asArray<SourceItem>(competitiveRecord.technology_provider_sources),
          ]
    )
  );

  const marketSources = uniqueSources(
    getPublicDisplaySources(
      hasCanonicalLedger
        ? [
            ...asArray<SourceItem>(canonicalLedgerRoles.market_evidence),
            ...asArray<SourceItem>(canonicalLedgerRoles.official_evidence),
            ...asArray<SourceItem>(canonicalLedgerRoles.local_ecosystem),
            ...asArray<SourceItem>(canonicalLedgerRoles.directory),
          ]
        : [
            ...asArray<SourceItem>(sourcesRecord.market_context_sources),
            ...asArray<SourceItem>(sourcesRecord.market_sources),
            ...asArray<SourceItem>(competitiveRecord.market_context_sources),
            ...asArray<SourceItem>(competitiveRecord.market_sources),
          ]
    )
  );

  const directFromCompetitive = uniqueCompetitors([
    ...asArray<VerifiedCompetitor>(competitiveRecord.local_direct_competitors),
    ...asArray<VerifiedCompetitor>(competitiveRecord.local_competitors),
    ...asArray<VerifiedCompetitor>(competitiveRecord.verified_competitors),
  ]);

  const directCompetitors =
    directFromCompetitive.length > 0
      ? directFromCompetitive
      : localSourceItems.map(sourceToCompetitor);

  const adjacent = uniqueCompetitors([
    ...asArray<VerifiedCompetitor>(competitiveRecord.local_adjacent_solutions).filter(
      (item) => String(item.region_match || item.region || "").toLowerCase() === "local"
    ),
    ...asArray<SourceItem>(canonicalLedgerRoles.adjacent_solution)
      .filter((source) => String(source.region_match || "").toLowerCase() === "local")
      .map(sourceToCompetitor),
  ]);

  const regionalFromCompetitive = uniqueCompetitors(
    asArray<VerifiedCompetitor>(competitiveRecord.regional_competitors)
  );

  const regional =
    regionalFromCompetitive.length > 0
      ? regionalFromCompetitive
      : regionalSourceItems.map(sourceToCompetitor);

  const internationalFromCompetitive = uniqueCompetitors(
    asArray<VerifiedCompetitor>(competitiveRecord.international_benchmarks)
  );

  const international =
    internationalFromCompetitive.length > 0
      ? internationalFromCompetitive
      : internationalSourceItems.map(sourceToCompetitor);

  const technologyFromCompetitive = uniqueCompetitors(
    asArray<VerifiedCompetitor>(competitiveRecord.technology_providers)
  );
  const technologyProviders =
    technologyFromCompetitive.length > 0
      ? technologyFromCompetitive
      : technologySourceItems.map(sourceToCompetitor);

  const displayedSources = marketSources.length
    ? marketSources.slice(0, 6)
    : allSources.slice(0, 6);

  const searchCoverage = String(
    sourcesRecord.search_coverage ||
      competitiveRecord.search_coverage ||
      analysisData.search_coverage ||
      sourcesRecord.discovery_confidence ||
      "low"
  );

  const evidenceConfidence = String(
    sourcesRecord.overall_evidence_confidence ||
      competitiveRecord.source_confidence ||
      analysisData.overall_evidence_confidence ||
      sourcesRecord.confidence_level ||
      competitiveRecord.confidence_level ||
      "low"
  );

  const relevanceConfidence = String(
    sourcesRecord.source_relevance_confidence ||
      competitiveRecord.source_relevance_confidence ||
      analysisData.source_relevance_confidence ||
      "low"
  );

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
        <MiniMetricLocal
          label={reportLanguage === "en" ? "Search coverage" : "Couverture de recherche"}
          value={confidenceText(searchCoverage, reportLanguage)}
        />
        <MiniMetricLocal
          label={reportLanguage === "en" ? "Evidence confidence" : "Confiance des preuves"}
          value={confidenceText(evidenceConfidence, reportLanguage)}
        />
        <MiniMetricLocal
          label={reportLanguage === "en" ? "Source relevance" : "Pertinence des sources"}
          value={confidenceText(relevanceConfidence, reportLanguage)}
        />
        <MiniMetricLocal
          label={t.retainedSources}
          value={String(retainedCount)}
        />
        <MiniMetricLocal
          label={context.directMetricLabel}
          value={String(directCompetitors.length)}
        />
        <MiniMetricLocal
          label={t.marketSources}
          value={String(marketSources.length)}
        />
      </div>

      {competitiveAnalysis?.market_gap && (
        <AnalysisBlockLocal
          title={t.marketGap}
          value={competitiveAnalysis.market_gap}
          language={reportLanguage}
        />
      )}

      <div className="grid gap-5 md:grid-cols-2">
        <CompetitorGroup
          title={context.directGroupTitle}
          competitors={directCompetitors}
          fallbackItems={getPublicTextItems(
            competitiveAnalysis?.direct_competitors || [],
            reportLanguage
          )}
          emptyText={context.directEmptyText}
          language={reportLanguage}
        />

        <CompetitorGroup
          title={context.adjacentGroupTitle}
          competitors={adjacent}
          fallbackItems={[]}
          emptyText={context.adjacentEmptyText}
          language={reportLanguage}
        />

        <CompetitorGroup
          title={t.regionalBenchmarks}
          competitors={regional}
          fallbackItems={[]}
          emptyText={
            reportLanguage === "en"
              ? "No regional benchmark."
              : "Aucun benchmark régional."
          }
          language={reportLanguage}
        />

        <CompetitorGroup
          title={t.internationalBenchmarks}
          competitors={international}
          fallbackItems={[]}
          emptyText={
            reportLanguage === "en"
              ? "No international benchmark."
              : "Aucun benchmark international."
          }
          language={reportLanguage}
        />

        <CompetitorGroup
          title={
            reportLanguage === "en"
              ? "Technology providers"
              : "Fournisseurs technologiques"
          }
          competitors={technologyProviders}
          fallbackItems={[]}
          emptyText={
            reportLanguage === "en"
              ? "No technology provider retained."
              : "Aucun fournisseur technologique retenu."
          }
          language={reportLanguage}
        />
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        <ListBlockLocal
          title={
            context.isGlobal ? t.comparableSolutions : t.indirectCompetitors
          }
          items={competitiveAnalysis?.indirect_competitors || []}
          language={reportLanguage}
        />

        <ListBlockLocal
          title={t.competitiveAdvantages}
          items={competitiveAnalysis?.competitive_advantages || []}
          language={reportLanguage}
        />
      </div>

      <SourceGroup
        title={t.marketSources}
        sources={displayedSources}
        emptyText={t.noSources}
        context={context}
        language={reportLanguage}
      />
    </div>
  );
}

function CompetitorGroup({
  title,
  competitors,
  fallbackItems,
  emptyText,
  language,
}: {
  title: string;
  competitors: VerifiedCompetitor[];
  fallbackItems: string[];
  emptyText: string;
  language: ForgeLang;
}) {
  return (
    <div className="rounded-3xl border border-slate-200/70 bg-white/75 p-5 shadow-sm">
      <h4 className="font-black text-slate-950">
        {cleanText(title, language)}
      </h4>

      <div className="mt-4 space-y-3">
        {competitors.length > 0 ? (
          competitors.map((competitor, index) => (
            <CompetitorCard
              key={`${competitor.name || competitor.title || "competitor"}-${index}`}
              competitor={competitor}
              language={language}
            />
          ))
        ) : fallbackItems.length > 0 ? (
          <ListBlockLocal title="Summary" items={fallbackItems} language={language} />
        ) : (
          <EmptyState text={cleanText(emptyText, language)} />
        )}
      </div>
    </div>
  );
}

function SourceGroup({
  title,
  sources,
  emptyText,
  context,
  language,
}: {
  title: string;
  sources: SourceItem[];
  emptyText: string;
  context: SourceDisplayContext;
  language: ForgeLang;
}) {
  return (
    <div className="rounded-3xl border border-slate-200/70 bg-white/75 p-5 shadow-sm">
      <h4 className="font-black text-slate-950">
        {cleanText(title, language)}
      </h4>

      <div className="mt-4 space-y-3">
        {sources.length > 0 ? (
          sources.map((source, index) => (
            <SourceCard
              key={`${source.url || source.title || "source"}-${index}`}
              source={source}
              index={index}
              context={context}
              language={language}
            />
          ))
        ) : (
          <EmptyState text={cleanText(emptyText, language)} />
        )}
      </div>
    </div>
  );
}