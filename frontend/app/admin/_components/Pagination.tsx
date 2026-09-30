import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";

import { Button } from "./Button";

// Sprint 7.4: pager of the admin lists (the API answers one page at a time).
// First/last page buttons avoid clicking "Suivant" twenty times.
export default function Pagination({
  page,
  pageSize,
  total,
  isLoading = false,
  onPageChange,
}: {
  page: number;
  pageSize: number;
  total: number;
  isLoading?: boolean;
  onPageChange: (page: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const first = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const last = Math.min(total, page * pageSize);
  const atStart = page <= 1 || isLoading;
  const atEnd = page >= pages || isLoading;

  return (
    <nav aria-label="Pagination" className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm">
      <span className="text-white/60">
        {first}–{last} sur {total}
      </span>
      <div className="flex items-center gap-2">
        <Button size="sm" icon={ChevronsLeft} aria-label="Première page" disabled={atStart} onClick={() => onPageChange(1)} />
        <Button size="sm" icon={ChevronLeft} aria-label="Page précédente" disabled={atStart} onClick={() => onPageChange(page - 1)}>
          Précédent
        </Button>
        <span className="px-2 text-white/60" aria-current="page">
          Page {page} / {pages}
        </span>
        <Button size="sm" aria-label="Page suivante" disabled={atEnd} onClick={() => onPageChange(page + 1)}>
          Suivant
          <ChevronRight size={14} aria-hidden="true" />
        </Button>
        <Button size="sm" icon={ChevronsRight} aria-label="Dernière page" disabled={atEnd} onClick={() => onPageChange(pages)} />
      </div>
    </nav>
  );
}
