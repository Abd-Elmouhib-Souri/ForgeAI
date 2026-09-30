// Sprint 7.4: one way to turn the screen's filters into a query string, used
// by the list AND its CSV export, so both always show the same rows.

export type Page<T> = { items: T[]; total: number; page: number; page_size: number };

export type ListParams = Record<string, string | number | boolean | null | undefined>;

export function buildListQuery(params: ListParams) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue; // "no filter"
    query.set(key, typeof value === "string" ? value.trim() : String(value));
  }
  const text = query.toString();
  return text ? `?${text}` : "";
}
