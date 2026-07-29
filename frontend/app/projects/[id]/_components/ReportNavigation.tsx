"use client";

import { useForgeLanguage } from "@/lib/language-context";

const navItems = {
  fr: [
    { id: "executive-summary", label: "Résumé" },
    { id: "problem", label: "Problème" },
    { id: "solution", label: "Solution" },
    { id: "target-market", label: "Marché" },
    { id: "personas", label: "Personas" },
    { id: "market-opportunity", label: "Opportunité" },
    { id: "swot", label: "SWOT" },
    { id: "bmc", label: "BMC" },
    { id: "sources", label: "Sources" },
    { id: "financial", label: "Finance" },
    { id: "startup-score", label: "Score" },
    { id: "debate", label: "Débat IA" },
    { id: "verdict", label: "Verdict" },
    { id: "action-plan", label: "Plan" },
    { id: "limitations", label: "Limites" },
  ],
  en: [
    { id: "executive-summary", label: "Summary" },
    { id: "problem", label: "Problem" },
    { id: "solution", label: "Solution" },
    { id: "target-market", label: "Market" },
    { id: "personas", label: "Personas" },
    { id: "market-opportunity", label: "Opportunity" },
    { id: "swot", label: "SWOT" },
    { id: "bmc", label: "BMC" },
    { id: "sources", label: "Sources" },
    { id: "financial", label: "Finance" },
    { id: "startup-score", label: "Score" },
    { id: "debate", label: "AI Debate" },
    { id: "verdict", label: "Verdict" },
    { id: "action-plan", label: "Plan" },
    { id: "limitations", label: "Limits" },
  ],
};

export default function ReportNavigation() {
  const { lang } = useForgeLanguage();
  const items = navItems[lang];

  return (
    <div className="sticky top-3 z-20 rounded-3xl border border-white/70 bg-white/80 p-3 shadow-xl shadow-sky-100/70 backdrop-blur-xl">
      <div className="flex gap-2 overflow-x-auto pb-1">
        {items.map((item) => (
          <a
            key={item.id}
            href={`#${item.id}`}
            className="shrink-0 rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-black text-slate-600 transition hover:-translate-y-0.5 hover:border-sky-200 hover:bg-sky-50 hover:text-sky-700"
          >
            {item.label}
          </a>
        ))}
      </div>
    </div>
  );
}