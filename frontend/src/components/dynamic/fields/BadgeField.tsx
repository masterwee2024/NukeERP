import type { DynamicFieldProps } from "./types";

const defaultColors: Record<string, string> = {
  draft: "bg-secondary-100 text-secondary-700",
  pending: "bg-warning-100 text-warning-700",
  approved: "bg-success-100 text-success-700",
  posted: "bg-primary-100 text-primary-700",
  void: "bg-danger-100 text-danger-700",
  cancelled: "bg-danger-100 text-danger-700",
  completed: "bg-success-100 text-success-700",
};

export default function BadgeField({ field, value }: DynamicFieldProps) {
  const strVal = String(value ?? "");
  const colorMap = field.badge_color || {};
  const colorClass =
    colorMap[strVal] ||
    defaultColors[strVal.toLowerCase()] ||
    "bg-secondary-100 text-secondary-700";

  return (
    <div className="space-y-1">
      <label className="block text-sm font-medium text-secondary-700">
        {field.label}
      </label>
      <span
        className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${colorClass}`}
      >
        {strVal || "—"}
      </span>
    </div>
  );
}
