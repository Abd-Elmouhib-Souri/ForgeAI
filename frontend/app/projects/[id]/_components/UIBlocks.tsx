import type { ReactNode } from "react";
import { cleanText } from "../_lib/text-cleaning";
import { formatScore } from "../_lib/formatters";

export function Panel({
  title,
  subtitle,
  children,
  className = "",
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`forge-card p-6 ${className}`}>
      <div className="mb-5">
        <h3 className="text-xl font-black tracking-tight text-slate-950">
          {title}
        </h3>
        {subtitle && (
          <p className="mt-2 text-sm font-semibold leading-6 text-slate-500">
            {subtitle}
          </p>
        )}
      </div>

      {children}
    </div>
  );
}

export function MetricCard({
  title,
  value,
  small = false,
}: {
  title: string;
  value: string;
  small?: boolean;
}) {
  return (
    <div className="forge-stat-card">
      <span>{title}</span>
      <strong className={small ? "!text-lg !leading-snug" : ""}>
        {cleanText(value)}
      </strong>
    </div>
  );
}

export function MiniMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200/70 bg-white/75 p-4 shadow-sm">
      <p className="text-xs font-black uppercase tracking-wide text-slate-400">
        {label}
      </p>
      <p className="mt-2 break-words text-sm font-black text-slate-800">
        {cleanText(value)}
      </p>
    </div>
  );
}

export function ResultCard({
  title,
  value,
  large = false,
}: {
  title: string;
  value: string;
  large?: boolean;
}) {
  return (
    <div className="rounded-2xl border border-slate-200/70 bg-white/75 p-5 shadow-sm">
      <p className="text-xs font-black uppercase tracking-wide text-slate-400">
        {title}
      </p>
      <p
        className={
          large
            ? "mt-2 text-2xl font-black tracking-tight text-slate-950"
            : "mt-2 text-sm font-bold leading-6 text-slate-600"
        }
      >
        {cleanText(value)}
      </p>
    </div>
  );
}

export function AnalysisBlock({
  title,
  value,
}: {
  title: string;
  value?: string | null;
}) {
  return (
    <div className="rounded-2xl border border-slate-200/70 bg-white/75 p-5 shadow-sm">
      <h3 className="font-black text-slate-950">{title}</h3>
      <p className="mt-2 whitespace-pre-line text-sm font-semibold leading-6 text-slate-600">
        {cleanText(value || "—")}
      </p>
    </div>
  );
}

export function ListBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-2xl border border-slate-200/70 bg-white/75 p-5 shadow-sm">
      <h3 className="font-black text-slate-950">{title}</h3>

      {items.length > 0 ? (
        <ul className="mt-3 list-disc space-y-2 pl-5 text-sm font-semibold leading-6 text-slate-600">
          {items.map((item, index) => (
            <li key={`${item}-${index}`}>{cleanText(item)}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm font-semibold text-slate-400">—</p>
      )}
    </div>
  );
}

export function WarningList({
  title,
  items,
}: {
  title: string;
  items: string[];
}) {
  return (
    <div className="rounded-2xl border border-yellow-200 bg-yellow-50/80 p-5">
      <h3 className="font-black text-yellow-800">{title}</h3>

      <ul className="mt-3 list-disc space-y-2 pl-5 text-sm font-semibold leading-6 text-yellow-800/80">
        {items.map((item, index) => (
          <li key={`${item}-${index}`}>{cleanText(item)}</li>
        ))}
      </ul>
    </div>
  );
}

export function EmptyState({ text }: { text: string }) {
  return (
    <p className="rounded-2xl border border-slate-200/70 bg-white/65 p-5 text-sm font-semibold text-slate-400">
      {text}
    </p>
  );
}

export function ScoreBar({
  label,
  value,
}: {
  label: string;
  value?: number | null;
}) {
  const safeValue =
    typeof value !== "number" || Number.isNaN(value)
      ? 0
      : Math.max(0, Math.min(10, value));

  return (
    <div className="rounded-2xl border border-slate-200/70 bg-white/75 p-5 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-sm font-black text-slate-800">{label}</p>
        <p className="text-sm font-black text-slate-500">
          {formatScore(safeValue)}
        </p>
      </div>

      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-gradient-to-r from-sky-400 via-violet-500 to-rose-400"
          style={{ width: `${safeValue * 10}%` }}
        />
      </div>
    </div>
  );
}