"use client";

import { useForgeLanguage, type ForgeLang } from "@/lib/language-context";

import type {
  DebateCommitteeQuestion,
  DebateMemberPosition,
  DebateRoomRound,
} from "../../_types/project-detail.types";

import { reportCopy } from "../../_lib/report-copy";
import { cleanText } from "../../_lib/text-cleaning";

function resolveLanguage(
  language: ForgeLang | undefined,
  fallback: ForgeLang
): ForgeLang {
  return language === "en" || language === "fr" ? language : fallback;
}

function cleanedItems(items: Array<string | null | undefined>, language: ForgeLang) {
  const seen = new Set<string>();
  return items
    .map((item) => cleanText(item || "", language))
    .filter(Boolean)
    .filter((item) => {
      const key = item.toLocaleLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
}

function roleLabel(value: string | undefined, language: ForgeLang): string {
  const rawRole = String(value || "").toLowerCase();
  const role =
    rawRole === "all_committee_members"
      ? "all_members"
      : rawRole;
  const labels: Record<string, [string, string]> = {
    committee_chair: ["Committee Chair", "Président du comité"],
    customer_problem_analyst: ["Customer & Problem Analyst", "Analyste client et problème"],
    market_competition_analyst: ["Market & Competition Analyst", "Analyste marché et concurrence"],
    product_technology_architect: ["Product & Technology Architect", "Architecte produit et technologie"],
    business_financial_analyst: ["Business & Financial Analyst", "Analyste business et financier"],
    risk_execution_officer: ["Risk & Execution Officer", "Responsable risque et exécution"],
    evidence_auditor: ["Evidence Auditor", "Auditeur des preuves"],
    red_team_challenger: ["Red Team Challenger", "Challenger Red Team"],
    project_defender: ["Project Defender", "Défenseur du projet"],
    critical_analyst: ["Critical Analyst", "Analyste critique"],
    all_members: ["All committee members", "Tous les membres du comité"],
  };
  const label = labels[role];
  if (label) return language === "en" ? label[0] : label[1];
  return cleanText(value || (language === "en" ? "Committee member" : "Membre du comité"), language);
}

function verdictLabel(value: string | undefined, language: ForgeLang): string {
  const normalized = String(value || "").toLowerCase();
  if (normalized.includes("conditional")) {
    return language === "en" ? "Conditional Go" : "GO conditionnel";
  }
  if (normalized.includes("insufficient")) {
    return language === "en" ? "Insufficient evidence" : "Preuves insuffisantes";
  }
  if (normalized.includes("pivot")) return language === "en" ? "Pivot" : "Pivoter";
  if (normalized.includes("no_go") || normalized.includes("stop")) {
    return language === "en" ? "No-Go" : "NO-GO";
  }
  if (normalized === "go") return "GO";
  return cleanText(value || (language === "en" ? "Decision pending" : "Décision en attente"), language);
}

function evidenceStatusLabel(value: string | undefined, language: ForgeLang): string {
  const normalized = String(value || "").toLowerCase();
  const labels: Record<string, [string, string]> = {
    supported: ["Supported", "Soutenu"],
    sourced: ["Sourced", "Sourcé"],
    verified: ["Verified", "Vérifié"],
    estimated: ["Estimated", "Estimé"],
    hypothesis: ["Hypothesis", "Hypothèse"],
    field_validation_required: ["Field validation required", "Validation terrain requise"],
    not_confirmed: ["Not confirmed", "Non confirmé"],
    evidence_audit: ["Evidence audit", "Audit des preuves"],
    committee_synthesis: ["Committee synthesis", "Synthèse du comité"],
  };
  const label = labels[normalized];
  if (label) return language === "en" ? label[0] : label[1];
  return cleanText(value || (language === "en" ? "Unclassified" : "Non classé"), language);
}

function authorityLabel(
  value: string | undefined,
  language: ForgeLang
): string {
  const mode = String(value || "").toLowerCase();

  const labels: Record<string, [string, string]> = {
    claim: [
      "Canonical claim",
      "Claim canonique",
    ],
    sources: [
      "Canonical sources",
      "Sources canoniques",
    ],
    context: [
      "Structured project context",
      "Contexte structuré du projet",
    ],
    synthesis: [
      "Committee synthesis",
      "Synthèse du comité",
    ],
    none: [
      "No evidence authority attached",
      "Aucune autorité de preuve attachée",
    ],
    legacy_category: [
      "Legacy evidence projection",
      "Projection de preuve historique",
    ],
  };

  const label = labels[mode];

  if (label) {
    return language === "en"
      ? label[0]
      : label[1];
  }

  return language === "en"
    ? "Authority not specified"
    : "Autorité non spécifiée";
}


function authorityExplanation(
  value: string | undefined,
  language: ForgeLang
): string {
  const mode = String(value || "").toLowerCase();

  if (mode === "claim") {
    return language === "en"
      ? "This answer projects an explicitly selected canonical evidence claim."
      : "Cette réponse projette un claim de preuve canonique explicitement sélectionné.";
  }

  if (mode === "sources") {
    return language === "en"
      ? "This answer consumes explicitly selected canonical sources. Claim evidence status is not used to classify those sources."
      : "Cette réponse consomme des sources canoniques explicitement sélectionnées. Le statut de preuve d'un claim n'est pas utilisé pour classifier ces sources.";
  }

  if (mode === "context") {
    return language === "en"
      ? "This answer is based on the canonical structured project context. No independent evidence claim is attached."
      : "Cette réponse repose sur le contexte structuré canonique du projet. Aucun claim de preuve indépendant n'est attaché.";
  }

  if (mode === "synthesis") {
    return language === "en"
      ? "This answer is a committee synthesis. No evidence claim or source is artificially attached."
      : "Cette réponse est une synthèse du comité. Aucun claim ni aucune source n'est artificiellement attaché.";
  }

  if (mode === "none") {
    return language === "en"
      ? "No canonical evidence authority is attached to this answer."
      : "Aucune autorité de preuve canonique n'est attachée à cette réponse.";
  }

  if (mode === "legacy_category") {
    return language === "en"
      ? "This historical answer uses the legacy category-based evidence projection."
      : "Cette réponse historique utilise la projection de preuve par catégorie héritée.";
  }

  return "";
}


function confidenceLabel(value: number | string | undefined, language: ForgeLang): string {
  if (typeof value === "number" && Number.isFinite(value)) {
    return `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%`;
  }
  const normalized = String(value || "").toLowerCase();
  if (normalized.includes("high") || normalized.includes("élev")) {
    return language === "en" ? "High" : "Élevée";
  }
  if (normalized.includes("medium") || normalized.includes("moy")) {
    return language === "en" ? "Medium" : "Moyenne";
  }
  if (normalized.includes("low") || normalized.includes("faib")) {
    return language === "en" ? "Low" : "Faible";
  }
  return language === "en" ? "Qualitative" : "Qualitative";
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
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <p className="text-[11px] font-black uppercase tracking-[0.17em] text-slate-400">
        {title}
      </p>
      <p className="mt-2 whitespace-pre-wrap text-sm font-semibold leading-6 text-slate-700">
        {cleaned}
      </p>
    </div>
  );
}

function ListBlock({
  title,
  items,
  language,
  emptyText,
}: {
  title: string;
  items?: string[];
  language: ForgeLang;
  emptyText?: string;
}) {
  const values = cleanedItems(items || [], language);
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <p className="text-[11px] font-black uppercase tracking-[0.17em] text-slate-400">
        {title}
      </p>
      {values.length ? (
        <ul className="mt-2 space-y-2">
          {values.map((item, index) => (
            <li key={`${title}-${index}`} className="rounded-xl bg-slate-50 px-3 py-2 text-sm font-semibold leading-6 text-slate-700">
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm font-semibold text-slate-400">
          {emptyText || (language === "en" ? "No item established." : "Aucun élément établi.")}
        </p>
      )}
    </div>
  );
}

function PositionCard({
  position,
  language,
}: {
  position: DebateMemberPosition;
  language: ForgeLang;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-black text-slate-900">{roleLabel(position.member, language)}</p>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-black uppercase tracking-wide text-slate-600">
          {confidenceLabel(position.confidence, language)}
        </span>
      </div>
      <p className="mt-2 text-sm font-semibold leading-6 text-slate-700">
        {cleanText(position.summary || position.position || "", language)}
      </p>
    </div>
  );
}

function QuestionCard({
  item,
  index,
  language,
}: {
  item: DebateCommitteeQuestion;
  index: number;
  language: ForgeLang;
}) {
  const answer = item.answer || {};
  const prep = item.meeting_preparation || {};
  const proofs = cleanedItems(prep.proofs_to_prepare || [], language);


  const authorityMode =
    answer.authority_mode ||
    "legacy_category";

  const authorityText = authorityExplanation(
    authorityMode,
    language
  );

  const canonicalSourceIds =
    answer.source_ids?.length
      ? answer.source_ids
      : answer.evidence_ids || [];

  const sourceIds = Array.from(
    new Set(
      canonicalSourceIds
        .map((sourceId) =>
          String(sourceId || "").trim()
        )
        .filter(Boolean)
    )
  );

  const evidenceUsed = Array.from(
    new Set(
      (answer.evidence_used || [])
        .map((source) => {
          const title = cleanText(
            source.title || "",
            language
          );

          const sourceId = String(
            source.source_id || ""
          ).trim();

          if (title && sourceId) {
            return `${title} · ${sourceId}`;
          }

          return title || sourceId;
        })
        .filter(Boolean)
    )
  );

  return (
    <article className="rounded-3xl border border-sky-200 bg-sky-50/50 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.16em] text-sky-600">
            {language === "en" ? `Committee question ${index + 1}` : `Question du comité ${index + 1}`}
          </p>
          <p className="mt-1 text-xs font-bold text-slate-500">
            {language === "en" ? "Asked by" : "Question posée par"}:{" "}
            {roleLabel(item.asked_by, language)}
            {" · "}
            {language === "en" ? "Addressed to" : "Adressée à"}:{" "}
            {roleLabel(item.addressed_to, language)}
            {item.answered_by && (
              <>
                {" · "}
                {language === "en" ? "Answered by" : "Réponse par"}:{" "}
                {roleLabel(item.answered_by, language)}
              </>
            )}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="rounded-full bg-white px-3 py-1 text-[11px] font-black text-slate-600 shadow-sm">
            {language === "en" ? "Authority" : "Autorité"}:{" "}
            {authorityLabel(
              authorityMode,
              language
            )}
          </span>

          {(authorityMode === "claim" ||
            authorityMode === "legacy_category") && (
            <span className="rounded-full bg-white px-3 py-1 text-[11px] font-black text-slate-600 shadow-sm">
              {language === "en" ? "Evidence" : "Preuve"}:{" "}
              {evidenceStatusLabel(
                answer.evidence_status,
                language
              )}
            </span>
          )}

          <span className="rounded-full bg-white px-3 py-1 text-[11px] font-black text-slate-600 shadow-sm">
            {language === "en" ? "Confidence" : "Confiance"}:{" "}
            {confidenceLabel(
              answer.confidence,
              language
            )}
          </span>
        </div>
      </div>

      <h5 className="mt-4 text-base font-black leading-7 text-slate-950">
        {cleanText(item.question || "", language)}
      </h5>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <TextBlock
          title={
            language === "en"
              ? "Evidence authority"
              : "Autorité de la réponse"
          }
          value={authorityText}
          language={language}
        />

        {authorityMode === "claim" &&
          answer.canonical_claim_found &&
          answer.canonical_claim_id && (
            <TextBlock
              title={
                language === "en"
                  ? "Canonical claim"
                  : "Claim canonique"
              }
              value={answer.canonical_claim_id}
              language={language}
            />
          )}

        <TextBlock
          title={language === "en" ? "Direct answer" : "Réponse directe"}
          value={answer.direct_answer}
          language={language}
        />
        <TextBlock
          title={language === "en" ? "Reasoning and evidence" : "Justification et preuve"}
          value={answer.reasoning_summary}
          language={language}
        />
        {evidenceUsed.length > 0 && (
          <ListBlock
            title={
              language === "en"
                ? "Evidence used"
                : "Preuves utilisées"
            }
            items={evidenceUsed}
            language={language}
          />
        )}

        {sourceIds.length > 0 && (
          <ListBlock
            title={
              language === "en"
                ? "Canonical source IDs"
                : "Identifiants de sources canoniques"
            }
            items={sourceIds}
            language={language}
          />
        )}

        <TextBlock
          title={language === "en" ? "Unresolved point" : "Point non résolu"}
          value={answer.unresolved_point}
          language={language}
        />
        <TextBlock
          title={language === "en" ? "Follow-up question" : "Question de relance"}
          value={item.follow_up_question}
          language={language}
        />
      </div>

      <details className="mt-4 rounded-2xl border border-amber-200 bg-amber-50/80 p-4" open>
        <summary className="cursor-pointer font-black text-amber-900">
          {language === "en" ? "Prepare for the real meeting" : "Préparation à la réunion réelle"}
        </summary>
        <div className="mt-4 grid gap-3 lg:grid-cols-2">
          <TextBlock
            title={language === "en" ? "Likely real question" : "Question probable"}
            value={prep.likely_real_question}
            language={language}
          />
          <TextBlock
            title={language === "en" ? "Recommended answer" : "Réponse recommandée"}
            value={prep.recommended_answer}
            language={language}
          />
          <ListBlock
            title={language === "en" ? "Proofs to prepare" : "Preuves à préparer"}
            items={proofs}
            language={language}
          />
          <TextBlock
            title={language === "en" ? "Answer to avoid" : "Réponse à éviter"}
            value={prep.answer_to_avoid}
            language={language}
          />
        </div>
      </details>
    </article>
  );
}

export default function DebateRoundCard({
  round,
  index,
  language,
}: {
  round: DebateRoomRound;
  index: number;
  language?: ForgeLang;
}) {
  const { lang } = useForgeLanguage();
  const reportLanguage = resolveLanguage(language, lang);
  const t = reportCopy[reportLanguage];
  const roundNumber = round.round || index + 1;
  const topic = cleanText(
    round.topic || round.moderator?.topic || (reportLanguage === "en" ? `Round ${roundNumber}` : `Tour ${roundNumber}`),
    reportLanguage
  );
  const questions = round.committee_questions || [];
  const positions = round.member_positions || [];
  const audit = round.evidence_audit || [];
  const summary = round.round_summary || {};

  return (
    <section className="rounded-[2rem] border border-slate-200/80 bg-white/80 p-5 shadow-sm md:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-black text-sky-600">
            {t.round} {roundNumber}
          </p>
          <h4 className="mt-1 text-xl font-black text-slate-950">{topic}</h4>
        </div>
        <span className="rounded-full bg-slate-900 px-4 py-2 text-xs font-black uppercase tracking-wider text-white">
          {verdictLabel(summary.decision, reportLanguage)}
        </span>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <TextBlock
          title={reportLanguage === "en" ? "Round objective" : "Objectif du tour"}
          value={round.objective || round.moderator?.focus}
          language={reportLanguage}
        />
        <TextBlock
          title={reportLanguage === "en" ? "Main committee question" : "Question principale du comité"}
          value={round.main_question || round.moderator?.key_question}
          language={reportLanguage}
        />
      </div>

      {positions.length > 0 && (
        <details className="mt-5 rounded-3xl border border-slate-200 bg-slate-50/70 p-4" open>
          <summary className="cursor-pointer font-black text-slate-900">
            {reportLanguage === "en" ? "Independent expert positions" : "Positions indépendantes des experts"}
          </summary>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {positions.map((position, positionIndex) => (
              <PositionCard key={`${position.member || "member"}-${positionIndex}`} position={position} language={reportLanguage} />
            ))}
          </div>
        </details>
      )}

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <div className="rounded-3xl border border-emerald-200 bg-emerald-50/80 p-4">
          <p className="font-black text-emerald-900">{t.defender}</p>
          <div className="mt-4 space-y-3">
            <TextBlock title={t.mainArgument} value={round.defender?.main_argument} language={reportLanguage} />
            <ListBlock title={t.supportingPoints} items={round.defender?.supporting_points} language={reportLanguage} />
            <ListBlock title={reportLanguage === "en" ? "Hypotheses" : "Hypothèses"} items={round.defender?.assumptions} language={reportLanguage} />
          </div>
        </div>
        <div className="rounded-3xl border border-rose-200 bg-rose-50/80 p-4">
          <p className="font-black text-rose-900">{t.critic}</p>
          <div className="mt-4 space-y-3">
            <TextBlock title={t.mainObjection} value={round.critic?.main_objection} language={reportLanguage} />
            <ListBlock title={t.criticalRisks} items={round.critic?.critical_risks} language={reportLanguage} />
            <ListBlock title={t.missingEvidence} items={round.critic?.missing_evidence} language={reportLanguage} />
          </div>
        </div>
      </div>

      <details className="mt-5 rounded-3xl border border-sky-200 bg-white p-4" open>
        <summary className="cursor-pointer font-black text-sky-900">
          {reportLanguage === "en"
            ? `Committee cross-examination — ${questions.length} questions and answers`
            : `Contre-interrogatoire du comité — ${questions.length} questions et réponses`}
        </summary>
        <div className="mt-4 space-y-4">
          {questions.length > 0 ? (
            questions.map((question, questionIndex) => (
              <QuestionCard
                key={question.question_id || `${roundNumber}-${questionIndex}`}
                item={question}
                index={questionIndex}
                language={reportLanguage}
              />
            ))
          ) : (
            <p className="text-sm font-semibold text-slate-500">
              {reportLanguage === "en"
                ? "No structured question was recorded for this round."
                : "Aucune question structurée n’a été enregistrée pour ce tour."}
            </p>
          )}
        </div>
      </details>

      <div className="mt-5 grid gap-4 lg:grid-cols-3">
        <ListBlock
          title={reportLanguage === "en" ? "Points of agreement" : "Points d’accord"}
          items={round.agreements}
          language={reportLanguage}
        />
        <ListBlock
          title={reportLanguage === "en" ? "Points of disagreement" : "Points de désaccord"}
          items={round.disagreements}
          language={reportLanguage}
        />
        <ListBlock
          title={reportLanguage === "en" ? "Unresolved questions" : "Questions non résolues"}
          items={round.unresolved_questions}
          language={reportLanguage}
        />
      </div>

      {audit.length > 0 && (
        <details className="mt-5 rounded-3xl border border-violet-200 bg-violet-50/60 p-4">
          <summary className="cursor-pointer font-black text-violet-900">
            {reportLanguage === "en" ? "Evidence audit" : "Audit des preuves"}
          </summary>
          <div className="mt-4 space-y-3">
            {audit.map((item, auditIndex) => (
              <div key={`${item.claim || "claim"}-${auditIndex}`} className="rounded-2xl border border-violet-100 bg-white p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="rounded-full bg-violet-100 px-3 py-1 text-[11px] font-black uppercase text-violet-800">
                    {evidenceStatusLabel(item.status, reportLanguage)}
                  </span>
                  <span className="text-xs font-bold text-slate-500">
                    {reportLanguage === "en" ? "Confidence" : "Confiance"}: {confidenceLabel(item.confidence, reportLanguage)}
                  </span>
                </div>
                <p className="mt-2 text-sm font-semibold leading-6 text-slate-700">
                  {cleanText(item.claim || "", reportLanguage)}
                </p>
              </div>
            ))}
          </div>
        </details>
      )}

      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <TextBlock
          title={reportLanguage === "en" ? "Round synthesis" : "Synthèse du tour"}
          value={summary.synthesis}
          language={reportLanguage}
        />
        <TextBlock
          title={reportLanguage === "en" ? "Next action" : "Action suivante"}
          value={summary.next_action}
          language={reportLanguage}
        />
        <ListBlock
          title={reportLanguage === "en" ? "GO conditions" : "Conditions GO"}
          items={summary.go_conditions}
          language={reportLanguage}
        />
        <ListBlock
          title={reportLanguage === "en" ? "NO-GO conditions" : "Conditions NO-GO"}
          items={summary.no_go_conditions}
          language={reportLanguage}
        />
      </div>
    </section>
  );
}
