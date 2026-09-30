// One toggle group for the list filters (analyses, users...): the active
// filter is announced to screen readers (aria-pressed) and visible at a glance.

export type FilterOption<T extends string> = { value: T; label: string };

export default function FilterTabs<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string; // what is being filtered, for screen readers
  options: FilterOption<T>[];
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <div role="group" aria-label={label} className="inline-flex flex-wrap gap-1 rounded-xl border border-white/10 bg-slate-950/60 p-1">
      {options.map((option) => {
        const active = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(option.value)}
            className={`h-8 whitespace-nowrap rounded-lg px-3 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-300 ${
              active ? "bg-red-500 text-white shadow" : "text-white/65 hover:bg-white/10 hover:text-white"
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
