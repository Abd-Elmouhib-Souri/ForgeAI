import type { ForgeLang } from "@/lib/language-context";

import type {
  AnalysisData,
  BusinessModelCanvas,
  FinancialEstimation,
  Project,
  SWOT,
  TextList,
} from "../_types/project-detail.types";

import {
  getConcreteSolution,
  getOfficialStartupScore,
  getPublicLocalMarketAssessment,
  getPublicTextItems,
  getReportLanguage,
} from "../_lib/analysis-helpers";

import { reportCopy } from "../_lib/report-copy";
import { cleanText } from "../_lib/text-cleaning";

type CoreSectionProps = {
  analysisData?: AnalysisData | null;
  project?: Project | null;
  copy?: Record<string, string>;
  language?: ForgeLang;
  swot?: SWOT | null;
  bmc?: BusinessModelCanvas | null;
  financialEstimation?: FinancialEstimation | null;
  limitations?: TextList;
  [key: string]: unknown;
};

type AnalysisValue = string | string[] | number | null | undefined;

function resolveLanguage({
  project,
  analysisData,
  language,
}: {
  project?: Project | null;
  analysisData?: AnalysisData | null;
  language?: ForgeLang;
}): ForgeLang {
  if (language === "en" || language === "fr") return language;
  return getReportLanguage(project || null, analysisData || null, "fr");
}

function getCopy(language: ForgeLang) {
  return reportCopy[language];
}

function toDisplayText(
  value: AnalysisValue,
  language: ForgeLang,
  fallback = "—"
): string {
  if (Array.isArray(value)) {
    const cleanedItems = value
      .map((item) => cleanText(String(item || "").trim(), language))
      .filter(Boolean);

    return cleanedItems.length > 0 ? cleanedItems.join("\n") : fallback;
  }

  if (typeof value === "number" && Number.isFinite(value)) {
    return String(value);
  }

  const cleaned = cleanText(String(value || "").trim(), language);
  return cleaned || fallback;
}

function toListItems(value: TextList, language: ForgeLang): string[] {
  if (Array.isArray(value)) {
    return getPublicTextItems(
      value.map((item) => String(item || "")),
      language
    );
  }

  if (typeof value === "string") {
    return getPublicTextItems([value], language);
  }

  return [];
}

function formatScore(value?: number | null): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "—";
  }

  return `${value.toFixed(1).replace(".0", "")}/10`;
}

function riskLabel(value?: string | null, language: ForgeLang = "fr"): string {
  const normalized = String(value || "").toLowerCase();

  if (language === "en") {
    if (normalized.includes("high") || normalized.includes("élev")) return "High";
    if (normalized.includes("medium") || normalized.includes("moy")) return "Medium";
    if (normalized.includes("low") || normalized.includes("faib")) return "Low";
    return value || "—";
  }

  if (normalized.includes("high") || normalized.includes("élev")) return "Élevé";
  if (normalized.includes("medium") || normalized.includes("moy")) return "Moyen";
  if (normalized.includes("low") || normalized.includes("faib")) return "Faible";

  return value || "—";
}

function confidenceLabel(
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

function criterionLabel(key: string, language: ForgeLang): string {
  const normalized = String(key || "").trim().toLowerCase();
  const labels: Record<string, Record<ForgeLang, string>> = {
    problem_solution_fit: {
      fr: "Adéquation problème-solution",
      en: "Problem-solution fit",
    },
    market_potential: {
      fr: "Potentiel de marché",
      en: "Market potential",
    },
    execution_feasibility: {
      fr: "Faisabilité d’exécution",
      en: "Execution feasibility",
    },
    business_model_strength: {
      fr: "Solidité du modèle économique",
      en: "Business model strength",
    },
    competitive_advantage: {
      fr: "Avantage concurrentiel",
      en: "Competitive advantage",
    },
    innovation: {
      fr: "Innovation",
      en: "Innovation",
    },
    scalability: {
      fr: "Capacité de passage à l’échelle",
      en: "Scalability",
    },
    financial_viability: {
      fr: "Viabilité financière",
      en: "Financial viability",
    },
    risk_management: {
      fr: "Gestion des risques",
      en: "Risk management",
    },
  };

  return (
    labels[normalized]?.[language] ||
    cleanText(normalized.replaceAll("_", " "), language)
  );
}

function verdictLabel(value?: string | null, language: ForgeLang = "fr"): string {
  const normalized = String(value || "")
    .trim()
    .toLowerCase()
    .replaceAll("-", "_")
    .replaceAll(" ", "_");

  const labels = language === "en"
    ? {
        go: "Go",
        conditional_go: "Continue with conditions",
        pivot: "Pivot",
        no_go: "No-go",
        insufficient_evidence: "Insufficient evidence",
      }
    : {
        go: "Poursuivre",
        conditional_go: "Poursuivre sous conditions",
        pivot: "Pivoter",
        no_go: "Ne pas poursuivre",
        insufficient_evidence: "Preuves insuffisantes",
      };

  if (["go", "poursuivre", "continue"].includes(normalized)) return labels.go;
  if (["conditional_go", "continue_with_conditions", "poursuivre_sous_conditions"].includes(normalized)) {
    return labels.conditional_go;
  }
  if (["pivot", "pivoter"].includes(normalized)) return labels.pivot;
  if (["no_go", "stop", "abandon", "abandonner"].includes(normalized)) return labels.no_go;
  if (["insufficient_evidence", "preuves_insuffisantes"].includes(normalized)) {
    return labels.insufficient_evidence;
  }

  return value || "—";
}

export function AnalysisBlock({
  title,
  value,
  language = "fr",
}: {
  title: string;
  value?: AnalysisValue;
  language?: ForgeLang;
}) {
  const normalizedValue = toDisplayText(value, language);

  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/70">
      <p className="text-xs font-black uppercase tracking-[0.2em] text-slate-400">
        {title}
      </p>

      <p className="mt-3 whitespace-pre-wrap text-sm font-semibold leading-7 text-slate-700">
        {normalizedValue}
      </p>
    </div>
  );
}

export function ListBlock({
  title,
  items,
  language = "fr",
  emptyText,
}: {
  title: string;
  items?: TextList;
  language?: ForgeLang;
  emptyText?: string;
}) {
  const normalizedItems = toListItems(items, language);

  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/70">
      <p className="text-xs font-black uppercase tracking-[0.2em] text-slate-400">
        {title}
      </p>

      {normalizedItems.length > 0 ? (
        <ul className="mt-3 space-y-2">
          {normalizedItems.map((item, index) => (
            <li
              key={`${title}-${index}`}
              className="rounded-2xl bg-slate-50 px-4 py-3 text-sm font-semibold leading-6 text-slate-700"
            >
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm font-semibold text-slate-400">
          {emptyText || "—"}
        </p>
      )}
    </div>
  );
}

function MetricCard({
  label,
  value,
  tone = "slate",
}: {
  label: string;
  value: string;
  tone?: "slate" | "emerald" | "sky" | "amber" | "rose";
}) {
  const toneClass = {
    slate: "border-slate-200 bg-white text-slate-900",
    emerald: "border-emerald-200 bg-emerald-50 text-emerald-900",
    sky: "border-sky-200 bg-sky-50 text-sky-900",
    amber: "border-amber-200 bg-amber-50 text-amber-900",
    rose: "border-rose-200 bg-rose-50 text-rose-900",
  }[tone];

  return (
    <div className={`rounded-3xl border p-5 shadow-sm ${toneClass}`}>
      <p className="text-xs font-black uppercase tracking-[0.2em] opacity-60">
        {label}
      </p>
      <p className="mt-3 text-2xl font-black">{value}</p>
    </div>
  );
}

function SectionShell({
  id,
  title,
  subtitle,
  children,
}: {
  id?: string;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-28 rounded-[2rem] border border-slate-200 bg-white/80 p-6 shadow-xl shadow-slate-200/70 backdrop-blur md:p-8">
      <div className="mb-6">
        <p className="text-xs font-black uppercase tracking-[0.24em] text-sky-500">
          ForgeAI Report
        </p>
        <h2 className="mt-2 text-2xl font-black tracking-tight text-slate-950 md:text-3xl">
          {title}
        </h2>
        {subtitle && (
          <p className="mt-3 max-w-3xl text-sm font-semibold leading-7 text-slate-500">
            {subtitle}
          </p>
        )}
      </div>

      {children}
    </section>
  );
}

export function ExecutiveSummarySection({
  analysisData,
  project,
  language,
}: CoreSectionProps) {
  if (!analysisData || !project) return null;

  const finalReport = analysisData.final_report;
  if (!finalReport) return null;

  const lang = resolveLanguage({
    project,
    analysisData,
    language,
  });

  const t = getCopy(lang);

  const context = finalReport.context;
  const summary = finalReport.executive_summary;
  const decision = finalReport.decision;

  return (
    <SectionShell
      id="executive-summary"
      title={t.sectionExecutive}
      subtitle={t.strategicReading}
    >
      <div className="grid gap-5 md:grid-cols-3">
        <MetricCard
          label={t.sector}
          value={cleanText(
            context?.sector ||
              project.industry ||
              "?",
            lang
          )}
          tone="sky"
        />

        <MetricCard
          label={t.region}
          value={cleanText(
            context?.target_region ||
              project.market_region ||
              "?",
            lang
          )}
          tone="emerald"
        />

        <MetricCard
          label={t.startupScore}
          value={formatScore(
            getOfficialStartupScore(
              analysisData,
              project?.startup_score ?? null
            )
          )}
          tone="amber"
        />
      </div>

      <div className="mt-5">
        <AnalysisBlock
          title={t.summary}
          value={
            decision?.debate_synthesis ||
            summary?.final_recommendation
          }
          language={lang}
        />
      </div>
    </SectionShell>
  );
}

export function ProblemSection({
  analysisData,
  project,
  language,
}: CoreSectionProps) {
  if (!analysisData || !project) return null;

  const lang = resolveLanguage({ project, analysisData, language });
  const t = getCopy(lang);

  const problemRiskItems =
    toListItems(analysisData.risks, lang).length > 0
      ? analysisData.risks
      : [
          lang === "en"
            ? "The problem still needs direct validation with real target users before investment."
            : "Le problème doit encore être validé directement avec de vrais utilisateurs cibles avant investissement.",
          lang === "en"
            ? "The first customer segment may be too broad and should be narrowed before scaling."
            : "Le premier segment client peut être trop large et doit être resserré avant le passage à l’échelle.",
        ];

  return (
    <SectionShell id="problem" title={t.sectionProblem}>
      <div className="grid gap-5 md:grid-cols-2">
        <AnalysisBlock
          title={t.problem}
          value={analysisData.problem || analysisData.problem_solved}
          language={lang}
        />
        <ListBlock
          title={t.problemRisks}
          items={problemRiskItems}
          language={lang}
        />
      </div>
    </SectionShell>
  );
}

export function SolutionSection({
  analysisData,
  project,
  language,
}: CoreSectionProps) {
  if (!analysisData || !project) return null;

  const lang = resolveLanguage({ project, analysisData, language });
  const t = getCopy(lang);

  return (
    <SectionShell id="solution" title={t.sectionSolution}>
      <div className="grid gap-5 md:grid-cols-2">
        <AnalysisBlock
          title={t.solution}
          value={getConcreteSolution(analysisData, project)}
          language={lang}
        />
        <AnalysisBlock
          title={t.difficulty}
          value={riskLabel(analysisData.difficulty, lang)}
          language={lang}
        />
      </div>

      <div className="mt-5 grid gap-5 md:grid-cols-2">
        <ListBlock
          title={t.technologies}
          items={analysisData.recommended_technologies || []}
          language={lang}
        />
        <ListBlock
          title={t.improvements}
          items={analysisData.improvement_suggestions || []}
          language={lang}
        />
      </div>
    </SectionShell>
  );
}

export function TargetMarketSection({
  analysisData,
  project,
  language,
}: CoreSectionProps) {
  if (!analysisData || !project) return null;

  const lang = resolveLanguage({ project, analysisData, language });
  const t = getCopy(lang);
  const marketStudy = analysisData.market_study;

  return (
    <SectionShell id="target-market" title={t.sectionTargetMarket}>
      <div className="grid gap-5 md:grid-cols-2">
        <AnalysisBlock
          title={t.targetUsers}
          value={
            analysisData.target_users ||
            analysisData.target_market ||
            marketStudy?.target_customers ||
            marketStudy?.customer_segments ||
            analysisData.persona_builder?.target_segments
          }
          language={lang}
        />
        <AnalysisBlock
          title={t.marketTarget}
          value={marketStudy?.target_market || analysisData.target_market}
          language={lang}
        />
        <AnalysisBlock
          title={t.targetRegion}
          value={analysisData.target_region || project.market_region}
          language={lang}
        />
        <ListBlock
          title={t.customerSegments}
          items={marketStudy?.customer_segments || []}
          language={lang}
        />
      </div>
    </SectionShell>
  );
}

export function MarketOpportunitySection({
  analysisData,
  project,
  language,
}: CoreSectionProps) {
  if (!analysisData || !project) return null;

  const lang = resolveLanguage({ project, analysisData, language });
  const t = getCopy(lang);
  const marketStudy = analysisData.market_study;

  const opportunityItems =
    toListItems(marketStudy?.opportunities, lang).length > 0
      ? marketStudy?.opportunities
      : toListItems(analysisData.swot?.opportunities, lang).length > 0
        ? analysisData.swot?.opportunities
        : [
            lang === "en"
              ? "Position the product around one priority workflow and expand only after measurable field validation."
              : "Positionner le produit autour d’un workflow prioritaire et élargir uniquement après une validation terrain mesurable.",
            lang === "en"
              ? "Use a bounded pilot to prove repeat use, time saved, reliability and willingness to pay."
              : "Utiliser un pilote limité pour prouver l’usage répété, le temps gagné, la fiabilité et la volonté de payer.",
          ];

  const neutralTrendMarkers =
    lang === "en"
      ? [
          "no market trend is sufficiently supported",
          "no confirmed market trend",
        ]
      : [
          "aucune tendance de marché n’est suffisamment soutenue",
          "aucune tendance de marché n'est suffisamment soutenue",
          "aucune tendance confirmée",
        ];

  const rawTrendItems = toListItems(marketStudy?.market_trends, lang);
  const meaningfulTrendItems = rawTrendItems.filter((item) => {
    const normalized = item.toLowerCase();
    return !neutralTrendMarkers.some((marker) => normalized.includes(marker));
  });
  const fallbackTrendSignals = toListItems(
    marketStudy?.market_trend_signals,
    lang
  );
  const marketTrendItems =
    meaningfulTrendItems.length > 0
      ? meaningfulTrendItems
      : fallbackTrendSignals.length > 0
        ? fallbackTrendSignals
        : rawTrendItems;

  const marketRiskItems =
    toListItems(marketStudy?.risks, lang).length > 0
      ? marketStudy?.risks
      : toListItems(analysisData.swot?.threats, lang).length > 0
        ? analysisData.swot?.threats
        : [
            lang === "en"
              ? "Users may keep using manual tools if the first benefit is not immediate."
              : "Les utilisateurs peuvent continuer avec des outils manuels si le premier bénéfice n’est pas immédiat.",
            lang === "en"
              ? "Willingness to pay must be proven through interviews and a paid or semi-paid pilot."
              : "La volonté de payer doit être prouvée par des entretiens et un pilote payant ou semi-payant.",
          ];

  return (
    <SectionShell id="market-opportunity" title={t.sectionMarketOpportunity}>
      <div className="grid gap-5 md:grid-cols-2">
        <AnalysisBlock
          title={t.marketSize}
          value={marketStudy?.market_size}
          language={lang}
        />
        <AnalysisBlock
          title={t.globalPotential}
          value={analysisData.global_market_assessment}
          language={lang}
        />
        <AnalysisBlock
          title={t.localFeasibility}
          value={getPublicLocalMarketAssessment(analysisData, project, lang)}
          language={lang}
        />
        <AnalysisBlock
          title={t.dataConfidence}
          value={confidenceLabel(
            marketStudy?.data_confidence ||
              analysisData.startup_score?.confidence_level ||
              "low",
            lang
          )}
          language={lang}
        />
      </div>

      <div className="mt-5 grid gap-5 md:grid-cols-2">
        <ListBlock
          title={t.marketTrends}
          items={marketTrendItems}
          language={lang}
        />
        <ListBlock
          title={t.opportunities}
          items={opportunityItems}
          language={lang}
        />
        <ListBlock
          title={t.marketRisks}
          items={marketRiskItems}
          language={lang}
        />
      </div>
    </SectionShell>
  );
}

export function SWOTSection({
  analysisData,
  project,
  swot,
  language,
}: CoreSectionProps) {
  const currentSwot = swot || analysisData?.swot;
  if (!currentSwot) return null;

  const lang = resolveLanguage({ project, analysisData, language });
  const t = getCopy(lang);

  return (
    <SectionShell id="swot" title={t.sectionSwot}>
      <div className="grid gap-5 md:grid-cols-2">
        <ListBlock title={t.strengths} items={currentSwot.strengths || []} language={lang} />
        <ListBlock title={t.weaknesses} items={currentSwot.weaknesses || []} language={lang} />
        <ListBlock title={t.opportunities} items={currentSwot.opportunities || []} language={lang} />
        <ListBlock title={t.threats} items={currentSwot.threats || []} language={lang} />
      </div>
    </SectionShell>
  );
}

export function BMCSection({
  analysisData,
  project,
  bmc,
  language,
}: CoreSectionProps) {
  const currentBmc = bmc || analysisData?.business_model_canvas;
  if (!currentBmc) return null;

  const lang = resolveLanguage({ project, analysisData, language });
  const t = getCopy(lang);

  return (
    <SectionShell id="business-model-canvas" title={t.sectionBmc}>
      <div className="grid gap-5 md:grid-cols-3">
        <AnalysisBlock title={t.valueProposition} value={currentBmc.value_proposition} language={lang} />
        <AnalysisBlock title={t.customerSegments} value={currentBmc.customer_segments} language={lang} />
        <AnalysisBlock title={t.channels} value={currentBmc.channels} language={lang} />
        <AnalysisBlock title={t.customerRelationships} value={currentBmc.customer_relationships} language={lang} />
        <AnalysisBlock title={t.revenueStreams} value={currentBmc.revenue_streams} language={lang} />
        <AnalysisBlock title={t.keyResources} value={currentBmc.key_resources} language={lang} />
        <AnalysisBlock title={t.keyActivities} value={currentBmc.key_activities} language={lang} />
        <AnalysisBlock title={t.keyPartners} value={currentBmc.key_partners} language={lang} />
        <AnalysisBlock title={t.costStructure} value={currentBmc.cost_structure} language={lang} />
      </div>
    </SectionShell>
  );
}

export const BusinessModelCanvasSection = BMCSection;

export function FinancialSection({
  analysisData,
  project,
  financialEstimation,
  language,
}: CoreSectionProps) {
  const currentFinancial =
    financialEstimation || analysisData?.financial_estimation;

  if (!currentFinancial) return null;

  const lang = resolveLanguage({ project, analysisData, language });
  const t = getCopy(lang);

  return (
    <SectionShell
      id="financial-estimation"
      title={t.sectionFinancial}
      subtitle={t.financialNoteText}
    >
      <div className="grid gap-5 md:grid-cols-2">
        <AnalysisBlock
          title={t.mvpBudget}
          value={currentFinancial.mvp_budget_estimate}
          language={lang}
        />
        <AnalysisBlock
          title={t.infrastructureCosts}
          value={currentFinancial.infrastructure_cost_estimate}
          language={lang}
        />
        <AnalysisBlock
          title={t.roi}
          value={currentFinancial.roi_outlook}
          language={lang}
        />
        <AnalysisBlock
          title={t.financialRisk}
          value={riskLabel(currentFinancial.financial_risk_level, lang)}
          language={lang}
        />
        <ListBlock
          title={t.possibleRevenue}
          items={currentFinancial.possible_revenue_streams || []}
          language={lang}
        />
      </div>
    </SectionShell>
  );
}

export const FinancialEstimationSection = FinancialSection;

export function StartupScoreSection({
  analysisData,
  project,
  language,
}: CoreSectionProps) {
  const currentScore =
    analysisData?.final_report?.startup_score;

  if (!currentScore) return null;

  const lang = resolveLanguage({
    project,
    analysisData,
    language,
  });

  const t = getCopy(lang);

  const breakdown = {
    innovation: currentScore.innovation,
    feasibility: currentScore.feasibility,
    profitability: currentScore.profitability,
    scalability: currentScore.scalability,
  };

  const availableBreakdown =
    Object.entries(
      breakdown
    ).filter(
      (
        entry
      ): entry is [string, number] =>
        typeof entry[1] === "number" &&
        Number.isFinite(entry[1])
    );

  return (
    <SectionShell
      id="startup-score"
      title={t.sectionStartupScore}
    >
      <div className="grid gap-5 md:grid-cols-2">
        <MetricCard
          label={t.startupScore}
          value={formatScore(
            getOfficialStartupScore(
              analysisData,
              project?.startup_score ?? null
            )
          )}
          tone="amber"
        />

        <AnalysisBlock
          title={t.summary}
          value={currentScore.score_explanation}
          language={lang}
        />
      </div>

      {availableBreakdown.length > 0 && (
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          {availableBreakdown.map(
            ([key, value]) => (
              <MetricCard
                key={key}
                label={criterionLabel(
                  key,
                  lang
                )}
                value={formatScore(value)}
              />
            )
          )}
        </div>
      )}
    </SectionShell>
  );
}

export function VerdictSection({
  analysisData,
  project,
  language,
}: CoreSectionProps) {
  const decision =
    analysisData?.final_report?.decision;

  if (!decision) return null;

  const lang = resolveLanguage({
    project,
    analysisData,
    language,
  });

  const t = getCopy(lang);

  const finalRecommendation =
    decision.final_recommendation ||
    decision.debate_synthesis;

  return (
    <SectionShell
      id="verdict"
      title={t.sectionVerdict}
    >
      <div className="grid gap-5 md:grid-cols-3">
        <MetricCard
          label={t.verdict}
          value={verdictLabel(
            decision.verdict_code ||
              decision.verdict,
            lang
          )}
          tone="emerald"
        />

        <MetricCard
          label={t.argumentScore}
          value={formatScore(
            decision.argument_strength_score ??
              decision.confidence_score ??
              null
          )}
          tone="sky"
        />

        <MetricCard
          label={t.risk}
          value={riskLabel(
            decision.risk_level,
            lang
          )}
          tone="rose"
        />
      </div>

      <div className="mt-5 grid gap-5 md:grid-cols-2">
        <AnalysisBlock
          title={t.finalRecommendation}
          value={finalRecommendation}
          language={lang}
        />

        <AnalysisBlock
          title={t.improvedIdea}
          value={decision.improved_idea}
          language={lang}
        />
      </div>

      <div className="mt-5 grid gap-5 md:grid-cols-2">
        <ListBlock
          title={t.criticalRisks}
          items={decision.critical_risks || []}
          language={lang}
        />

        <ListBlock
          title={t.validatedOpportunities}
          items={
            decision.validated_opportunities ||
            []
          }
          language={lang}
          emptyText={
            lang === "en"
              ? "No opportunity is considered validated without compatible evidence."
              : "Aucune opportunité n’est considérée comme validée sans preuve compatible."
          }
        />

        <ListBlock
          title={t.potentialOpportunities}
          items={
            decision.potential_opportunities ||
            []
          }
          language={lang}
        />

        <ListBlock
          title={
            lang === "en"
              ? "GO conditions"
              : "Conditions GO"
          }
          items={decision.go_conditions || []}
          language={lang}
        />

        <ListBlock
          title={
            lang === "en"
              ? "NO-GO conditions"
              : "Conditions NO-GO"
          }
          items={decision.no_go_conditions || []}
          language={lang}
        />

        <ListBlock
          title={t.goNoGo}
          items={
            decision.go_no_go_conditions ||
            []
          }
          language={lang}
        />
      </div>
    </SectionShell>
  );
}

export function ActionPlanSection({
  analysisData,
  project,
  language,
}: CoreSectionProps) {
  const decision =
    analysisData?.final_report?.decision;

  if (!decision) return null;

  const lang = resolveLanguage({
    project,
    analysisData,
    language,
  });

  const t = getCopy(lang);

  const items =
    decision.next_actions ||
    decision.action_plan ||
    [];

  return (
    <SectionShell
      id="action-plan"
      title={t.sectionActionPlan}
    >
      <ListBlock
        title={t.nextActions}
        items={items}
        language={lang}
        emptyText={t.defaultLimitations}
      />
    </SectionShell>
  );
}

export function LimitationsSection({
  analysisData,
  project,
  limitations,
  language,
}: CoreSectionProps) {
  const lang = resolveLanguage({ project, analysisData, language });
  const t = getCopy(lang);

  const items =
    limitations ||
    analysisData?.public_limitations ||
    analysisData?.fact_check_report?.limitations ||
    analysisData?.competitive_analysis?.limitations ||
    analysisData?.forgecrawler?.limitations ||
    analysisData?.data_limitations ||
    [];

  return (
    <SectionShell id="limitations" title={t.sectionLimitations}>
      <ListBlock
        title={t.limitationsIdentified}
        items={items}
        language={lang}
        emptyText={t.defaultLimitations}
      />
    </SectionShell>
  );
}
export const FinalVerdictSection = VerdictSection;
export const RecommendedActionPlanSection = ActionPlanSection;
export const AnalysisLimitationsSection = LimitationsSection;

export function CoreSections({
  analysisData,
  project,
  language,
}: CoreSectionProps) {
  if (!analysisData || !project) return null;

  const lang = resolveLanguage({ project, analysisData, language });

  return (
    <div className="space-y-8">
      <ExecutiveSummarySection analysisData={analysisData} project={project} language={lang} />
      <ProblemSection analysisData={analysisData} project={project} language={lang} />
      <SolutionSection analysisData={analysisData} project={project} language={lang} />
      <TargetMarketSection analysisData={analysisData} project={project} language={lang} />
      <MarketOpportunitySection analysisData={analysisData} project={project} language={lang} />
      <SWOTSection analysisData={analysisData} project={project} language={lang} />
      <BMCSection analysisData={analysisData} project={project} language={lang} />
      <FinancialSection analysisData={analysisData} project={project} language={lang} />
      <StartupScoreSection analysisData={analysisData} project={project} language={lang} />
      <VerdictSection analysisData={analysisData} project={project} language={lang} />
      <ActionPlanSection analysisData={analysisData} project={project} language={lang} />
      <LimitationsSection analysisData={analysisData} project={project} language={lang} />
    </div>
  );
}
