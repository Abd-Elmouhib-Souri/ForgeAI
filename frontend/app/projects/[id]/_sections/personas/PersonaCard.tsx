"use client";

import { useForgeLanguage, type ForgeLang } from "@/lib/language-context";

import type { PersonaItem } from "../../_types/project-detail.types";

import { reportCopy } from "../../_lib/report-copy";
import { cleanText } from "../../_lib/text-cleaning";

function resolveLanguage(
  language: ForgeLang | undefined,
  fallback: ForgeLang
): ForgeLang {
  return language === "en" || language === "fr" ? language : fallback;
}

function valueText(value: string | null | undefined, language: ForgeLang): string {
  const cleaned = cleanText(value || "", language);
  return cleaned || "—";
}

function listItems(items: string[] | undefined, language: ForgeLang): string[] {
  return (items || [])
    .map((item) => cleanText(item, language))
    .filter(Boolean);
}

function MiniMetricLocal({
  label,
  value,
  language,
}: {
  label: string;
  value?: string | null;
  language: ForgeLang;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
      <p className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">
        {label}
      </p>
      <p className="mt-1 text-sm font-black text-slate-800">
        {valueText(value, language)}
      </p>
    </div>
  );
}

function TextPanel({
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

function ListPanel({
  title,
  items,
  language,
}: {
  title: string;
  items?: string[];
  language: ForgeLang;
}) {
  const cleanedItems = listItems(items, language);

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

export default function PersonaCard({
  persona,
  index,
  language,
}: {
  persona: PersonaItem;
  index: number;
  language?: ForgeLang;
}) {
  const { lang } = useForgeLanguage();
  const reportLanguage = resolveLanguage(language, lang);
  const t = reportCopy[reportLanguage];

  const displayName =
    persona.name ||
    persona.persona_name ||
    persona.segment ||
    `${t.persona} ${index + 1}`;

  const displayRole =
    persona.role ||
    persona.profession ||
    persona.segment ||
    persona.context ||
    "—";

  const painItems =
    persona.frustrations && persona.frustrations.length > 0
      ? persona.frustrations
      : persona.main_pain
        ? [persona.main_pain]
        : [];

  const obstacleItems =
    persona.adoption_obstacles && persona.adoption_obstacles.length > 0
      ? persona.adoption_obstacles
      : persona.objections || [];

  const triggerItems = persona.adoption_trigger
    ? [persona.adoption_trigger]
    : [];

  const valueItems = persona.expected_value ? [persona.expected_value] : [];

  return (
    <div className="rounded-3xl border border-slate-200/70 bg-white/80 p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-xl hover:shadow-sky-100">
      <p className="text-xs font-black uppercase tracking-wide text-sky-600">
        {t.persona} {index + 1}
      </p>

      <h3 className="mt-2 text-xl font-black tracking-tight text-slate-950">
        {cleanText(displayName, reportLanguage)}
      </h3>

      <p className="mt-1 text-sm font-semibold text-slate-500">
        {cleanText(displayRole, reportLanguage)}
      </p>

      {persona.profile && (
        <p className="mt-4 rounded-2xl bg-slate-50 p-4 text-sm font-semibold leading-7 text-slate-700">
          {cleanText(persona.profile, reportLanguage)}
        </p>
      )}

      <div className="mt-5 grid gap-3 md:grid-cols-3">
        <MiniMetricLocal
          label={reportLanguage === "en" ? "Segment" : "Segment"}
          value={persona.segment}
          language={reportLanguage}
        />
        <MiniMetricLocal
          label={reportLanguage === "en" ? "Buying power" : "Pouvoir d’achat"}
          value={persona.buying_power || persona.budget_level}
          language={reportLanguage}
        />
        <MiniMetricLocal
          label={reportLanguage === "en" ? "Decision power" : "Pouvoir de décision"}
          value={persona.decision_power || persona.tech_level}
          language={reportLanguage}
        />
      </div>

      <div className="mt-5 grid gap-5 md:grid-cols-2">
        <ListPanel
          title={t.goals}
          items={persona.goals || valueItems}
          language={reportLanguage}
        />
        <ListPanel
          title={t.frustrations}
          items={painItems}
          language={reportLanguage}
        />
        <ListPanel
          title={
            reportLanguage === "en"
              ? "Current alternatives"
              : "Alternatives actuelles"
          }
          items={persona.current_alternatives || []}
          language={reportLanguage}
        />
        <ListPanel
          title={t.adoptionObstacles}
          items={obstacleItems}
          language={reportLanguage}
        />
        <ListPanel
          title={
            reportLanguage === "en"
              ? "Adoption triggers"
              : "Déclencheurs d’adoption"
          }
          items={triggerItems}
          language={reportLanguage}
        />
        <ListPanel
          title={
            reportLanguage === "en"
              ? "Success metrics"
              : "Indicateurs de réussite"
          }
          items={persona.success_metrics || []}
          language={reportLanguage}
        />
      </div>

      <div className="mt-5 space-y-5">
        <TextPanel
          title={t.useCase}
          value={persona.use_case || persona.context}
          language={reportLanguage}
        />
        <TextPanel
          title={t.userJourney}
          value={persona.user_journey}
          language={reportLanguage}
        />
        <TextPanel
          title={t.messageToConvince}
          value={persona.message_to_convince || persona.expected_value}
          language={reportLanguage}
        />

        <ListPanel
          title={
            reportLanguage === "en"
              ? "Interview questions"
              : "Questions d’entretien"
          }
          items={persona.interview_questions || []}
          language={reportLanguage}
        />
      </div>
    </div>
  );
}