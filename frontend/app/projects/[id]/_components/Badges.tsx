"use client";

import { useForgeLanguage } from "@/lib/language-context";
import {
  riskLevelLabel,
  riskLevelLabelEn,
  statusLabel,
  statusLabelEn,
  verdictLabel,
} from "../_lib/formatters";
import type { AnalysisStatus } from "../_types/project-detail.types";
import { cleanText } from "../_lib/text-cleaning";

export function Badge({ label }: { label: string }) {
  return (
    <span className="forge-badge">
      {cleanText(label)}
    </span>
  );
}

export function AnalysisStatusBadge({
  status,
}: {
  status?: AnalysisStatus | null;
}) {
  const { lang } = useForgeLanguage();
  const currentStatus = status || "not_started";

  return (
    <span
      className={`rounded-full border px-3 py-1 text-xs font-black ${statusBadgeClass(
        currentStatus
      )}`}
    >
      {lang === "en" ? statusLabelEn(currentStatus) : statusLabel(currentStatus)}
    </span>
  );
}

export function VerdictBadge({ verdict }: { verdict?: string | null }) {
  return (
    <span
      className={`rounded-full border px-3 py-1 text-xs font-black ${verdictBadgeClass(
        verdict || ""
      )}`}
    >
      {verdictLabel(verdict || "")}
    </span>
  );
}

export function RiskBadge({ risk }: { risk?: string | null }) {
  const { lang } = useForgeLanguage();

  return (
    <span
      className={`rounded-full border px-3 py-1 text-xs font-black ${riskBadgeClass(
        risk || ""
      )}`}
    >
      {lang === "en" ? riskLevelLabelEn(risk || "") : riskLevelLabel(risk || "")}
    </span>
  );
}

export function statusBadgeClass(status?: AnalysisStatus | null): string {
  switch (status) {
    case "completed":
      return "border-emerald-200 bg-emerald-50 text-emerald-700";
    case "running":
    case "pending":
      return "border-sky-200 bg-sky-50 text-sky-700";
    case "failed":
      return "border-red-200 bg-red-50 text-red-700";
    default:
      return "border-slate-200 bg-white/70 text-slate-500";
  }
}

export function verdictBadgeClass(value?: string): string {
  switch (value) {
    case "POURSUIVRE":
      return "border-emerald-200 bg-emerald-50 text-emerald-700";
    case "PIVOTER":
      return "border-yellow-200 bg-yellow-50 text-yellow-700";
    case "ABANDONNER":
      return "border-red-200 bg-red-50 text-red-700";
    default:
      return "border-slate-200 bg-white/70 text-slate-500";
  }
}

export function riskBadgeClass(value?: string): string {
  switch (value) {
    case "low":
      return "border-emerald-200 bg-emerald-50 text-emerald-700";
    case "medium":
      return "border-yellow-200 bg-yellow-50 text-yellow-700";
    case "high":
      return "border-red-200 bg-red-50 text-red-700";
    default:
      return "border-slate-200 bg-white/70 text-slate-500";
  }
}