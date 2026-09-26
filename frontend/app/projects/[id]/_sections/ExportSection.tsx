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

const copy = {
  fr: {
    title: "Export",
    intro:
      "Télécharge le rapport complet du projet (13 sections du CDC) en document PDF prêt à partager.",
    exportPdf: "Exporter en PDF",
    exporting: "Génération du PDF en cours…",
    download: "Télécharger le PDF",
    downloading: "Téléchargement…",
    ready: "Le PDF est prêt. Le téléchargement a démarré.",
    error: "L'export a échoué. Réessayez dans quelques instants.",
    downloadError: "Le téléchargement a échoué. Relancez l'export.",
  },
  en: {
    title: "Export",
    intro:
      "Download the complete project report (13 CDC sections) as a ready-to-share PDF document.",
    exportPdf: "Export as PDF",
    exporting: "Generating PDF…",
    download: "Download the PDF",
    downloading: "Downloading…",
    ready: "The PDF is ready. The download has started.",
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

  const [working, setWorking] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState("");
  const [download, setDownload] = useState<DownloadTarget | null>(null);

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

  const runExport = async () => {
    setWorking(true);
    setError("");
    try {
      const response = await api.post<ExportResponse>(
        `/projects/${projectId}/export/pdf`,
      );
      const target = {
        url: response.data.download_url,
        fileName: response.data.file_name,
      };
      setDownload(target);
      await fetchAndSave(target);
    } catch (requestError) {
      setError(messageFrom(requestError, t.error));
      setDownload(null);
    } finally {
      setWorking(false);
    }
  };

  return (
    <section className="scroll-mt-28 space-y-4" id="export">
      <div className="rounded-3xl border border-violet-100 bg-gradient-to-br from-violet-50 via-white to-sky-50 p-6 shadow-sm">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
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
          </div>
          <button
            type="button"
            disabled={working}
            onClick={() => void runExport()}
            className="shrink-0 rounded-2xl bg-violet-700 px-5 py-3 text-sm font-black text-white transition hover:bg-violet-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {working ? t.exporting : t.exportPdf}
          </button>
        </div>

        {error && (
          <p className="mt-4 rounded-2xl border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">
            {error}
          </p>
        )}

        {download && !error && (
          <div className="mt-4 flex flex-col gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm font-semibold text-emerald-800">{t.ready}</p>
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
