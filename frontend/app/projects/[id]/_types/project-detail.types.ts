export type AnalysisStatus =
  | "not_started"
  | "queued"
  | "pending"
  | "running"
  | "needs_clarification"
  | "completed"
  | "failed"
  | string;

export type OutputLanguage = "fr" | "en" | string;

export type TextList = string[] | string | null | undefined;


export type ContextReadinessStatus =
  | "ready"
  | "ready_cautious"
  | "needs_clarification"
  | "insufficient_context"
  | "out_of_scope"
  | string;

export interface ContextConfidenceData {
  score?: number;
  status?: ContextReadinessStatus;
  missing_fields?: string[];
  ambiguous_fields?: string[];
  blockers?: string[];
  clarification_questions?: string[];
  reasons?: string[];
  ready_for_agents?: boolean;
}

export interface IdeaReadinessChecklistItem {
  key?: string;
  label?: string;
  checked?: boolean;
  required?: boolean;
}

export interface IdeaReadinessData {
  format?: string;
  canonical_format?: string;
  schema_version?: string;
  status?: ContextReadinessStatus;
  score?: number;
  threshold?: number;
  ready_for_agents?: boolean;
  detected?: Record<string, unknown>;
  missing_fields?: string[];
  ambiguous_fields?: string[];
  blockers?: string[];
  assumptions?: string[];
  questions?: string[];
  clarification_questions?: string[];
  checklist?: IdeaReadinessChecklistItem[];
  recommendation?: string;
  reasons?: string[];
  context_confidence?: ContextConfidenceData;
  project_context_packet?: ProjectContextPacketData;
  legacy_project_context?: Record<string, unknown>;
}

export interface ProjectContextPacketData {
  schema_version?: string;
  project_name?: string;
  description?: string;
  language?: OutputLanguage;
  target_region?: string;
  industry_user_input?: string;
  primary_archetype?: string;
  secondary_archetypes?: string[];
  business_model_hypotheses?: string[];
  mvp_scope?: string[];
  constraints?: string[];
  success_metrics?: string[];
  confidence?: ContextConfidenceData;
  [key: string]: unknown;
}

export interface ContextExtractionQuality {
  score?: number;
  missing_fields?: string[];
  ambiguous_fields?: string[];
  ready_for_agents?: boolean;
}

export type SourceDisplayContext = {
  isGlobal: boolean;
  directMetricLabel: string;
  directGroupTitle: string;
  directEmptyText: string;
  adjacentGroupTitle: string;
  adjacentEmptyText: string;
};

export interface Project {
  id: number;
  title: string;
  description: string;
  industry?: string | null;
  market_region?: string | null;
  output_language?: OutputLanguage | null;
  status?: string | null;
  startup_score?: number | null;
  analysis_status?: AnalysisStatus | null;
  analysis_step?: string | null;
  analysis_progress?: number | null;
  analysis_data?: AnalysisData | null;
  analysis_error?: string | null;
  analysis_started_at?: string | null;
  analysis_completed_at?: string | null;
  analysis_run_id?: string | null;
  analysis_heartbeat_at?: string | null;
  analysis_attempt?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface MarketStudy {
  format?: string;
  status?: string;
  context_locked?: boolean;
  output_language?: OutputLanguage;
  market_size?: string;
  target_market?: string;
  target_customers?: TextList;
  market_trends?: string[];
  market_trend_signals?: string[];
  market_trends_status?: string;
  customer_segments?: TextList;
  opportunities?: string[];
  risks?: string[];
  data_confidence?: string;
}

export interface SWOT {
  format?: string;
  status?: string;
  context_locked?: boolean;
  output_language?: OutputLanguage;
  strengths?: string[];
  weaknesses?: string[];
  opportunities?: string[];
  threats?: string[];
}

export interface BusinessModelCanvas {
  format?: string;
  status?: string;
  context_locked?: boolean;
  output_language?: OutputLanguage;
  value_proposition?: string | string[];
  customer_segments?: string | string[];
  channels?: string | string[];
  customer_relationships?: string | string[];
  revenue_streams?: string | string[];
  key_resources?: string | string[];
  key_activities?: string | string[];
  key_partners?: string | string[];
  cost_structure?: string | string[];
}

export interface SourceItem {
  title?: string;
  url?: string;
  snippet?: string;
  extracted_text_preview?: string;
  source_type?: string;
  source_role?: string;
  comparison_scope?: string;
  technology_supplier?: boolean;
  canonical_source_id?: string;
  region_match?: string;
  is_direct_competitor?: boolean;
  target_match_level?: string;
  is_product_page?: boolean;
  grounded?: boolean;
  provider?: string;
  why_relevant?: string;
  search_query?: string | null;
  extraction_method?: string;
  text_extracted?: boolean;
  pricing_found?: boolean;
  confidence?: string;
  confidence_level?: string;
  source_relevance_score?: number;
  public_display?: boolean;
  internal_only?: boolean;
  rejected?: boolean;
  matched_strong_terms?: string[];
  matched_weak_terms?: string[];
  matched_forbidden_terms?: string[];
  matched_domain_terms?: string[];
  matched_target_terms?: string[];
  matched_use_case_terms?: string[];
  matched_solution_terms?: string[];
  product_evidence_signals?: string[];
  market_evidence_signals?: string[];
  evidence_categories?: string[];
  same_or_close_target_user?: boolean;
  same_or_close_use_case?: boolean;
  same_or_close_solution_category?: boolean;
  clear_contextual_link?: boolean;
  vendor_key?: string;
  vendor_name?: string;
  canonical_vendor_domain?: string;
  sector_mismatch?: boolean;
  mismatch_terms?: string[];
  search_provider?: string;
  provider_score?: number;
  rejection_reason?: string;
  error?: string | null;
}

export interface CanonicalSourceLedger {
  version?: string;
  sources?: SourceItem[];
  sources_count?: number;
  roles?: Record<string, SourceItem[]>;
  counts?: Record<string, number>;
}

export interface ExternalSources {
  format?: string;
  query?: string;
  queries?: string[];
  target_region?: string;
  status?: string;
  confidence_level?: string;
  source_based?: boolean;
  context_locked?: boolean;
  sources_count?: number;
  canonical_sources_count?: number;
  canonical_source_ledger?: CanonicalSourceLedger;
  internal_sources_count?: number;
  rejected_sources_count?: number;
  local_competitors_found?: boolean;
  local_competitors_count?: number;
  regional_competitors_count?: number;
  international_benchmarks_count?: number;
  technology_providers_count?: number;
  market_sources_count?: number;
  sources?: SourceItem[];
  public_sources?: SourceItem[];
  retained_sources?: SourceItem[];
  technology_provider_sources?: SourceItem[];
  adjacent_solution_sources?: SourceItem[];
  local_competitor_sources?: SourceItem[];
  regional_competitor_sources?: SourceItem[];
  international_benchmark_sources?: SourceItem[];
  market_context_sources?: SourceItem[];
  errors?: string[];
  limitations?: string[];
  no_verified_relevant_source_found?: boolean;
  no_source_message?: string;
}

export interface VerifiedCompetitor {
  name?: string;
  title?: string;
  region?: string;
  region_match?: string;
  source_type?: string;
  source_role?: string;
  comparison_scope?: string;
  technology_supplier?: boolean;
  canonical_source_id?: string;
  description?: string;
  evidence?: string;
  source_url?: string;
  url?: string;
  pricing?: string;
  why_relevant?: string;
  vendor_key?: string;
  canonical_vendor_domain?: string;
  sector_mismatch?: boolean;
  mismatch_terms?: string[];
}

export interface MarketContextSource {
  title?: string;
  source_type?: string;
  evidence?: string;
  source_url?: string;
  url?: string;
  why_relevant?: string;
}

export interface CompetitiveAnalysis {
  format?: string;
  status?: string;
  context_locked?: boolean;
  output_language?: OutputLanguage;
  direct_competitors?: string[];
  indirect_competitors?: string[];
  competitive_advantages?: string[];
  market_gap?: string;
  source_based?: boolean;
  confidence_level?: string;
  sources_count?: number;
  canonical_sources_count?: number;
  canonical_source_ledger?: CanonicalSourceLedger;
  limitations?: string[];
  local_competitors_count?: number;
  local_adjacent_solutions_count?: number;
  regional_competitors_count?: number;
  international_benchmarks_count?: number;
  technology_providers_count?: number;
  market_sources_count?: number;
  no_local_competitor_found?: boolean;
  local_direct_competitors?: VerifiedCompetitor[];
  local_adjacent_solutions?: VerifiedCompetitor[];
  regional_competitors?: VerifiedCompetitor[];
  international_benchmarks?: VerifiedCompetitor[];
  technology_providers?: VerifiedCompetitor[];
  market_context_sources?: MarketContextSource[];
  sources?: SourceItem[];
  public_sources?: SourceItem[];
  technology_provider_sources?: SourceItem[];
  adjacent_solution_sources?: SourceItem[];
  local_competitor_sources?: SourceItem[];
  regional_competitor_sources?: SourceItem[];
  international_benchmark_sources?: SourceItem[];
  market_sources?: SourceItem[];
  external_sources?: SourceItem[];
  coverage_status?: string;
  search_coverage?: string;
  source_relevance_confidence?: string;
  source_confidence?: string;
}

export interface FinancialEstimation {
  format?: string;
  status?: string;
  context_locked?: boolean;
  output_language?: OutputLanguage;
  mvp_budget_estimate?: string;
  infrastructure_cost_estimate?: string;
  possible_revenue_streams?: string[];
  roi_outlook?: string;
  financial_risk_level?: string;
}

export interface StartupScore {
  format?: string;
  status?: string;
  context_locked?: boolean;
  output_language?: OutputLanguage;

  score?: number;
  startup_score?: number;
  overall_score?: number;
  final_score?: number;
  score_out_of_10?: number;
  global_score?: number;

  innovation?: number;
  feasibility?: number;
  profitability?: number;
  scalability?: number;

  summary?: string;
  score_explanation?: string;
  verdict?: string;
  verdict_code?: string;
  canonical_verdict_code?: string;
  risk_level?: string;
  confidence_level?: string;
  investment_readiness?: string;
  breakdown?: Record<string, number>;
  score_breakdown?: Record<string, number>;
  criteria_scores?: Record<string, number>;
  strengths?: string[];
  weaknesses?: string[];
  next_actions?: string[];

  potential_score?: number;
  evidence_confidence_score?: number;
  execution_readiness_score?: number;
  evidence_confidence_level?: string;
  overall_evidence_confidence?: string;
  decision_score?: number;

  manual_review_required?: boolean;
  score_warning?: string | null;
}

export interface PersonaItem {
  id?: string;
  name?: string;
  persona_name?: string;
  role?: string;
  segment?: string;
  profile?: string;
  context?: string;
  main_pain?: string;
  current_alternatives?: string[];
  expected_value?: string;
  adoption_trigger?: string;
  objections?: string[];
  buying_power?: string;
  decision_power?: string;
  urgency_level?: string;
  success_metrics?: string[];
  interview_questions?: string[];

  age?: number | null;
  location?: string;
  profession?: string;
  goals?: string[];
  frustrations?: string[];
  preferred_channels?: string[];
  budget_level?: string;
  budget_explanation?: string;
  tech_level?: string;
  user_journey?: string;
  use_case?: string;
  adoption_obstacles?: string[];
  message_to_convince?: string;
}

export interface PersonaBuilderData {
  format?: string;
  status?: string;
  output_language?: OutputLanguage;
  context_locked?: boolean;
  summary?: string;
  persona_summary?: string;
  primary_persona?: PersonaItem;
  personas?: PersonaItem[];
  target_segments?: string[];
  buyer_user_difference?: string;
  validation_questions?: string[];
  persona_risks?: string[];
  recommended_validation_method?: string[];
  limitations?: string[];
  manual_review_required?: boolean;
  fallback_used?: boolean;
  error_handled?: boolean;
}

export interface FactCheckEvidence {
  display_title?: string;
  title?: string;
  source_title?: string;
  name?: string;
  vendor_name?: string;
  url?: string;
  source_type?: string;
  source_role?: string;
  canonical_category?: string;
  region_match?: string;
  confidence?: string;
  public_confidence?: string;
  source_relevance_score?: number;
  why_relevant?: string;
  public_reason?: string;
  evidence_categories?: string[];
  is_direct_competitor?: boolean;
}

export interface FactCheckClaim {
  claim?: string;
  path?: string;
  category?: string;
  status?: string;
  public_status?: string;
  confidence?: string;
  public_confidence?: string;
  evidence?: Array<FactCheckEvidence | string>;
  consulted_sources?: Array<FactCheckEvidence | string>;
  evidence_kind?: "supporting" | "consulted_insufficient" | string;
  correction?: string | null;
}

export interface FactCheckSourceSummary {
  total_sources?: number;
  sources_with_url?: number;
  verified_competitors?: number;
  relevant_sources?: number;
  local_competitor_sources?: number;
  local_adjacent_solutions?: number;
  regional_benchmarks?: number;
  international_benchmarks?: number;
  market_evidence?: number;
  market_size_evidence?: number;
  market_demand_evidence?: number;
  problem_evidence?: number;
  solution_evidence?: number;
  pricing_evidence?: number;
  source_confidence?: string;
}

export interface FactCheckReport {
  format?: string;
  status?: string;
  method?: string;
  summary?: string;
  fact_check_summary?: string;
  claims?: FactCheckClaim[];
  source_count?: number;
  relevant_source_count?: number;
  source_summary?: FactCheckSourceSummary;
  retained_sources?: FactCheckEvidence[];
  global_confidence?: string;
  confidence_level?: string;
  supported_claims?: string[];
  uncertain_claims?: string[];
  warnings?: string[];
  red_flags?: string[];
  recommended_next_checks?: string[];
  recommended_validation?: string[];
  limitations?: string[];
}

export interface DebateRoomModerator {
  role?: string;
  round?: number;
  topic?: string;
  focus?: string;
  key_question?: string;
  data_sources?: string[];
}

export interface DebateCommitteeMember {
  id?: string;
  role?: string;
  mandate?: string;
  voting_member?: boolean;
}

export interface DebateMemberPosition {
  member?: string;
  position?: string;
  confidence?: string | number;
  summary?: string;
}

export interface DebateEvidenceUsedItem extends SourceItem {
  source_id?: string;
}

export interface DebateQuestionAnswer {
  direct_answer?: string;
  reasoning_summary?: string;
  confidence?: number;

  support_status?: string;

  evidence_status?: string;
  claim_kind?: string;
  validation_required?: boolean;

  source_ids?: string[];

  // Temporary backend compatibility alias.
  evidence_ids?: string[];

  evidence_used?: DebateEvidenceUsedItem[];

  canonical_claim_id?: string;
  canonical_claim_found?: boolean;

  /**
   * Canonical question-level authority declared by Debate Room.
   * The UI must display this value and must not infer authority
   * from source_ids, evidence_status or canonical_claim_id.
   */
  authority_mode?:
    | "claim"
    | "sources"
    | "context"
    | "synthesis"
    | "none"
    | "legacy_category";

  unresolved_point?: string;
}

export interface DebateQuestionMeetingPreparation {
  likely_real_question?: string;
  recommended_answer?: string;
  proofs_to_prepare?: string[];
  answer_to_avoid?: string;
}

export interface DebateCommitteeQuestion {
  question_id?: string;
  asked_by?: string;
  addressed_to?: string;
  answered_by?: string;
  question?: string;
  question_type?: string;
  answer?: DebateQuestionAnswer;
  follow_up_question?: string;
  meeting_preparation?: DebateQuestionMeetingPreparation;
}

export interface DebateEvidenceAuditItem {
  claim?: string;
  status?: string;
  confidence?: string | number;
  evidence_ids?: string[];
}

export interface DebateRoundMeetingPreparation {
  likely_questions?: string[];
  recommended_answers?: string[];
  proofs_to_prepare?: string[];
  answers_to_avoid?: string[];
  unresolved_points?: string[];
  follow_up_questions?: string[];
}

export interface DebateGlobalMeetingPreparation {
  title?: string;
  project?: string;
  top_questions?: string[];
  recommended_answers?: string[];
  proofs_to_prepare?: string[];
  answers_to_avoid?: string[];
  unresolved_questions?: string[];
  unresolved_points?: string[];
  follow_up_questions?: string[];
}

export interface DebateRoomDefender {
  role?: string;
  round?: number;
  position?: string;
  main_argument?: string;
  supporting_points?: string[];
  opportunities?: string[];
  response_to_previous_critic?: string;
  assumptions?: string[];
  opportunity_score?: number;
}

export interface DebateRoomCritic {
  role?: string;
  round?: number;
  main_objection?: string;
  critical_risks?: string[];
  weak_assumptions?: string[];
  missing_evidence?: string[];
  counter_recommendation?: string;
  risk_score?: number;
}

export interface DebateRoomRoundSummary {
  validated_points?: string[];
  potential_opportunities?: string[];
  remaining_risks?: string[];
  decision?: string;
  synthesis?: string;
  next_action?: string;
  go_conditions?: string[];
  no_go_conditions?: string[];
}

export interface DebateRoomRound {
  round?: number;
  topic?: string;
  objective?: string;
  main_question?: string;
  moderator?: DebateRoomModerator;
  member_positions?: DebateMemberPosition[];
  defender?: DebateRoomDefender;
  critic?: DebateRoomCritic;
  committee_questions?: DebateCommitteeQuestion[];
  cross_examination?: DebateCommitteeQuestion[];
  evidence_audit?: DebateEvidenceAuditItem[];
  agreements?: string[];
  disagreements?: string[];
  unresolved_questions?: string[];
  meeting_preparation?: DebateRoundMeetingPreparation;
  round_summary?: DebateRoomRoundSummary;
  context_locked?: boolean;
  output_language?: OutputLanguage;
}

export interface DebateDecisionByRound {
  round?: number;
  topic?: string;
  decision?: string;
  critic_risk_score?: number;
  main_objection?: string;
  synthesis?: string;
}

export interface DebateCommitteeVote {
  member?: string;
  vote?: string;
  confidence?: number;
  confidence_basis?: {
    evidence_score?: number;
    execution_readiness_score?: number;
    role_adjustment?: number;
    formula?: string;
  };
  blocking_conditions?: string[];
  reason?: string;
  veto?: boolean;
}

export interface DebateRoomJudge {
  format?: string;
  status?: string;
  context_locked?: boolean;
  output_language?: OutputLanguage;
  role?: string;
  verdict?: string;
  verdict_code?: string;
  argument_strength_score?: number;
  confidence_score?: number;
  risk_level?: string;
  critical_risks?: string[];
  validated_findings?: string[];
  validated_opportunities?: string[];
  potential_opportunities?: string[];
  potential_score?: number;
  evidence_confidence_score?: number;
  execution_readiness_score?: number;
  investment_attractiveness_score?: number;
  improved_idea?: string;
  final_recommendation?: string;
  next_actions?: string[];
  action_plan?: string[];
  decision_by_round?: DebateDecisionByRound[];
  debate_synthesis?: string;
  go_no_go_conditions?: string[];
  go_conditions?: string[];
  no_go_conditions?: string[];
  missing_evidence?: string[];
  weak_assumptions?: string[];
  committee_votes?: DebateCommitteeVote[];
  committee_vote?: Record<string, number>;
  vetoes?: DebateCommitteeVote[];
}

export interface DebateRoomMeta {
  completed_steps?: string[];
  failed_steps?: string[];
  progress?: number;
  current_step?: string;
  completed?: boolean;
  error?: string | null;
  output_language?: OutputLanguage;
  context_locked?: boolean;
  llm_used?: boolean;
  evidence_aware?: boolean;
  questions_visible?: boolean;
  meeting_preparation_enabled?: boolean;
  fallback_used?: boolean;
  format?: string;
  status?: string;
}

export interface DebateRoomData {
  format?: string;
  title?: string;
  status?: string;
  output_language?: OutputLanguage;
  context_locked?: boolean;
  max_rounds?: number;
  committee?: DebateCommitteeMember[];
  rounds?: DebateRoomRound[];
  judge?: DebateRoomJudge;
  meeting_preparation?: DebateGlobalMeetingPreparation;
  meta?: DebateRoomMeta;
  project_context_used?: Record<string, unknown>;
  evidence_packet_used?: Record<string, unknown>;
}

export interface FinalReportPublicSource extends SourceItem {
  source_id?: string;
}

export type FinalReportEvidenceStatus =
  | "sourced"
  | "estimated"
  | "not_confirmed"
  | string;

export type FinalReportClaimKind =
  | "evidence_claim"
  | "hypothesis"
  | "estimate"
  | "recommendation"
  | "audit_conclusion"
  | "project_input"
  | string;

export interface FinalReportClaim {
  claim_id?: string;
  path?: string;
  category?: string;
  claim?: string;
  public_text?: string;
  text?: string;
  confidence?: string;
  evidence_status?: FinalReportEvidenceStatus;
  claim_kind?: FinalReportClaimKind;
  validation_required?: boolean;
  source_ids?: string[];
  supporting_evidence?: FinalReportPublicSource[];
  consulted_sources?: FinalReportPublicSource[];
}

export interface FinalReportContext {
  schema_version?: string;
  project_name?: string;
  sector?: string;
  target_region?: string;
}

export interface FinalReportAuthorityContract {
  context?: string;
  sources?: string;
  evidence?: string;
  decision?: string;
  recalculates_readiness?: boolean;
  reclassifies_sources?: boolean;
  reclassifies_evidence?: boolean;
  recalculates_verdict?: boolean;
}

export interface FinalReportExecutiveSummary {
  decision_source?: string;
  verdict_code?: string;
  final_recommendation?: string;
  evidence_counts?: {
    sourced?: number;
    estimated?: number;
    not_confirmed?: number;
    unclassified?: number;
    validation_required?: number;
  };
  supported_claims?: FinalReportClaim[];
  estimated_claims?: FinalReportClaim[];
  not_confirmed_claims?: FinalReportClaim[];
  unclassified_claims?: FinalReportClaim[];
  validation_priorities?: FinalReportClaim[];
}

export interface FinalReportDecision {
  available?: boolean;
  format?: string;
  status?: string;

  source?: string;
  verdict?: string;
  verdict_code?: string;

  final_recommendation?: string;
  risk_level?: string;

  argument_strength_score?: number;
  confidence_score?: number;

  debate_synthesis?: string;
  improved_idea?: string;

  next_actions?: string[];
  action_plan?: string[];

  critical_risks?: string[];
  validated_findings?: string[];
  validated_opportunities?: string[];
  potential_opportunities?: string[];
  missing_evidence?: string[];
  weak_assumptions?: string[];

  go_conditions?: string[];
  no_go_conditions?: string[];
  go_no_go_conditions?: string[];

  decision_by_round?: DebateDecisionByRound[];
  committee_vote?: unknown;
  vetoes?: unknown;
}

export interface FinalReportCompetitive {
  source_ledger_present?: boolean;
  source_ledger_source?: string;
  canonical_sources_count?: number;
  counts?: Record<string, number>;

  canonical_source_ids?: string[];
  local_direct_competitor_source_ids?: string[];
  direct_competitor_source_ids?: string[];
  adjacent_solution_source_ids?: string[];
  regional_benchmark_source_ids?: string[];
  international_benchmark_source_ids?: string[];
  technology_provider_source_ids?: string[];
  technology_benchmark_source_ids?: string[];
  local_ecosystem_source_ids?: string[];
  ecosystem_actor_source_ids?: string[];
  market_context_source_ids?: string[];
  market_evidence_source_ids?: string[];
  official_source_items_source_ids?: string[];
  directory_source_ids?: string[];
  evidence_source_ids?: string[];
  benchmark_source_ids?: string[];
}

export interface FinalReportEvidence {
  ledger_present?: boolean;
  canonical_evidence_statuses?: string[];
  status_contract?: Record<string, unknown>;
  claims?: FinalReportClaim[];
  source_index?: Record<
    string,
    FinalReportPublicSource
  >;
}

export interface FinalReportStartupScore {
  global_score?: number;
  innovation?: number;
  feasibility?: number;
  profitability?: number;
  scalability?: number;
  score_explanation?: string;
}

export interface FinalReportMeetingPreparation {
  title?: string;
  project?: string;
  top_questions?: string[];
  recommended_answers?: string[];
  proofs_to_prepare?: string[];
  answers_to_avoid?: string[];
  unresolved_questions?: string[];
  unresolved_points?: string[];
  follow_up_questions?: string[];
}

export interface FinalReportData {
  format?: string;
  schema_version?: string;

  authority_contract?: FinalReportAuthorityContract;
  context?: FinalReportContext;
  executive_summary?: FinalReportExecutiveSummary;
  decision?: FinalReportDecision;
  competitive?: FinalReportCompetitive;
  evidence?: FinalReportEvidence;
  startup_score?: FinalReportStartupScore;
  meeting_preparation?: FinalReportMeetingPreparation;
  module_presence?: Record<string, boolean>;
}

export interface StartupEvaluatorMeta {
  completed_steps?: string[];
  failed_steps?: string[];
  progress?: number;
  current_step?: string;
  error?: string | null;
}

export interface AnalysisData {
  summary?: string;
  detected_sector?: string;
  target_region?: string;
  output_language?: OutputLanguage;
  problem?: string;
  target_users?: string;
  recommended_technologies?: string[];
  difficulty?: string;
  global_market_assessment?: string;
  local_market_assessment?: string;
  data_limitations?: string;
  sources_used?: string[];
  improvement_suggestions?: string[];

  target_market?: string;
  problem_solved?: string;
  proposed_solution?: string;
  business_model?: string;
  revenue_model?: string;
  risks?: string[] | string;
  recommendations?: string[] | string;
  innovation_score?: number;

  market_study?: MarketStudy;
  swot?: SWOT;
  business_model_canvas?: BusinessModelCanvas;
  forgecrawler?: ExternalSources;
  competitive_analysis?: CompetitiveAnalysis;
  financial_estimation?: FinancialEstimation;
  startup_score?: StartupScore;

  persona_builder?: PersonaBuilderData;
  personas?: PersonaBuilderData;

  fact_check_report?: FactCheckReport;
  debate_room?: DebateRoomData;
  final_report?: FinalReportData;
  startup_evaluator_meta?: StartupEvaluatorMeta;
  public_limitations?: string[];
  evidence_ledger?: {
    format?: string;
    claims?: Array<{
      claim_id?: string; category?: string; claim?: string; source_ids?: string[];
      status?: string; confidence?: string; public_text?: string;
    }>;
    confidence_by_category?: Record<string, string>;
  };
  evidence_confidence?: Record<string, string>;
  overall_evidence_confidence?: string;
  search_coverage?: string;
  source_relevance_confidence?: string;
  verdict_code?: string;
  needs_clarification?: boolean;
  idea_readiness?: IdeaReadinessData;
  context_confidence?: ContextConfidenceData;
  context_extraction_quality?: ContextExtractionQuality;
  project_context_packet?: ProjectContextPacketData;
  legacy_project_context?: Record<string, unknown>;
  agent_context_packet?: Record<string, unknown>;
  query_planner?: Record<string, unknown>;

  structured_project_context?: Record<string, unknown>;
  project_intelligence?: {
    structured_project_context?: Record<string, unknown>;
    [key: string]: unknown;
  };
  partial_completion?: boolean;
}

export interface ProjectAnalysisResponse {
  project_id?: number;
  analysis_status?: AnalysisStatus | null;
  analysis_step?: string | null;
  analysis_progress?: number | null;
  analysis_data?: AnalysisData | null;
  analysis_error?: string | null;
  analysis_started_at?: string | null;
  analysis_completed_at?: string | null;
  analysis_run_id?: string | null;
  analysis_heartbeat_at?: string | null;
  analysis_attempt?: number | null;
}
