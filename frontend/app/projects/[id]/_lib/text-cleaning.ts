import type { ForgeLang } from "@/lib/language-context";

type Pair = readonly [string, string];

function replacePairs(value: string, pairs: Pair[]): string {
  let output = String(value || "");

  for (const [bad, good] of pairs) {
    output = output.replaceAll(bad, good);
  }

  return output;
}

const mojibakePairs: Pair[] = [
  ["\u00E2\u20AC\u201D", "\u2014"],
  ["\u00E2\u20AC\u201C", "\u2013"],
  ["\u00E2\u20AC\u02DC", "\u2018"],
  ["\u00E2\u20AC\u2122", "\u2019"],
  ["\u00E2\u20AC\u0153", "\u201C"],
  ["\u00E2\u20AC\u009D", "\u201D"],
  ["\u00E2\u20AC\u00A6", "\u2026"],
  ["\u00E2\u0153\u201C", "\u2713"],
  ["\u00E2\u0153\u201D", "\u2713"],
  ["\u00E2\u0153\u2026", "\u2705"],
  ["\u00C3\u00A9", "\u00E9"],
  ["\u00C3\u00A8", "\u00E8"],
  ["\u00C3\u00AA", "\u00EA"],
  ["\u00C3\u00AB", "\u00EB"],
  ["\u00C3\u00A0", "\u00E0"],
  ["\u00C3\u00A1", "\u00E1"],
  ["\u00C3\u00A2", "\u00E2"],
  ["\u00C3\u00A4", "\u00E4"],
  ["\u00C3\u00AE", "\u00EE"],
  ["\u00C3\u00AF", "\u00EF"],
  ["\u00C3\u00B4", "\u00F4"],
  ["\u00C3\u00B6", "\u00F6"],
  ["\u00C3\u00B9", "\u00F9"],
  ["\u00C3\u00BB", "\u00FB"],
  ["\u00C3\u00BC", "\u00FC"],
  ["\u00C3\u00A7", "\u00E7"],
  ["\u00C3\u2030", "\u00C9"],
  ["\u00C3\u02C6", "\u00C8"],
  ["\u00C3\u0160", "\u00CA"],
  ["\u00C2\u00AB", "\u00AB"],
  ["\u00C2\u00BB", "\u00BB"],
  ["\u00C2\u00B0", "\u00B0"],
  ["\u00C2", ""],
];

const spacingPairs: Pair[] = [
  ["Saa S", "SaaS"],
  ["Saa s", "SaaS"],
  ["Postgre SQL", "PostgreSQL"],
  ["Postgre Sql", "PostgreSQL"],
  ["Ed Tech", "EdTech"],
  ["HR Tech", "HRTech"],
  ["Skill Bridge Lite", "SkillBridge Lite"],
];

const technicalPairsEn: Pair[] = [
  ["LangGraph", "analysis workflow"],
  ["ForgeCrawler", "external sources"],
  ["RAG", "available sources"],
  ["Self-Correction RAG", "claim verification"],
  ["FactChecker", "claim verification"],
  ["fact_checker", "claim verification"],
  ["LLM", "analysis engine"],
  ["DDGS", "external search engine"],
  ["Gemini", "analysis engine"],
  ["Groq", "analysis engine"],
  ["trafilatura", "web extraction"],
  ["BeautifulSoup", "web extraction"],
  ["beautifulsoup", "web extraction"],
  ["persona_builder", "Customer personas"],
  ["Persona Builder", "Customer personas"],
];

const technicalPairsFr: Pair[] = [
  ["LangGraph", "workflow d'analyse"],
  ["ForgeCrawler", "sources externes"],
  ["RAG", "sources disponibles"],
  ["Self-Correction RAG", "verification des affirmations"],
  ["FactChecker", "verification des affirmations"],
  ["fact_checker", "verification des affirmations"],
  ["LLM", "moteur d'analyse"],
  ["DDGS", "moteur de recherche externe"],
  ["Gemini", "moteur d'analyse"],
  ["Groq", "moteur d'analyse"],
  ["trafilatura", "extraction web"],
  ["BeautifulSoup", "extraction web"],
  ["beautifulsoup", "extraction web"],
  ["persona_builder", "Personas clients"],
  ["Persona Builder", "Personas clients"],
];

const publicPairsEn: Pair[] = [
  ["Analyse strategique + Debat strategique terminee partiellement", "Strategic analysis completed"],
  ["Analyse strategique + Debat strategique termine partiellement", "Strategic analysis completed"],
  ["Analyse Sprint 3 + Debate Room terminee", "Strategic analysis completed"],
  ["Analyse terminee", "Analysis completed"],
  ["Analyse complete", "Complete analysis"],
  ["Debat strategique", "Strategic debate"],
  ["Verification des affirmations", "Claim verification"],
  ["Personas clients", "Customer personas"],
  ["Source externe", "External source"],
  ["Sources externes", "External sources"],
  ["Concurrents locaux", "Local competitors"],
  ["Aucun concurrent local direct verifie", "No verified direct local competitor"],
  ["Aucun benchmark regional", "No regional benchmark"],
  ["Aucun benchmark international", "No international benchmark"],
  ["Aucune source externe disponible", "No external source available"],
  ["Moyenne", "Medium"],
  ["Moyen", "Medium"],
  ["moyenne", "medium"],
  ["moyen", "medium"],
  ["Elevee", "High"],
  ["Eleve", "High"],
  ["Faible", "Low"],
  ["A verifier", "To verify"],
  ["a verifier", "to verify"],
  ["Non confirme", "Not confirmed"],
  ["Estime", "Estimated"],
  ["Validation terrain requise", "Field validation required"],
  ["PIVOTER", "PIVOT"],
  ["POURSUIVRE", "CONTINUE"],
  ["ABANDONNER", "STOP"],
  ["Pivoter", "Pivot"],
  ["Poursuivre", "Continue"],
  ["Abandonner", "Stop"],
  ["completed partially", "completed"],
  ["terminee partiellement", "completed"],
  ["termine partiellement", "completed"],
  ["risk level: high", "risk level: High"],
  ["risk level: medium", "risk level: Medium"],
  ["risk level: low", "risk level: Low"],
];

const publicPairsFr: Pair[] = [
  ["Analyse strategique + Debat strategique terminee partiellement", "Analyse strategique + Debat strategique terminee"],
  ["Analyse strategique + Debat strategique termine partiellement", "Analyse strategique + Debat strategique termine"],
  ["Analyse Analyse strategique", "Analyse strategique"],
  ["Analyse strategique Analyse strategique", "Analyse strategique"],
  ["Analyse Analyse", "Analyse"],
  ["terminee partiellement", "terminee"],
  ["termine partiellement", "termine"],
  ["completed partially", "terminee"],
  ["risk level: high", "niveau de risque : Eleve"],
  ["risk level: medium", "niveau de risque : Moyen"],
  ["risk level: low", "niveau de risque : Faible"],
];

const identifierPairsFr: Pair[] = [
  ["all_committee_members", "Tous les membres du comité"],
  ["project_defender", "Défenseur du projet"],
  ["field_validation_required", "Validation terrain requise"],
  ["not_confirmed", "Non confirmé"],
  ["solution_hypothesis", "Hypothèse de solution"],
  ["local_competition", "Concurrence locale"],
  ["market_demand", "Demande du marché"],
  ["market_size", "Taille du marché"],
  ["market_context", "Contexte de marché"],
];

const identifierPairsEn: Pair[] = [
  ["all_committee_members", "All committee members"],
  ["project_defender", "Project defender"],
  ["field_validation_required", "Field validation required"],
  ["not_confirmed", "Not confirmed"],
  ["solution_hypothesis", "Solution hypothesis"],
  ["local_competition", "Local competition"],
  ["market_demand", "Market demand"],
  ["market_size", "Market size"],
  ["market_context", "Market context"],
];

const typoPairs: Pair[] = [
  ["Armes robotiques", "Bras robotiques"],
  ["armes robotiques", "bras robotiques"],
  ["Crescement", "Croissance"],
  ["crescement", "croissance"],
  ["anomalies de humidite", "anomalies d'humidite"],
  ["anomalies de l'humidite", "anomalies d'humidite"],
  ["de infrastructure", "d'infrastructure"],
  ["couts de infrastructure", "couts d'infrastructure"],
  ["Le potentiel de revenus est bonne", "Le potentiel de revenus est bon"],
  ["le potentiel de revenus est bonne", "le potentiel de revenus est bon"],
];

const sourcePairs: Pair[] = [
  ["fintechare", "fintech are"],
  ["replacingmultiplefinancialservices", "replacing multiple financial services"],
  ["singleapp", "single app"],
  ["thepaymentsolution", "the payment solution"],
  ["poweringglobalrevenue", "powering global revenue"],
  ["300+markets", "300+ markets"],
  ["Startyour", "Start your"],
  ["startyour", "start your"],
  ["thegloballeader", "the global leader"],
  ["Theglobalplatform", "The global platform"],
  ["theglobalplatform", "the global platform"],
  ["Facebookleads", "Facebook leads"],
  ["InstagramandTikTokhave", "Instagram and TikTok have"],
  ["globalsuperappsdominating", "global super apps dominating"],
  ["Wirelesssensorstrack", "Wireless sensors track"],
  ["wirelesssensorstrack", "wireless sensors track"],
  ["GreenhousesProjects", "Greenhouse projects"],
  ["sensorsTrack", "sensors track"],
  ["sensorstrack", "sensors track"],
  ["sensorsto", "sensors to"],
  ["solutionsallow", "solutions allow"],
  ["wea...", "weather..."],
];

function fixMojibake(value: string): string {
  return replacePairs(value, mojibakePairs);
}

function normalizeTechnologyTokens(value: string): string {
  return String(value || "")
    .replace(/\bIo[\s\u00A0._-]*T\b/gi, "IoT")
    .replace(/\bLo[\s\u00A0._-]*Ra[\s\u00A0._-]*WAN\b/gi, "LoRaWAN")
    .replace(/\bLo[\s\u00A0._-]*RaWAN\b/gi, "LoRaWAN")
    .replace(/\b4[\s\u00A0._-]*G\b/gi, "4G")
    .replace(/\b5[\s\u00A0._-]*G\b/gi, "5G")
    .replace(/\bWi[\s\u00A0._-]*Fi\b/gi, "Wi-Fi");
}

function fixCommonSpacing(value: string): string {
  return replacePairs(String(value || ""), spacingPairs)
    .replace(/\s+([.,;:!?])/g, "$1")
    .replace(/([([{])\s+/g, "$1")
    .replace(/\s+([)\]}])/g, "$1")
    .replace(/\s{2,}/g, " ")
    .trim();
}

export function cleanText(value: string, language: ForgeLang = "fr"): string {
  let cleaned = fixCommonSpacing(fixMojibake(String(value || "")));

  cleaned = replacePairs(
    cleaned,
    language === "en" ? technicalPairsEn : technicalPairsFr
  );

  cleaned = fixMojibake(cleaned);

  cleaned = replacePairs(
    cleaned,
    language === "en" ? publicPairsEn : publicPairsFr
  );

  cleaned = replacePairs(cleaned, typoPairs);
  cleaned = replacePairs(
    cleaned,
    language === "en" ? identifierPairsEn : identifierPairsFr
  );
  cleaned = normalizeTechnologyTokens(cleaned);
  cleaned = fixCommonSpacing(fixMojibake(cleaned));

  const lowered = cleaned.toLowerCase();

  const technicalErrorMarkers = [
    "search failed",
    "operation timed out",
    "no results found",
    "traceback",
    "stacktrace",
    "fallback",
    "provider failed",
    "model failed",
    "download error",
    "certificate verify failed",
    "read timed out",
  ];

  if (technicalErrorMarkers.some((marker) => lowered.includes(marker))) {
    if (language === "en") {
      return (
        "Some external sources could not be fully accessed. " +
        "The analysis remains usable, but field validation is recommended."
      );
    }

    return (
      "Certaines sources externes n'ont pas pu etre consultees entierement. " +
      "L'analyse reste exploitable, mais une validation terrain est recommandee."
    );
  }

  return cleaned;
}

export function normalizeSourceText(value: string): string {
  let normalized = fixCommonSpacing(fixMojibake(String(value || "")))
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/([a-zA-Z])(\d)/g, "$1 $2")
    .replace(/(\d)([a-zA-Z])/g, "$1 $2")
    .replace(/\s+/g, " ")
    .trim();

  normalized = replacePairs(normalized, sourcePairs);
  normalized = normalizeTechnologyTokens(normalized);

  return fixCommonSpacing(normalized);
}

export function isBadCollapsedSourceText(value: string): boolean {
  const lowered = value.toLowerCase();

  if (
    lowered.includes("\u043E \u0441\u0435\u0440\u0432\u0438\u0441\u0435") ||
    lowered.includes("\u0430\u0432\u0442\u043E\u0440\u0430\u043C")
  ) {
    return true;
  }

  const words = value.split(/\s+/);

  return words.some((word) => {
    const clean = word.replace(/[^a-zA-Z]/g, "");
    return clean.length > 34 && clean === clean.toLowerCase();
  });
}