"use client";

import { useForgeLanguage, type ForgeLang } from "@/lib/language-context";

import type { DebateRoomData } from "../_types/project-detail.types";

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

  if (language === "en") {
    if (normalized.includes("conditional")) return "Continue with conditions";
    if (normalized.includes("pivot")) return "Pivot";
    if (normalized.includes("continue") || normalized.includes("poursuivre")) {
      return "Continue";
    }
    if (normalized.includes("stop") || normalized.includes("abandon")) {
      return "Stop";
    }
    return cleanText(value || "Continue with conditions", language);
  }

  if (normalized.includes("conditional")) return "Poursuivre sous conditions";
  if (normalized.includes("pivot")) return "Pivoter";
  if (normalized.includes("continue") || normalized.includes("poursuivre")) {
    return "Poursuivre";
  }
  if (normalized.includes("stop") || normalized.includes("abandon")) {
    return "Abandonner";
  }

  return cleanText(value || "Poursuivre sous conditions", language);
}

function riskText(value?: string | null, language: ForgeLang = "fr"): string {
  const normalized = String(value || "").toLowerCase();

  if (language === "en") {
    if (normalized.includes("high") || normalized.includes("elev")) return "High";
    if (normalized.includes("medium") || normalized.includes("moy")) return "Medium";
    if (normalized.includes("low") || normalized.includes("faib")) return "Low";
    return cleanText(value || "Medium", language);
  }

  if (normalized.includes("high") || normalized.includes("elev")) return "Élevé";
  if (normalized.includes("medium") || normalized.includes("moy")) return "Moyen";
  if (normalized.includes("low") || normalized.includes("faib")) return "Faible";

  return cleanText(value || "Moyen", language);
}

function uniqueItems(items: string[]): string[] {
  const seen = new Set<string>();

  return items
    .map((item) => String(item || "").trim())
    .filter(Boolean)
    .filter((item) => {
      const key = item.toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
}

function collectRoundOpportunities(debateRoom: DebateRoomData): string[] {
  const rounds = (debateRoom.rounds || []) as unknown[];

  const collected: string[] = [];

  for (const rawRound of rounds) {
    const round = rawRound as Record<string, unknown>;
    const defender = round.defender as Record<string, unknown> | undefined;
    const summary = round.round_summary as Record<string, unknown> | undefined;

    const defenderOpportunities = defender?.opportunities;
    const validatedPoints = summary?.validated_points;

    if (Array.isArray(defenderOpportunities)) {
      collected.push(...defenderOpportunities.map(String));
    }

    if (Array.isArray(validatedPoints)) {
      collected.push(...validatedPoints.map(String));
    }
  }

  return uniqueItems(collected).slice(0, 6);
}

function inferVerdict(debateRoom: DebateRoomData): string {
  const judge = debateRoom.judge;
  const goNoGo = judge?.go_no_go_conditions || [];
  const rounds = debateRoom.rounds || [];

  if (judge?.verdict) return judge.verdict;

  const hasConditionalGo =
    goNoGo.some((item) => String(item).toLowerCase().includes("go")) ||
    rounds.some((round) =>
      String(round.round_summary?.decision || "")
        .toLowerCase()
        .includes("conditional")
    );

  return hasConditionalGo ? "Continue with conditions" : "Continue";
}

function inferRisk(debateRoom: DebateRoomData): string {
  const judge = debateRoom.judge;

  if (judge?.risk_level) return judge.risk_level;
  if ((judge?.critical_risks || []).length > 0) return "Medium";

  const roundRisks = (debateRoom.rounds || []).some((round) => {
    return (
      (round.critic?.critical_risks || []).length > 0 ||
      (round.round_summary?.remaining_risks || []).length > 0
    );
  });

  return roundRisks ? "Medium" : "Low";
}

function inferRecommendation(
  debateRoom: DebateRoomData,
  language: ForgeLang
): string {
  const judge = debateRoom.judge;

  if (judge?.final_recommendation) return judge.final_recommendation;
  if (judge?.debate_synthesis) return judge.debate_synthesis;

  const firstAction =
    judge?.next_actions?.[0] ||
    judge?.action_plan?.[0] ||
    judge?.go_no_go_conditions?.[0];

  if (firstAction) return firstAction;

  return language === "en"
    ? "Continue only with a narrow MVP and validate repeated usage before scaling."
    : "Poursuivre uniquement avec un MVP réduit et valider l’usage répété avant de passer à l’échelle.";
}

function inferImprovedIdea(language: ForgeLang): string {
  return language === "en"
    ? "Keep the product focused on the first operational workflow, validate it with pilot users, then expand only after proof of weekly usage and willingness to pay."
    : "Garder le produit centré sur le premier workflow opérationnel, le valider avec des utilisateurs pilotes, puis élargir seulement après preuve d’usage hebdomadaire et de volonté de payer.";
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

function ListBlockLocal({
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
  const cleanedItems = uniqueItems(
    (items || []).map((item) => cleanText(item, language))
  ).filter(Boolean);

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
        <p className="mt-3 text-sm font-semibold text-slate-400">
          {emptyText || (language === "en" ? "No item identified." : "Aucun élément identifié.")}
        </p>
      )}
    </div>
  );
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
        text={
          reportLanguage === "en"
            ? "Debate Room Pro+ is unavailable."
            : "Debate Room Pro+ non disponible."
        }
      />
    );
  }

  const rounds = debateRoom.rounds || [];
  const judge = debateRoom.judge;

  const inferredVerdict = inferVerdict(debateRoom);
  const inferredRisk = inferRisk(debateRoom);
  const inferredRecommendation = inferRecommendation(debateRoom, reportLanguage);
  const inferredImprovedIdea = judge?.improved_idea || inferImprovedIdea(reportLanguage);

  const validatedOpportunities =
    (judge?.validated_opportunities || []).length > 0
      ? judge?.validated_opportunities || []
      : collectRoundOpportunities(debateRoom);

  return (
    <div className="space-y-5">
      <div className="grid gap-3 md:grid-cols-4">
        <MiniMetricLocal label={t.debateRounds} value={String(rounds.length)} />
        <MiniMetricLocal
          label={t.verdict}
          value={verdictText(inferredVerdict, reportLanguage)}
        />
        <MiniMetricLocal
          label={t.argumentScore}
          value={formatScore(
            judge?.argument_strength_score ?? judge?.confidence_score ?? null,
            reportLanguage
          )}
        />
        <MiniMetricLocal
          label={t.risk}
          value={riskText(inferredRisk, reportLanguage)}
        />
      </div>

      <TextBlock
        title={t.debateSynthesis}
        value={
          judge?.debate_synthesis ||
          (reportLanguage === "en"
            ? "The committee recommends continuing with conditions: validate the first target segment, prove repeated usage and avoid scaling before the MVP is tested."
            : "Le comité recommande de poursuivre sous conditions : valider le premier segment cible, prouver l’usage répété et éviter le passage à l’échelle avant le test MVP.")
        }
        language={reportLanguage}
      />

      <div className="grid gap-5 md:grid-cols-2">
        <TextBlock
          title={t.finalRecommendation}
          value={inferredRecommendation}
          language={reportLanguage}
        />
        <TextBlock
          title={t.improvedIdea}
          value={inferredImprovedIdea}
          language={reportLanguage}
        />
        <ListBlockLocal
          title={t.criticalRisks}
          items={judge?.critical_risks || []}
          language={reportLanguage}
        />
        <ListBlockLocal
          title={t.validatedOpportunities}
          items={validatedOpportunities}
          language={reportLanguage}
        />
        <ListBlockLocal
          title={t.goNoGo}
          items={judge?.go_no_go_conditions || []}
          language={reportLanguage}
        />
        <ListBlockLocal
          title={t.nextActions}
          items={judge?.next_actions || judge?.action_plan || []}
          language={reportLanguage}
        />
      </div>

      <div className="space-y-5">
        {rounds.length > 0 ? (
          rounds.map((round, index) => (
            <DebateRoundCard
              key={`${round.round || index}-${round.topic || "round"}`}
              round={round}
              index={index}
              language={reportLanguage}
            />
          ))
        ) : (
          <EmptyState
            text={
              reportLanguage === "en"
                ? "No debate round recorded."
                : "Aucun tour de débat enregistré."
            }
          />
        )}
      </div>
    </div>
  );
}