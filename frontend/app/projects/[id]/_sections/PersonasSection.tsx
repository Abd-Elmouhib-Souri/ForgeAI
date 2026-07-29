"use client";

import { useForgeLanguage, type ForgeLang } from "@/lib/language-context";

import type {
  PersonaBuilderData,
  PersonaItem,
} from "../_types/project-detail.types";

import { reportCopy } from "../_lib/report-copy";
import { cleanText } from "../_lib/text-cleaning";

import { EmptyState } from "../_components/UIBlocks";
import PersonaCard from "./personas/PersonaCard";

function resolveLanguage(
  language: ForgeLang | undefined,
  fallback: ForgeLang,
  personasData?: PersonaBuilderData | null
): ForgeLang {
  if (language === "en" || language === "fr") return language;
  if (personasData?.output_language === "en") return "en";
  if (personasData?.output_language === "fr") return "fr";
  return fallback;
}

function uniquePersonas(personasData: PersonaBuilderData): PersonaItem[] {
  const rawPersonas =
    personasData.personas && personasData.personas.length > 0
      ? personasData.personas
      : personasData.primary_persona
        ? [personasData.primary_persona]
        : [];

  const seen = new Set<string>();
  const result: PersonaItem[] = [];

  for (const persona of rawPersonas) {
    const key = String(
      persona.id ||
        persona.name ||
        persona.persona_name ||
        persona.role ||
        persona.segment ||
        JSON.stringify(persona)
    ).toLowerCase();

    if (seen.has(key)) continue;

    seen.add(key);
    result.push(persona);
  }

  return result;
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

function ListPanel({
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
  const cleanedItems = (items || [])
    .map((item) => cleanText(item, language))
    .filter(Boolean);

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
          {emptyText || "—"}
        </p>
      )}
    </div>
  );
}

export default function PersonasSection({
  personasData,
  language,
}: {
  personasData?: PersonaBuilderData | null;
  language?: ForgeLang;
}) {
  const { lang } = useForgeLanguage();
  const reportLanguage = resolveLanguage(language, lang, personasData);
  const t = reportCopy[reportLanguage];

  if (!personasData) {
    return <EmptyState text={t.noPersonas} />;
  }

  const personas = uniquePersonas(personasData);

  const validationMethods =
    personasData.recommended_validation_method ||
    personasData.validation_questions ||
    [];

  const risks =
    personasData.limitations && personasData.limitations.length > 0
      ? personasData.limitations
      : personasData.persona_risks && personasData.persona_risks.length > 0
        ? personasData.persona_risks
        : [
            reportLanguage === "en"
              ? "These personas are strategic hypotheses and must be validated with real users."
              : "Ces personas sont des hypothèses stratégiques et doivent être confirmés par des utilisateurs réels.",
          ];

  return (
    <div className="space-y-5">
      <TextBlock
        title={
          reportLanguage === "en"
            ? "Persona summary"
            : "Synthèse des profils ciblés"
        }
        value={personasData.persona_summary || personasData.summary}
        language={reportLanguage}
      />

      {personasData.buyer_user_difference && (
        <TextBlock
          title={
            reportLanguage === "en"
              ? "Buyer / user difference"
              : "Différence acheteur / utilisateur"
          }
          value={personasData.buyer_user_difference}
          language={reportLanguage}
        />
      )}

      {personas.length > 0 ? (
        <div className="grid gap-5 lg:grid-cols-2">
          {personas.map((persona, index) => (
            <PersonaCard
              key={`${index}-${persona.id || persona.name || persona.persona_name || "persona"}`}
              persona={persona}
              index={index}
              language={reportLanguage}
            />
          ))}
        </div>
      ) : (
        <EmptyState
          text={
            reportLanguage === "en"
              ? "No persona generated."
              : "Aucun persona généré."
          }
        />
      )}

      <div className="grid gap-5 md:grid-cols-2">
        <ListPanel
          title={t.validationQuestions}
          items={validationMethods}
          language={reportLanguage}
        />

        <ListPanel
          title={t.limitationsIdentified}
          items={risks}
          language={reportLanguage}
        />
      </div>
    </div>
  );
}