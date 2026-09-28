// Sprint 7.4: pager of the admin lists (the API answers one page at a time).
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

  return (
    <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm">
      <span className="text-white/60">
        {first}–{last} sur {total}
      </span>
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1 || isLoading}
          className="rounded-lg border border-white/10 px-3 py-1.5 hover:bg-white/10 disabled:opacity-40"
        >
          Précédent
        </button>
        <span className="text-white/60">
          Page {page} / {pages}
        </span>
        <button
          type="button"
          onClick={() => onPageChange(page + 1)}
          disabled={page >= pages || isLoading}
          className="rounded-lg border border-white/10 px-3 py-1.5 hover:bg-white/10 disabled:opacity-40"
        >
          Suivant
        </button>
      </div>
    </div>
  );
}
