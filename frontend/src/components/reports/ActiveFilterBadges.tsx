import { X } from "lucide-react";

interface ActiveFilterBadgesProps {
  params: Array<{ key: string; label: string }>;
  values: Record<string, unknown>;
  onClear: (key: string) => void;
  onClearAll: () => void;
}

const labelMap: Record<string, string> = {
  period_from: "Period From",
  period_to: "Period To",
  account_ids: "Accounts",
  show_zero_balances: "Show Zero",
};

function formatValue(key: string, value: unknown): string {
  if (key === "show_zero_balances") return value ? "Yes" : "No";
  if (Array.isArray(value)) return `${value.length} selected`;
  return String(value ?? "");
}

export default function ActiveFilterBadges({
  params,
  values,
  onClear,
  onClearAll,
}: ActiveFilterBadgesProps) {
  const activeFilters = params.filter((p) => {
    const v = values[p.key];
    return v !== undefined && v !== null && v !== "" && !(Array.isArray(v) && v.length === 0);
  });

  if (activeFilters.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2">
      {activeFilters.map((p) => (
        <span
          key={p.key}
          className="inline-flex items-center gap-1 rounded-full bg-secondary-100 px-3 py-1 text-xs font-medium text-secondary-700"
        >
          {labelMap[p.label] || p.label}: {formatValue(p.key, values[p.key])}
          <button
            onClick={() => onClear(p.key)}
            className="ml-0.5 rounded-full p-0.5 hover:bg-secondary-200"
          >
            <X className="h-3 w-3" />
          </button>
        </span>
      ))}
      <button
        onClick={onClearAll}
        className="text-xs font-medium text-secondary-500 hover:text-secondary-700"
      >
        Clear All
      </button>
    </div>
  );
}
