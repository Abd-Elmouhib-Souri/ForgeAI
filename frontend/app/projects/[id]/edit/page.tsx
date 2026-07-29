"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import ProtectedPage from "@/components/auth/ProtectedPage";
import api from "@/lib/api";
import { getApiErrorMessage } from "@/lib/api-error";
import { useForgeLanguage, type ForgeLang } from "@/lib/language-context";
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

interface Project {
  id: number;
  title: string;
  description: string;
  industry?: string | null;
  market_region?: string | null;
  output_language?: ForgeLang | null;
  status: string;
  startup_score?: number | null;
}

const content = {
  fr: {
    eyebrow: "Modification",
    title: "Modifier le projet",
    subtitle:
      "Mettez à jour les informations principales. Après une modification importante, relancez l’analyse IA pour obtenir un rapport cohérent.",
    loading: "Chargement du projet...",
    notFound: "Projet introuvable.",
    titleLabel: "Titre du projet",
    industryLabel: "Secteur",
    industryPlaceholder: "ex: EdTech, HealthTech, FinTech, SaaS...",
    regionLabel: "Pays/Région cible",
    regionHelp:
      "Ce choix sera utilisé par le RAG web local lors de la prochaine analyse IA.",
    languageLabel: "Langue du rapport IA",
    languageHelp:
      "Le bouton FR / EN global sera envoyé au backend comme langue de sortie.",
    currentLanguage: "Langue actuelle",
    descriptionLabel: "Description",
    save: "Enregistrer",
    saving: "Enregistrement...",
    error: "Erreur lors de la modification.",
    sideTitle: "Conseil ForgeAI",
    sideText:
      "Si vous changez le secteur, la cible ou la région, relancez l’analyse pour éviter un rapport basé sur l’ancien contexte.",
    back: "Retour au projet",
  },
  en: {
    eyebrow: "Edit",
    title: "Edit project",
    subtitle:
      "Update the main information. After an important change, relaunch the AI analysis to get a consistent report.",
    loading: "Loading project...",
    notFound: "Project not found.",
    titleLabel: "Project title",
    industryLabel: "Sector",
    industryPlaceholder: "e.g. EdTech, HealthTech, FinTech, SaaS...",
    regionLabel: "Target country/region",
    regionHelp:
      "This choice will be used by the local web RAG during the next AI analysis.",
    languageLabel: "AI report language",
    languageHelp:
      "The global FR / EN switch will be sent to the backend as the output language.",
    currentLanguage: "Current language",
    descriptionLabel: "Description",
    save: "Save",
    saving: "Saving...",
    error: "Error while updating the project.",
    sideTitle: "ForgeAI advice",
    sideText:
      "If you change the sector, target users or region, relaunch the analysis to avoid a report based on the old context.",
    back: "Back to project",
  },
};

function EditProjectContent() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const { lang, setLang } = useForgeLanguage();
  const t = content[lang];

  const [title, setTitle] = useState("");
  const [industry, setIndustry] = useState("");
  const [marketRegion, setMarketRegion] = useState("Tunisie");
  const [description, setDescription] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchProject = async () => {
      try {
        const res = await api.get<Project>(`/projects/${id}`);

        setTitle(res.data.title);
        setIndustry(res.data.industry || "");
        setMarketRegion(res.data.market_region || "Tunisie");
        setDescription(res.data.description);

        if (
          res.data.output_language === "fr" ||
          res.data.output_language === "en"
        ) {
          setLang(res.data.output_language);
        }
      } catch (err: unknown) {
        setError(getApiErrorMessage(err, t.notFound));
      } finally {
        setIsLoading(false);
      }
    };

    if (id) {
      fetchProject();
    }
  }, [id, setLang, t.notFound]);

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();

    setError("");
    setIsSubmitting(true);

    try {
      await api.patch(`/projects/${id}`, {
        title,
        industry: industry || null,
        market_region: marketRegion,
        description,
        output_language: lang,
      });

      router.replace(`/projects/${id}`);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, t.error));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="forge-page min-h-screen">
      <ForgeAppNavbar active="projects" />

      <section className="forge-section-sm">
        <div className="forge-panel p-8">
          <span className="forge-eyebrow">{"\u270F\uFE0F"} {t.eyebrow}</span>
          <h1 className="forge-title mt-2">{t.title}</h1>
          <p className="forge-subtitle">{t.subtitle}</p>
        </div>

        <div className="mt-10 grid gap-8 lg:grid-cols-[1fr_0.42fr]">
          <div className="forge-form-card mx-0 w-full max-w-none">
            {isLoading && (
              <p className="animate-pulse text-sm font-bold text-slate-500">
                {t.loading}
              </p>
            )}

            {!isLoading && (
              <form onSubmit={handleUpdate} className="space-y-5">
                <div className="forge-field">
                  <label className="forge-label">{t.titleLabel}</label>
                  <input
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    required
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
                  {isSubmitting ? t.saving : t.save}
                </button>
              </form>
            )}
          </div>

          <aside className="forge-glass-card p-6">
            <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-yellow-100 text-2xl">
              💡
            </div>

            <h2 className="text-2xl font-black tracking-tight text-slate-950">
              {t.sideTitle}
            </h2>

            <p className="mt-3 text-sm font-semibold leading-6 text-slate-500">
              {t.sideText}
            </p>

            <button
              type="button"
              onClick={() => router.replace(`/projects/${id}`)}
              className="forge-btn forge-btn-secondary mt-6 w-full"
            >
              {t.back}
            </button>
          </aside>
        </div>
      </section>
    </main>
  );
}

export default function EditProjectPage() {
  return (
    <ProtectedPage>
      <EditProjectContent />
    </ProtectedPage>
  );
}





