import type { ForgeLang } from "@/lib/language-context";

import type {
  AnalysisData,
  BusinessModelCanvas,
  FinancialEstimation,
  Project,
  StartupScore,
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
  startupScore?: StartupScore | null;
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

function verdictLabel(value?: string | null, language: ForgeLang = "fr"): string {
  const normalized = String(value || "").toLowerCase();

  if (language === "en") {
    if (normalized.includes("pivot")) return "Pivot";
    if (normalized.includes("poursuivre") || normalized.includes("continue")) {
      return "Continue";
    }
    if (normalized.includes("abandon") || normalized.includes("stop")) return "Stop";
    return value || "—";
  }

  if (normalized.includes("pivot")) return "Pivoter";
  if (normalized.includes("poursuivre") || normalized.includes("continue")) {
    return "Poursuivre";
  }
  if (normalized.includes("abandon") || normalized.includes("stop")) {
    return "Abandonner";
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

  const lang = resolveLanguage({ project, analysisData, language });
  const t = getCopy(lang);

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
            analysisData.detected_sector || project.industry || "—",
            lang
          )}
          tone="sky"
        />
        <MetricCard
          label={t.region}
          value={cleanText(
            analysisData.target_region || project.market_region || "—",
            lang
          )}
          tone="emerald"
        />
        <MetricCard
          label={t.startupScore}
          value={formatScore(getOfficialStartupScore(analysisData, project.startup_score))}
          tone="amber"
        />
      </div>

      <div className="mt-5">
        <AnalysisBlock
          title={t.summary}
          value={analysisData.summary}
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
          value={analysisData.difficulty}
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
          value={analysisData.target_users || analysisData.target_market}
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
              ? "Position the product as a focused SaaS for small training providers instead of a broad generic platform."
              : "Positionner le produit comme un SaaS ciblé pour les petits organismes de formation au lieu d’une plateforme générique.",
            lang === "en"
              ? "Use a pilot program to prove weekly usage, time saved and willingness to pay."
              : "Utiliser un pilote pour prouver l’usage hebdomadaire, le temps gagné et la volonté de payer.",
          ];

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
          value={
            marketStudy?.data_confidence ||
            analysisData.startup_score?.confidence_level ||
            (lang === "en" ? "Low" : "Faible")
          }
          language={lang}
        />
      </div>

      <div className="mt-5 grid gap-5 md:grid-cols-2">
        <ListBlock
          title={t.marketTrends}
          items={marketStudy?.market_trends || []}
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
  startupScore,
  language,
}: CoreSectionProps) {
  const currentScore = startupScore || analysisData?.startup_score;
  if (!currentScore && !project?.startup_score) return null;

  const lang = resolveLanguage({ project, analysisData, language });
  const t = getCopy(lang);

  const officialScore = getOfficialStartupScore(
    analysisData || null,
    project?.startup_score ?? null
  );

  const breakdown =
    currentScore?.criteria_scores ||
    currentScore?.score_breakdown ||
    currentScore?.breakdown ||
    {};

  return (
    <SectionShell id="startup-score" title={t.sectionStartupScore}>
      <div className="grid gap-5 md:grid-cols-4">
        <MetricCard label={t.globalScore} value={formatScore(officialScore)} tone="amber" />
        <MetricCard label={t.risk} value={riskLabel(currentScore?.risk_level, lang)} tone="rose" />
        <MetricCard label={t.sourceConfidence} value={cleanText(currentScore?.confidence_level || "—", lang)} tone="sky" />
        <MetricCard label={t.verdict} value={verdictLabel(currentScore?.verdict, lang)} tone="emerald" />
      </div>

      {(currentScore?.summary || currentScore?.score_explanation) && (
        <div className="mt-5">
          <AnalysisBlock
            title={t.summary}
            value={currentScore.summary || currentScore.score_explanation}
            language={lang}
          />
        </div>
      )}

      {Object.keys(breakdown).length > 0 && (
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          {Object.entries(breakdown).map(([key, value]) => (
            <MetricCard
              key={key}
              label={cleanText(key.replaceAll("_", " "), lang)}
              value={formatScore(typeof value === "number" ? value : null)}
            />
          ))}
        </div>
      )}

      <div className="mt-5 grid gap-5 md:grid-cols-2">
        <ListBlock
          title={t.strengths}
          items={currentScore?.strengths || []}
          language={lang}
        />
        <ListBlock
          title={t.weaknesses}
          items={currentScore?.weaknesses || []}
          language={lang}
        />
        <ListBlock
          title={t.nextActions}
          items={currentScore?.next_actions || []}
          language={lang}
        />
      </div>
    </SectionShell>
  );
}

export function VerdictSection({
  analysisData,
  project,
  language,
}: CoreSectionProps) {
  if (!analysisData?.debate_room?.judge && !analysisData?.startup_score) {
    return null;
  }

  const lang = resolveLanguage({ project, analysisData, language });
  const t = getCopy(lang);
  const judge = analysisData?.debate_room?.judge;
  const startupScore = analysisData?.startup_score;

  const officialScore = getOfficialStartupScore(
    analysisData || null,
    project?.startup_score ?? null
  );

  const finalRecommendation =
    judge?.final_recommendation ||
    judge?.debate_synthesis ||
    startupScore?.summary ||
    (lang === "en"
      ? "Continue with a narrow MVP, validate real user adoption and prove willingness to pay before scaling."
      : "Poursuivre avec un MVP réduit, valider l’adoption réelle et prouver la volonté de payer avant le passage à l’échelle.");

  const improvedIdea =
    judge?.improved_idea ||
    (lang === "en"
      ? "Focus the product on the first operational workflow, run a pilot with real target users, then expand features only after repeated usage is proven."
      : "Centrer le produit sur le premier workflow opérationnel, lancer un pilote avec de vrais utilisateurs cibles, puis élargir les fonctionnalités seulement après preuve d’usage répété.");

  const validatedOpportunities =
    toListItems(judge?.validated_opportunities || [], lang).length > 0
      ? judge?.validated_opportunities || []
      : toListItems(analysisData.swot?.opportunities || [], lang).length > 0
        ? analysisData.swot?.opportunities || []
        : startupScore?.strengths || [];

  const criticalRisks =
    toListItems(judge?.critical_risks || [], lang).length > 0
      ? judge?.critical_risks || []
      : analysisData.swot?.threats || startupScore?.weaknesses || [];

  return (
    <SectionShell id="verdict" title={t.sectionVerdict}>
      <div className="grid gap-5 md:grid-cols-3">
        <MetricCard
          label={t.verdict}
          value={verdictLabel(judge?.verdict || startupScore?.verdict, lang)}
          tone="emerald"
        />
        <MetricCard
          label={t.argumentScore}
          value={formatScore(
            judge?.argument_strength_score ??
              judge?.confidence_score ??
              officialScore
          )}
          tone="sky"
        />
        <MetricCard
          label={t.risk}
          value={riskLabel(judge?.risk_level || startupScore?.risk_level, lang)}
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
          value={improvedIdea}
          language={lang}
        />
      </div>

      <div className="mt-5 grid gap-5 md:grid-cols-2">
        <ListBlock
          title={t.criticalRisks}
          items={criticalRisks}
          language={lang}
        />
        <ListBlock
          title={t.validatedOpportunities}
          items={validatedOpportunities}
          language={lang}
        />
        <ListBlock
          title={t.goNoGo}
          items={judge?.go_no_go_conditions || []}
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
  if (!analysisData) return null;

  const lang = resolveLanguage({ project, analysisData, language });
  const t = getCopy(lang);
  const judge = analysisData.debate_room?.judge;

  const actions =
    judge?.next_actions ||
    judge?.action_plan ||
    analysisData.recommendations ||
    analysisData.startup_score?.next_actions ||
    [];

  return (
    <SectionShell id="action-plan" title={t.sectionActionPlan}>
      <ListBlock
        title={t.nextActions}
        items={actions}
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