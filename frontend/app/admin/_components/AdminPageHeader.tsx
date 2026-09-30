import type { ReactNode } from "react";
import { ArrowLeft } from "lucide-react";

import { ButtonLink } from "./Button";

// Sprint 7.3: the title block of every console page. Navigation lives in
// the shell's sidebar; a page only adds its own actions (export...) and,
// for a detail page, a real "back" button to its list.
export default function AdminPageHeader({
  title,
  subtitle,
  backHref,
  backLabel = "Retour à la liste",
  actions,
}: {
  title: string;
  subtitle?: ReactNode;
  backHref?: string;
  backLabel?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="border-b border-white/10 bg-white/[0.03] px-6 py-5">
      <div className="mx-auto flex max-w-7xl flex-wrap items-end justify-between gap-4">
        <div>
          {backHref && (
            <ButtonLink href={backHref} variant="secondary" size="sm" icon={ArrowLeft} className="mb-3">
              {backLabel}
            </ButtonLink>
          )}
          <h1 className="text-2xl font-bold">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-white/50">{subtitle}</p>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
    </div>
  );
}
