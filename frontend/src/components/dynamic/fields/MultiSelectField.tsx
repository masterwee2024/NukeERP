import { useOptionsResolver } from "@/hooks/useOptionsResolver";
import type { DynamicFieldProps } from "./types";

export default function MultiSelectField({
  field,
  value,
  onChange,
  error,
  disabled,
}: DynamicFieldProps) {
  const { options, loading } = useOptionsResolver(field);
  const selected = Array.isArray(value) ? value : [];

  function handleToggle(optValue: string) {
    const next = selected.includes(optValue)
      ? selected.filter((v: string) => v !== optValue)
      : [...selected, optValue];
    onChange(field.field_name, next);
  }

  return (
    <div className="space-y-1">
      <label className="block text-sm font-medium text-secondary-700">
        {field.label}
        {field.required && <span className="text-danger-500 ml-0.5">*</span>}
      </label>
      <div
        className={`max-h-40 overflow-y-auto rounded-md border p-1 ${
          error ? "border-danger-500" : "border-secondary-300"
        }`}
      >
        {(loading ? [] : options).map((opt) => {
          const isSelected = selected.includes(opt.value);
          return (
            <label
              key={opt.value}
              className={`flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-secondary-100 ${
                isSelected ? "bg-primary-50 text-primary-700" : "text-secondary-700"
              }`}
            >
              <input
                type="checkbox"
                checked={isSelected}
                onChange={() => handleToggle(opt.value)}
                disabled={disabled || field.readonly}
                className="rounded border-secondary-300 text-primary-600 focus:ring-primary-500"
              />
              {opt.label}
            </label>
          );
        })}
        {!loading && options.length === 0 && (
          <p className="px-2 py-1.5 text-sm text-secondary-400">No options available</p>
        )}
      </div>
      {field.help_text && !error && (
        <p className="text-xs text-secondary-400">{field.help_text}</p>
      )}
      {error && <p className="text-xs text-danger-500">{error}</p>}
    </div>
  );
}
