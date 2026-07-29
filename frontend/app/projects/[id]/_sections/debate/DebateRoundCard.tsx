"use client";

import { useForgeLanguage, type ForgeLang } from "@/lib/language-context";

import type { DebateRoomRound } from "../../_types/project-detail.types";

import { reportCopy } from "../../_lib/report-copy";
import { cleanText } from "../../_lib/text-cleaning";

function resolveLanguage(
  language: ForgeLang | undefined,
  fallback: ForgeLang
): ForgeLang {
  return language === "en" || language === "fr" ? language : fallback;
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
      <p className="text-xs font-black uppercase tracking-[0.18em] text-slate-400">
        {title}
      </p>
      <p className="mt-2 whitespace-pre-wrap text-sm font-semibold leading-6 text-slate-700">
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
  const cleanedItems = (items || [])
    .map((item) => cleanText(item, language))
    .filter(Boolean);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <p className="text-xs font-black uppercase tracking-[0.18em] text-slate-400">
        {title}
      </p>

      {cleanedItems.length > 0 ? (
        <ul className="mt-2 space-y-2">
          {cleanedItems.map((item, index) => (
            <li
              key={`${title}-${index}`}
              className="rounded-xl bg-slate-50 px-3 py-2 text-sm font-semibold leading-6 text-slate-700"
            >
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm font-semibold text-slate-400">—</p>
      )}
    </div>
  );
}

function EmptyBox({ text }: { text: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm font-semibold text-slate-400">
      {text}
    </div>
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

  return (
    <div className="rounded-3xl border border-slate-200/70 bg-white/75 p-5 shadow-sm">
      <p className="text-sm font-black text-sky-600">
        {t.round} {round.round || index + 1}
      </p>

      <h4 className="mt-1 text-lg font-black text-slate-950">
        {cleanText(round.topic || round.moderator?.topic || "—", reportLanguage)}
      </h4>

      {(round.moderator?.focus || round.moderator?.key_question) && (
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <TextBlock
            title={reportLanguage === "en" ? "Round focus" : "Focus du tour"}
            value={round.moderator?.focus}
            language={reportLanguage}
          />
          <TextBlock
            title={
              reportLanguage === "en"
                ? "Key question"
                : "Question principale"
            }
            value={round.moderator?.key_question}
            language={reportLanguage}
          />
        </div>
      )}

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/80 p-4">
          <p className="font-black text-emerald-800">{t.defender}</p>

          {round.defender ? (
            <div className="mt-4 space-y-4">
              <TextBlock
                title={t.mainArgument}
                value={round.defender.main_argument}
                language={reportLanguage}
              />
              <ListBlockLocal
                title={t.supportingPoints}
                items={round.defender.supporting_points || []}
                language={reportLanguage}
              />
              <ListBlockLocal
                title={t.opportunities}
                items={round.defender.opportunities || []}
                language={reportLanguage}
              />
              <ListBlockLocal
                title={
                  reportLanguage === "en"
                    ? "Assumptions"
                    : "Hypothèses"
                }
                items={round.defender.assumptions || []}
                language={reportLanguage}
              />
            </div>
          ) : (
            <EmptyBox
              text={
                reportLanguage === "en"
                  ? "Defense unavailable."
                  : "Défense indisponible."
              }
            />
          )}
        </div>

        <div className="rounded-2xl border border-red-200 bg-red-50/80 p-4">
          <p className="font-black text-red-800">{t.critic}</p>

          {round.critic ? (
            <div className="mt-4 space-y-4">
              <TextBlock
                title={t.mainObjection}
                value={round.critic.main_objection}
                language={reportLanguage}
              />
              <ListBlockLocal
                title={t.criticalRisks}
                items={round.critic.critical_risks || []}
                language={reportLanguage}
              />
              <ListBlockLocal
                title={t.missingEvidence}
                items={round.critic.missing_evidence || []}
                language={reportLanguage}
              />
              <ListBlockLocal
                title={t.weakAssumptions}
                items={round.critic.weak_assumptions || []}
                language={reportLanguage}
              />
            </div>
          ) : (
            <EmptyBox
              text={
                reportLanguage === "en"
                  ? "Critical analysis unavailable."
                  : "Analyse critique indisponible."
              }
            />
          )}
        </div>
      </div>

      {round.round_summary && (
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <TextBlock
            title={
              reportLanguage === "en"
                ? "Round synthesis"
                : "Synthèse du tour"
            }
            value={round.round_summary.synthesis}
            language={reportLanguage}
          />
          <TextBlock
            title={reportLanguage === "en" ? "Decision" : "Décision"}
            value={round.round_summary.decision}
            language={reportLanguage}
          />
          <ListBlockLocal
            title={
              reportLanguage === "en"
                ? "Validated points"
                : "Points validés"
            }
            items={round.round_summary.validated_points || []}
            language={reportLanguage}
          />
          <ListBlockLocal
            title={reportLanguage === "en" ? "Remaining risks" : "Risques restants"}
            items={round.round_summary.remaining_risks || []}
            language={reportLanguage}
          />
        </div>
      )}
    </div>
  );
}