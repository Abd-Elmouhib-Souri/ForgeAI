import type { ReactNode } from "react";

export default function ReportSection({
  id,
  number,
  title,
  subtitle,
  children,
}: {
  id?: string;
  number: number;
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <section id={id} className="forge-card scroll-mt-28 p-6">
      <div className="mb-6 flex items-start gap-4">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-400 via-violet-500 to-rose-400 text-sm font-black text-white shadow-lg shadow-violet-200">
          {number}
        </div>

        <div>
          <h2 className="text-2xl font-black tracking-tight text-slate-950">
            {title}
          </h2>
          {subtitle && (
            <p className="mt-2 text-sm font-semibold leading-6 text-slate-500">
              {subtitle}
            </p>
          )}
        </div>
      </div>

      {children}
    </section>
  );
}