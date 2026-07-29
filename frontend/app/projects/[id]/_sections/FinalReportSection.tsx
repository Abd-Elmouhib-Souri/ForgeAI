"use client";

import { useForgeLanguage } from "@/lib/language-context";

import type { AnalysisData, Project } from "../_types/project-detail.types";

import { reportCopy } from "../_lib/report-copy";
import {
  getPersonaBuilderData,
  getReportLanguage,
} from "../_lib/analysis-helpers";

import ReportSection from "../_components/ReportSection";
import ReportNavigation from "../_components/ReportNavigation";
import { EmptyState } from "../_components/UIBlocks";

import ReportIntro from "./ReportIntro";
import AnalysisJourneySection from "./AnalysisJourneySection";
import PersonasSection from "./PersonasSection";
import SourcesAndCompetitorsSection from "./SourcesAndCompetitorsSection";
import DebateRoomSection from "./DebateRoomSection";
import FactCheckSection from "./FactCheckSection";

import {
  AnalysisLimitationsSection,
  BMCSection,
  ExecutiveSummarySection,
  FinancialEstimationSection,
  FinalVerdictSection,
  MarketOpportunitySection,
  ProblemSection,
  RecommendedActionPlanSection,
  SolutionSection,
  StartupScoreSection,
  SWOTSection,
  TargetMarketSection,
} from "./CoreSections";

export default function FinalReportSection({
  analysisData,
  project,
  copy,
}: {
  analysisData: AnalysisData | null;
  project: Project;
  copy?: Partial<Record<string, string>>;
}) {
  const { lang } = useForgeLanguage();

  if (!analysisData) {
    const t = reportCopy[lang];
    return <EmptyState text={copy?.noReport || t.noReport} />;
  }

  const reportLanguage = getReportLanguage(project, analysisData, lang);
  const t = reportCopy[reportLanguage];
  const personasData = getPersonaBuilderData(analysisData);

  return (
    <section className="space-y-6">
      <ReportIntro analysisData={analysisData} project={project} />

      <ReportNavigation />

      <AnalysisJourneySection analysisData={analysisData} project={project} />

      <ReportSection id="executive-summary" number={1} title={t.sectionExecutive}>
        <ExecutiveSummarySection
          analysisData={analysisData}
          project={project}
          language={reportLanguage}
        />
      </ReportSection>

      <ReportSection id="problem" number={2} title={t.sectionProblem}>
        <ProblemSection
          analysisData={analysisData}
          project={project}
          language={reportLanguage}
        />
      </ReportSection>

      <ReportSection id="solution" number={3} title={t.sectionSolution}>
        <SolutionSection
          analysisData={analysisData}
          project={project}
          language={reportLanguage}
        />
      </ReportSection>

      <ReportSection id="target-market" number={4} title={t.sectionTargetMarket}>
        <TargetMarketSection
          analysisData={analysisData}
          project={project}
          language={reportLanguage}
        />
      </ReportSection>

      <ReportSection id="personas" number={5} title={t.sectionPersonas}>
        <PersonasSection
          personasData={personasData}
          language={reportLanguage}
        />
      </ReportSection>

      <ReportSection
        id="market-opportunity"
        number={6}
        title={t.sectionMarketOpportunity}
      >
        <MarketOpportunitySection
          analysisData={analysisData}
          project={project}
          language={reportLanguage}
        />
      </ReportSection>

      <ReportSection id="swot" number={7} title={t.sectionSwot}>
        <SWOTSection
          analysisData={analysisData}
          project={project}
          swot={analysisData.swot}
          language={reportLanguage}
        />
      </ReportSection>

      <ReportSection id="bmc" number={8} title={t.sectionBmc}>
        <BMCSection
          analysisData={analysisData}
          project={project}
          bmc={analysisData.business_model_canvas}
          language={reportLanguage}
        />
      </ReportSection>

      <ReportSection id="sources" number={9} title={t.sectionSources}>
        <SourcesAndCompetitorsSection
          analysisData={analysisData}
          project={project}
          language={reportLanguage}
        />
      </ReportSection>

      <ReportSection id="financial" number={10} title={t.sectionFinancial}>
        <FinancialEstimationSection
          analysisData={analysisData}
          project={project}
          financialEstimation={analysisData.financial_estimation}
          language={reportLanguage}
        />
      </ReportSection>

      <ReportSection id="startup-score" number={11} title={t.sectionStartupScore}>
        <StartupScoreSection
          analysisData={analysisData}
          project={project}
          startupScore={analysisData.startup_score}
          language={reportLanguage}
        />
      </ReportSection>

      <ReportSection id="debate" number={12} title={t.sectionDebate}>
        <DebateRoomSection
          debateRoom={analysisData.debate_room}
          language={reportLanguage}
        />
      </ReportSection>

      <ReportSection id="verdict" number={13} title={t.sectionVerdict}>
        <FinalVerdictSection
          analysisData={analysisData}
          project={project}
          language={reportLanguage}
        />
      </ReportSection>

      <ReportSection id="action-plan" number={14} title={t.sectionActionPlan}>
        <RecommendedActionPlanSection
          analysisData={analysisData}
          project={project}
          language={reportLanguage}
        />
      </ReportSection>

      <ReportSection id="limitations" number={15} title={t.sectionLimitations}>
        <FactCheckSection
          factCheckReport={analysisData.fact_check_report}
          language={reportLanguage}
        />

        <div className="mt-6">
          <AnalysisLimitationsSection
            analysisData={analysisData}
            project={project}
            language={reportLanguage}
          />
        </div>
      </ReportSection>
    </section>
  );
}