"use client";

import { useForgeLanguage, type ForgeLang } from "@/lib/language-context";

import type {
  DebateCommitteeMember,
  DebateCommitteeVote,
  DebateRoomData,
} from "../_types/project-detail.types";

import { reportCopy } from "../_lib/report-copy";
import { cleanText } from "../_lib/text-cleaning";

import { EmptyState } from "../_components/UIBlocks";
import DebateRoundCard from "./debate/DebateRoundCard";

function resolveLanguage(
  language: ForgeLang | undefined,
  fallback: ForgeLang,
  debateRoom?: DebateRoomData | null
): ForgeLang {
  if (language === "en" || language === "fr") return language;
  if (debateRoom?.output_language === "en") return "en";
  if (debateRoom?.output_language === "fr") return "fr";
  return fallback;
}

function formatScore(value?: number | null, language: ForgeLang = "fr"): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return language === "en" ? "Qualitative" : "Qualitatif";
  }
  return `${value.toFixed(1).replace(".0", "")}/10`;
}

function verdictText(value?: string | null, language: ForgeLang = "fr"): string {
  const normalized = String(value || "").toLowerCase();
  if (normalized.includes("insufficient")) {
    return language === "en" ? "Insufficient evidence" : "Preuves insuffisantes";
  }
  if (normalized.includes("conditional")) {
    return language === "en" ? "Continue with conditions" : "Poursuivre sous conditions";
  }
  if (normalized.includes("pivot")) return language === "en" ? "Pivot" : "Pivoter";
  if (normalized.includes("no_go") || normalized.includes("stop") || normalized.includes("abandon")) {
    return language === "en" ? "No-Go" : "NO-GO";
  }
  if (normalized === "go" || normalized.startsWith("go_")) return "GO";
  return cleanText(value || (language === "en" ? "Continue with conditions" : "Poursuivre sous conditions"), language);
}

function riskText(value?: string | null, language: ForgeLang = "fr"): string {
  const normalized = String(value || "").toLowerCase();
  if (normalized.includes("high") || normalized.includes("elev") || normalized.includes("élev")) {
    return language === "en" ? "High" : "Élevé";
  }
  if (normalized.includes("medium") || normalized.includes("moy")) {
    return language === "en" ? "Medium" : "Moyen";
  }
  if (normalized.includes("low") || normalized.includes("faib")) {
    return language === "en" ? "Low" : "Faible";
  }
  return language === "en" ? "Medium" : "Moyen";
}

function uniqueItems(items: Array<string | null | undefined>, language: ForgeLang): string[] {
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

function memberLabel(value: string | undefined, language: ForgeLang): string {
  const role = String(value || "").toLowerCase();
  const labels: Record<string, [string, string]> = {
    committee_chair: ["Committee Chair", "Président du comité"],
    customer_problem_analyst: ["Customer & Problem Analyst", "Analyste client et problème"],
    market_competition_analyst: ["Market & Competition Analyst", "Analyste marché et concurrence"],
    product_technology_architect: ["Product & Technology Architect", "Architecte produit et technologie"],
    business_financial_analyst: ["Business & Financial Analyst", "Analyste business et financier"],
    risk_execution_officer: ["Risk & Execution Officer", "Responsable risque et exécution"],
    evidence_auditor: ["Evidence Auditor", "Auditeur des preuves"],
    red_team_challenger: ["Red Team Challenger", "Challenger Red Team"],
  };
  const label = labels[role];
  if (label) return language === "en" ? label[0] : label[1];
  return cleanText(value || (language === "en" ? "Committee member" : "Membre du comité"), language);
}

function MiniMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">{label}</p>
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
      <p className="text-xs font-black uppercase tracking-[0.2em] text-slate-400">{title}</p>
      <p className="mt-3 whitespace-pre-wrap text-sm font-semibold leading-7 text-slate-700">{cleaned}</p>
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
  const values = uniqueItems(items || [], language);
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-black uppercase tracking-[0.2em] text-slate-400">{title}</p>
      {values.length ? (
        <ul className="mt-3 space-y-2">
          {values.map((item, index) => (
            <li key={`${title}-${index}`} className="rounded-2xl bg-slate-50 px-4 py-3 text-sm font-semibold leading-6 text-slate-700">
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm font-semibold text-slate-400">
          {emptyText || (language === "en" ? "No item established." : "Aucun élément établi.")}
        </p>
      )}
    </div>
  );
}

function CommitteeMemberCard({ member, language }: { member: DebateCommitteeMember; language: ForgeLang }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-black text-slate-900">{cleanText(member.role || memberLabel(member.id, language), language)}</p>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-[10px] font-black uppercase tracking-wide text-slate-600">
          {member.voting_member
            ? language === "en" ? "Voting member" : "Membre votant"
            : language === "en" ? "Advisory role" : "Rôle consultatif"}
        </span>
      </div>
      <p className="mt-2 text-sm font-semibold leading-6 text-slate-600">{cleanText(member.mandate || "", language)}</p>
    </div>
  );
}

function VoteCard({ vote, language }: { vote: DebateCommitteeVote; language: ForgeLang }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-black text-slate-900">{memberLabel(vote.member, language)}</p>
        <span className="rounded-full bg-slate-900 px-3 py-1 text-[11px] font-black uppercase text-white">
          {verdictText(vote.vote, language)}
        </span>
      </div>
      <p className="mt-2 text-sm font-semibold leading-6 text-slate-700">{cleanText(vote.reason || "", language)}</p>
      {typeof vote.confidence === "number" && (
        <p className="mt-2 text-xs font-bold text-slate-500">
          {language === "en" ? "Vote confidence" : "Confiance du vote"}: {Math.round(vote.confidence * 100)}%
        </p>
      )}
      {vote.veto && (
        <p className="mt-3 rounded-xl bg-rose-100 px-3 py-2 text-xs font-black uppercase text-rose-800">
          {language === "en" ? "Temporary veto" : "Veto temporaire"}
        </p>
      )}
    </div>
  );
}

function collectPotentialOpportunities(debateRoom: DebateRoomData, language: ForgeLang): string[] {
  return uniqueItems(
    (debateRoom.rounds || []).flatMap((round) => [
      ...(round.round_summary?.potential_opportunities || []),
      ...(round.defender?.opportunities || []),
    ]),
    language
  ).slice(0, 8);
}

export default function DebateRoomSection({
  debateRoom,
  language,
}: {
  debateRoom?: DebateRoomData | null;
  language?: ForgeLang;
}) {
  const { lang } = useForgeLanguage();
  const reportLanguage = resolveLanguage(language, lang, debateRoom);
  const t = reportCopy[reportLanguage];

  if (!debateRoom) {
    return (
      <EmptyState
        text={reportLanguage === "en" ? "Debate Room Pro is unavailable." : "Debate Room Pro n’est pas disponible."}
      />
    );
  }

  const rounds = debateRoom.rounds || [];
  const judge = debateRoom.judge;
  const committee = debateRoom.committee || [];
  const votes = judge?.committee_votes || [];
  const meeting = debateRoom.meeting_preparation;
  const verdict = judge?.verdict_code || judge?.verdict;
  const validatedOpportunities = judge?.validated_opportunities || [];
  const potentialOpportunities = judge?.potential_opportunities || collectPotentialOpportunities(debateRoom, reportLanguage);

  return (
    <div className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
        <MiniMetric label={t.debateRounds} value={String(rounds.length)} />
        <MiniMetric label={t.verdict} value={verdictText(verdict, reportLanguage)} />
        <MiniMetric label={reportLanguage === "en" ? "Strategic potential" : "Potentiel stratégique"} value={formatScore(judge?.potential_score, reportLanguage)} />
        <MiniMetric label={reportLanguage === "en" ? "Evidence confidence" : "Confiance des preuves"} value={formatScore(judge?.evidence_confidence_score ?? judge?.confidence_score, reportLanguage)} />
        <MiniMetric label={reportLanguage === "en" ? "Execution readiness" : "Préparation à l’exécution"} value={formatScore(judge?.execution_readiness_score, reportLanguage)} />
        <MiniMetric label={reportLanguage === "en" ? "Investment attractiveness" : "Attractivité d’investissement"} value={formatScore(judge?.investment_attractiveness_score, reportLanguage)} />
      </div>

      <div className="rounded-[2rem] border border-slate-200 bg-slate-950 p-6 text-white shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.2em] text-sky-300">
              {reportLanguage === "en" ? "Investment Committee Memo" : "Mémo du comité d’investissement"}
            </p>
            <h3 className="mt-2 text-2xl font-black">{verdictText(verdict, reportLanguage)}</h3>
          </div>
          <span className="rounded-full bg-white/10 px-4 py-2 text-xs font-black uppercase tracking-wide">
            {reportLanguage === "en" ? "Risk" : "Risque"}: {riskText(judge?.risk_level, reportLanguage)}
          </span>
        </div>
        <p className="mt-4 max-w-5xl text-sm font-semibold leading-7 text-slate-200">
          {cleanText(
            judge?.debate_synthesis ||
              (reportLanguage === "en"
                ? "The project is testable, but customer urgency, local demand, repeated use, payment and unit economics require stronger evidence."
                : "Le projet est testable, mais l’urgence client, la demande locale, l’usage répété, le paiement et l’économie unitaire exigent des preuves plus solides."),
            reportLanguage
          )}
        </p>
      </div>

      {committee.length > 0 && (
        <details className="rounded-[2rem] border border-slate-200 bg-slate-50/80 p-5" open>
          <summary className="cursor-pointer text-lg font-black text-slate-950">
            {reportLanguage === "en" ? `Strategic committee — ${committee.length} roles` : `Comité stratégique — ${committee.length} rôles`}
          </summary>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {committee.map((member, index) => (
              <CommitteeMemberCard key={member.id || `${member.role}-${index}`} member={member} language={reportLanguage} />
            ))}
          </div>
        </details>
      )}

      {votes.length > 0 && (
        <details className="rounded-[2rem] border border-indigo-200 bg-indigo-50/60 p-5" open>
          <summary className="cursor-pointer text-lg font-black text-indigo-950">
            {reportLanguage === "en" ? `Individual committee votes — ${votes.length}` : `Votes individuels du comité — ${votes.length}`}
          </summary>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {votes.map((vote, index) => (
              <VoteCard key={`${vote.member || "member"}-${index}`} vote={vote} language={reportLanguage} />
            ))}
          </div>
        </details>
      )}

      <div className="grid gap-5 md:grid-cols-2">
        <TextBlock title={t.finalRecommendation} value={judge?.final_recommendation} language={reportLanguage} />
        <TextBlock title={t.improvedIdea} value={judge?.improved_idea} language={reportLanguage} />
        <ListBlock title={t.criticalRisks} items={judge?.critical_risks} language={reportLanguage} />
        <ListBlock
          title={t.validatedOpportunities}
          items={validatedOpportunities}
          language={reportLanguage}
          emptyText={reportLanguage === "en" ? "No opportunity is validated without compatible evidence." : "Aucune opportunité n’est validée sans preuve compatible."}
        />
        <ListBlock title={t.potentialOpportunities} items={potentialOpportunities} language={reportLanguage} />
        <ListBlock title={t.missingEvidence} items={judge?.missing_evidence} language={reportLanguage} />
        <ListBlock title={reportLanguage === "en" ? "Committee GO conditions" : "Conditions GO du comité"} items={judge?.go_conditions || judge?.go_no_go_conditions} language={reportLanguage} />
        <ListBlock title={reportLanguage === "en" ? "Committee NO-GO conditions" : "Conditions NO-GO du comité"} items={judge?.no_go_conditions} language={reportLanguage} />
      </div>

      <div className="space-y-5">
        {rounds.length ? (
          rounds.map((round, index) => (
            <DebateRoundCard
              key={`${round.round || index}-${round.topic || "round"}`}
              round={round}
              index={index}
              language={reportLanguage}
            />
          ))
        ) : (
          <EmptyState text={reportLanguage === "en" ? "No debate round was recorded." : "Aucun tour de débat n’a été enregistré."} />
        )}
      </div>

      {meeting && (
        <section className="rounded-[2rem] border border-amber-200 bg-amber-50/80 p-6 shadow-sm">
          <p className="text-xs font-black uppercase tracking-[0.2em] text-amber-700">
            {reportLanguage === "en" ? "Real meeting preparation" : "Préparation à une réunion réelle"}
          </p>
          <h3 className="mt-2 text-2xl font-black text-amber-950">
            {reportLanguage === "en" ? "Questions you must be ready to answer" : "Questions auxquelles vous devez être prêt à répondre"}
          </h3>
          <div className="mt-5 grid gap-5 lg:grid-cols-2">
            <ListBlock title={reportLanguage === "en" ? "Likely questions" : "Questions probables"} items={meeting.top_questions} language={reportLanguage} />
            <ListBlock title={reportLanguage === "en" ? "Recommended answers" : "Réponses recommandées"} items={meeting.recommended_answers} language={reportLanguage} />
            <ListBlock title={reportLanguage === "en" ? "Proofs to prepare" : "Preuves à préparer"} items={meeting.proofs_to_prepare} language={reportLanguage} />
            <ListBlock title={reportLanguage === "en" ? "Answers to avoid" : "Réponses à éviter"} items={meeting.answers_to_avoid} language={reportLanguage} />
            <ListBlock title={reportLanguage === "en" ? "Unresolved questions" : "Questions non résolues"} items={meeting.unresolved_questions} language={reportLanguage} />
            <ListBlock
              title={
                reportLanguage === "en"
                  ? "Unresolved points"
                  : "Points non r?solus"
              }
              items={meeting.unresolved_points}
              language={reportLanguage}
            />
            <ListBlock
              title={
                reportLanguage === "en"
                  ? "Follow-up questions"
                  : "Questions de relance"
              }
              items={meeting.follow_up_questions}
              language={reportLanguage}
            />
            <ListBlock title={t.nextActions} items={judge?.next_actions || judge?.action_plan} language={reportLanguage} />
          </div>
        </section>
      )}
    </div>
  );
}
