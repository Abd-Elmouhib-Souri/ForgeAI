"use client";

import { useState } from "react";

import api from "@/lib/api";

type Language = "fr" | "en" | string;

type ExportResponse = {
  export_id: number;
  format: string;
  file_path: string;
  created_at: string;
};

const copy = {
  fr: {
    title: "Export",
    intro:
      "Telecharge le rapport complet du projet (13 sections du CDC) en document PDF pret a partager.",
    exportPdf: "Exporter en PDF",
    exporting: "Generation du PDF en cours…",
    download: "Telecharger le PDF",
    error: "L'export a echoue. Reessayez dans quelques instants.",
  },
  en: {
    title: "Export",
    intro:
      "Download the complete project report (13 CDC sections) as a ready-to-share PDF document.",
    exportPdf: "Export as PDF",
    exporting: "Generating PDF…",
    download: "Download the PDF",
    error: "Export failed. Please try again shortly.",
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

export default function ExportSection({
  projectId,
  language,
}: {
  projectId: string;
  language: Language;
}) {
  const t = language === "en" ? copy.en : copy.fr;

  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);

  const runExport = async () => {
    setWorking(true);
    setError("");
    try {
      const response = await api.post<ExportResponse>(
        `/projects/${projectId}/export/pdf`,
      );
      const base = process.env.NEXT_PUBLIC_API_URL ?? "";
      setDownloadUrl(`${base}${response.data.file_path}`);
    } catch (requestError) {
      setError(messageFrom(requestError, t.error));
      setDownloadUrl(null);
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

        {downloadUrl && (
          <div className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
            <a
              href={downloadUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-black text-emerald-800 underline"
            >
              {t.download}
            </a>
          </div>
        )}
      </div>
    </section>
  );
}
