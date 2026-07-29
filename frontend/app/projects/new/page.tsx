"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import ProtectedPage from "@/components/auth/ProtectedPage";
import api from "@/lib/api";
import { getApiErrorMessage } from "@/lib/api-error";
import { useForgeLanguage } from "@/lib/language-context";
import ForgeAppNavbar from "@/components/forge/ForgeAppNavbar";

const MARKET_REGION_OPTIONS = [
  "Tunisie",
  "Maroc",
  "Algérie",
  "Égypte",
  "France",
  "MENA",
  "Afrique",
  "Europe",
  "Global",
];

const content = {
  fr: {
    eyebrow: "Nouvelle idée",
    title: "Créer une nouvelle idée ForgeAI",
    subtitle:
      "Décrivez votre idée avec assez de contexte. ForgeAI utilisera ces informations pour générer une analyse business, un score startup, une étude marché, un débat IA et un rapport final.",
    titleLabel: "Titre du projet",
    titlePlaceholder: "ex: SmartQueue Clinic",
    industryLabel: "Secteur",
    industryPlaceholder: "ex: EdTech, HealthTech, FinTech, SaaS...",
    regionLabel: "Pays/Région cible",
    regionHelp:
      "Exemple : Tunisie pour une analyse locale, MENA pour une analyse régionale, Global pour une analyse internationale.",
    languageLabel: "Langue du rapport IA",
    languageHelp:
      "Le bouton FR / EN global détermine la langue de sortie de l’analyse IA.",
    currentLanguage: "Langue actuelle",
    descriptionLabel: "Description",
    descriptionPlaceholder:
      "Décrivez le problème, la cible, la solution, le marché visé, le modèle économique éventuel et ce que vous voulez valider.",
    create: "Créer le projet",
    creating: "Création...",
    error: "Erreur lors de la création.",
    sideTitle: "Ce que ForgeAI va générer",
    sideText:
      "Une fois le projet créé, vous pourrez lancer une analyse IA complète.",
    items: [
      "Analyse de l’idée et résumé exécutif",
      "Étude de marché locale ou globale",
      "SWOT + Business Model Canvas",
      "Analyse concurrentielle avec sources",
      "Personas clients",
      "Startup Score et verdict stratégique",
    ],
  },
  en: {
    eyebrow: "New idea",
    title: "Create a new ForgeAI idea",
    subtitle:
      "Describe your idea with enough context. ForgeAI will use this information to generate business analysis, startup score, market study, AI debate and a final report.",
    titleLabel: "Project title",
    titlePlaceholder: "e.g. SmartQueue Clinic",
    industryLabel: "Sector",
    industryPlaceholder: "e.g. EdTech, HealthTech, FinTech, SaaS...",
    regionLabel: "Target country/region",
    regionHelp:
      "Example: Tunisia for a local analysis, MENA for a regional analysis, Global for an international analysis.",
    languageLabel: "AI report language",
    languageHelp:
      "The global FR / EN switch determines the output language of the AI analysis.",
    currentLanguage: "Current language",
    descriptionLabel: "Description",
    descriptionPlaceholder:
      "Describe the problem, target users, solution, target market, possible business model and what you want to validate.",
    create: "Create project",
    creating: "Creating...",
    error: "Error while creating the project.",
    sideTitle: "What ForgeAI will generate",
    sideText:
      "Once the project is created, you can launch a complete AI analysis.",
    items: [
      "Idea analysis and executive summary",
      "Local or global market study",
      "SWOT + Business Model Canvas",
      "Competitive analysis with sources",
      "Customer personas",
      "Startup Score and strategic verdict",
    ],
  },
};

function NewProjectContent() {
  const router = useRouter();
  const { lang } = useForgeLanguage();
  const t = content[lang];

  const [title, setTitle] = useState("");
  const [industry, setIndustry] = useState("");
  const [marketRegion, setMarketRegion] = useState("Tunisie");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();

    setError("");
    setIsSubmitting(true);

    try {
      const res = await api.post("/projects", {
        title,
        industry: industry || null,
        market_region: marketRegion,
        description,
        output_language: lang,
      });

      router.replace(`/projects/${res.data.id}`);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, t.error));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="forge-page min-h-screen">
      <ForgeAppNavbar active="new-project" />

      <section className="forge-section-sm">
        <div className="forge-panel p-8">
          <span className="forge-eyebrow">🚀 {t.eyebrow}</span>
          <h1 className="forge-title mt-2">{t.title}</h1>
          <p className="forge-subtitle">{t.subtitle}</p>
        </div>

        <div className="mt-10 grid gap-8 lg:grid-cols-[1fr_0.48fr]">
          <div className="forge-form-card mx-0 w-full max-w-none">
            <form onSubmit={handleCreate} className="space-y-5">
              <div className="forge-field">
                <label className="forge-label">{t.titleLabel}</label>
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                  placeholder={t.titlePlaceholder}
                  className="forge-input"
                />
              </div>

              <div className="forge-field">
                <label className="forge-label">{t.industryLabel}</label>
                <input
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  placeholder={t.industryPlaceholder}
                  className="forge-input"
                />
              </div>

              <div className="forge-field">
                <label className="forge-label">{t.regionLabel}</label>

                <select
                  value={marketRegion}
                  onChange={(e) => setMarketRegion(e.target.value)}
                  className="forge-select"
                >
                  {MARKET_REGION_OPTIONS.map((region) => (
                    <option key={region} value={region}>
                      {region}
                    </option>
                  ))}
                </select>

                <p className="forge-help">{t.regionHelp}</p>
              </div>

              <div className="rounded-3xl border border-violet-200 bg-violet-50/70 p-5">
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <p className="font-black text-violet-700">
                      {t.languageLabel}
                    </p>
                    <p className="mt-1 text-sm font-semibold leading-6 text-violet-600/80">
                      {t.languageHelp}
                    </p>
                  </div>

                  <span className="forge-badge forge-badge-violet">
                    {t.currentLanguage}: {lang.toUpperCase()}
                  </span>
                </div>
              </div>

              <div className="forge-field">
                <label className="forge-label">{t.descriptionLabel}</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  required
                  rows={8}
                  placeholder={t.descriptionPlaceholder}
                  className="forge-textarea"
                />
              </div>

              {error && (
                <p className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={isSubmitting}
                className="forge-btn forge-btn-primary w-full disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isSubmitting ? t.creating : t.create}
              </button>
            </form>
          </div>

          <aside className="forge-glass-card p-6">
            <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-sky-100 text-2xl">
              ✨
            </div>

            <h2 className="text-2xl font-black tracking-tight text-slate-950">
              {t.sideTitle}
            </h2>
            <p className="mt-3 text-sm font-semibold leading-6 text-slate-500">
              {t.sideText}
            </p>

            <div className="mt-6 space-y-3">
              {t.items.map((item) => (
                <div key={item} className="forge-status-row">
                  <div className="flex items-center gap-3">
                    <span className="forge-check">✓</span>
                    <span className="text-sm font-bold text-slate-600">
                      {item}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </aside>
        </div>
      </section>
    </main>
  );
}

export default function NewProjectPage() {
  return (
    <ProtectedPage>
      <NewProjectContent />
    </ProtectedPage>
  );
}





