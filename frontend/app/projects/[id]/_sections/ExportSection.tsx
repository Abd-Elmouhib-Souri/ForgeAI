"use client";

import { useState } from "react";

import api from "@/lib/api";

type Language = "fr" | "en" | string;

// Backend contract (Sprint 6.1 hardening): no public file URL anymore,
// only an authenticated download endpoint relative to the API root.
type ExportResponse = {
  export_id: number;
  format: string;
  download_url: string;
  file_name: string;
  created_at: string;
};

type DownloadTarget = {
  url: string;
  fileName: string;
};

// Formats served by POST /projects/{id}/export/{format} (same private flow).
type ExportFormat = "pdf" | "word" | "powerpoint";

// Sprint 6.4 role templates: they select and order report sections
// (backend app/services/export/templates.py); no text is generated.
type ExportTemplate = "business" | "entrepreneur" | "student" | "consultant";

const TEMPLATE_OPTIONS: { value: ExportTemplate; fr: string; en: string; hintFr: string; hintEn: string }[] = [
  { value: "business", fr: "Rapport complet", en: "Complete report",
    hintFr: "Les 13 sections du CDC.", hintEn: "All 13 CDC sections." },
  { value: "entrepreneur", fr: "Entrepreneur", en: "Founder",
    hintFr: "Marché, business model, concurrence et plan de lancement.", hintEn: "Market, business model, competition and launch plan." },
  { value: "student", fr: "Étudiant", en: "Student",
    hintFr: "Conception : personas, backlog, sprints, architecture et UML.", hintEn: "Design: personas, backlog, sprints, architecture and UML." },
  { value: "consultant", fr: "Consultant", en: "Consultant",
    hintFr: "Diagnostic : comité, SWOT, risques et recommandations.", hintEn: "Diagnosis: committee, SWOT, risks and recommendations." },
];

const copy = {
  fr: {
    title: "Export",
    profile: "Profil du dossier",
    intro:
      "Télécharge le rapport complet du projet (13 sections du CDC) en PDF prêt à partager ou en Word modifiable, et un pitch deck PowerPoint de 12 slides.",
    exportPdf: "Exporter en PDF",
    exportWord: "Exporter en Word",
    exportDeck: "Exporter le pitch deck",
    exporting: "Génération en cours…",
    download: "Télécharger à nouveau",
    downloading: "Téléchargement…",
    ready: { pdf: "Le PDF est prêt. Le téléchargement a démarré.", word: "Le document Word est prêt. Le téléchargement a démarré.", powerpoint: "Le pitch deck est prêt. Le téléchargement a démarré." },
    error: "L'export a échoué. Réessayez dans quelques instants.",
    downloadError: "Le téléchargement a échoué. Relancez l'export.",
  },
  en: {
    title: "Export",
    profile: "Dossier profile",
    intro:
      "Download the complete project report (13 CDC sections) as a ready-to-share PDF or an editable Word document, and a 12-slide PowerPoint pitch deck.",
    exportPdf: "Export as PDF",
    exportWord: "Export as Word",
    exportDeck: "Export the pitch deck",
    exporting: "Generating…",
    download: "Download again",
    downloading: "Downloading…",
    ready: { pdf: "The PDF is ready. The download has started.", word: "The Word document is ready. The download has started.", powerpoint: "The pitch deck is ready. The download has started." },
    error: "Export failed. Please try again shortly.",
    downloadError: "Download failed. Please export again.",
  },
};

function messageFrom(error: unknown, fallback: string) {
  if (typeof error === "object" && error && "response" in error) {
    const detail = (error as { response?: { data?: { detail?: unknown } } })
      .response?.data?.detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

// Saves a Blob under the given name without navigating away.
function saveBlob(blob: Blob, fileName: string) {
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  // Release the in-memory copy once the browser has taken the file.
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

export default function ExportSection({
  projectId,
  language,
}: {
  projectId: string;
  language: Language;
}) {
  const t = language === "en" ? copy.en : copy.fr;

  // Format being generated (null = idle): one export at a time.
  const [working, setWorking] = useState<ExportFormat | null>(null);
  // Chosen role template, sent with every export request.
  const [template, setTemplate] = useState<ExportTemplate>("business");
  const selectedTemplate = TEMPLATE_OPTIONS.find((option) => option.value === template) ?? TEMPLATE_OPTIONS[0];
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState("");
  const [download, setDownload] = useState<(DownloadTarget & { format: ExportFormat }) | null>(null);

  // The bearer token lives in the axios instance: a plain <a href> could
  // not authenticate, so the file is fetched as a Blob through `api`.
  const fetchAndSave = async (target: DownloadTarget) => {
    setDownloading(true);
    try {
      const response = await api.get<Blob>(target.url, { responseType: "blob" });
      saveBlob(response.data, target.fileName);
    } catch (requestError) {
      // A Blob error body cannot be read as JSON detail: generic message.
      setError(messageFrom(requestError, t.downloadError));
    } finally {
      setDownloading(false);
    }
  };

  const runExport = async (format: ExportFormat) => {
    setWorking(format);
    setError("");
    try {
      const response = await api.post<ExportResponse>(
        `/projects/${projectId}/export/${format}?template=${template}`,
      );
      const target = {
        url: response.data.download_url,
        fileName: response.data.file_name,
        format,
      };
      setDownload(target);
      await fetchAndSave(target);
    } catch (requestError) {
      setError(messageFrom(requestError, t.error));
      setDownload(null);
    } finally {
      setWorking(null);
    }
  };

  return (
    <section className="scroll-mt-28 space-y-4" id="export">
      <div className="rounded-3xl border border-violet-100 bg-gradient-to-br from-violet-50 via-white to-sky-50 p-6 shadow-sm">
        <div className="flex flex-col gap-4">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.18em] text-violet-600">
              {t.title}
            </p>
            <h2 className="mt-1 text-2xl font-black text-slate-950">
              {t.title}
            </h2>
            <p className="mt-2 max-w-3xl text-sm font-medium leading-6 text-slate-600">
              {t.intro}
            </p>
            <label className="mt-4 block text-xs font-black uppercase tracking-[0.14em] text-slate-500" htmlFor="export-template">
              {t.profile}
            </label>
            <select
              id="export-template"
              value={template}
              disabled={working !== null}
              onChange={(event) => setTemplate(event.target.value as ExportTemplate)}
              className="mt-1 rounded-xl border border-violet-200 bg-white px-3 py-2 text-sm font-semibold text-slate-800"
            >
              {TEMPLATE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {language === "en" ? option.en : option.fr}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs font-medium text-slate-500">
              {language === "en" ? selectedTemplate.hintEn : selectedTemplate.hintFr}
            </p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
            <button
              type="button"
              disabled={working !== null}
              onClick={() => void runExport("pdf")}
              className="rounded-2xl bg-violet-700 px-5 py-3 text-sm font-black text-white transition hover:bg-violet-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {working === "pdf" ? t.exporting : t.exportPdf}
            </button>
            <button
              type="button"
              disabled={working !== null}
              onClick={() => void runExport("word")}
              className="rounded-2xl border border-violet-300 bg-white px-5 py-3 text-sm font-black text-violet-800 transition hover:bg-violet-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {working === "word" ? t.exporting : t.exportWord}
            </button>
            <button
              type="button"
              disabled={working !== null}
              onClick={() => void runExport("powerpoint")}
              className="rounded-2xl border border-violet-300 bg-white px-5 py-3 text-sm font-black text-violet-800 transition hover:bg-violet-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {working === "powerpoint" ? t.exporting : t.exportDeck}
            </button>
          </div>
        </div>

        {error && (
          <p className="mt-4 rounded-2xl border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">
            {error}
          </p>
        )}

        {download && !error && (
          <div className="mt-4 flex flex-col gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm font-semibold text-emerald-800">{t.ready[download.format]}</p>
            <button
              type="button"
              disabled={downloading}
              onClick={() => void fetchAndSave(download)}
              className="shrink-0 rounded-xl border border-emerald-300 bg-white px-4 py-2 text-sm font-black text-emerald-800 transition hover:bg-emerald-100 disabled:opacity-60"
            >
              {downloading ? t.downloading : t.download}
            </button>
          </div>
        )}
      </div>
    </section>
  );
}
