import { useOptionsResolver } from "@/hooks/useOptionsResolver";
import type { DynamicFieldProps } from "./types";

export default function RadioField({
  field,
  value,
  onChange,
  error,
  disabled,
}: DynamicFieldProps) {
  const { options, loading } = useOptionsResolver(field);

  return (
    <div className="space-y-1">
      <label className="block text-sm font-medium text-secondary-700">
        {field.label}
        {field.required && <span className="text-danger-500 ml-0.5">*</span>}
      </label>
      <div className="space-y-1">
        {loading ? (
          <p className="text-sm text-secondary-400">Loading...</p>
        ) : (
          options.map((opt) => (
            <label
              key={opt.value}
              className="flex cursor-pointer items-center gap-2 text-sm text-secondary-700"
            >
              <input
                type="radio"
                name={field.field_name}
                value={opt.value}
                checked={String(value) === opt.value}
                onChange={(e) => onChange(field.field_name, e.target.value)}
                disabled={disabled || field.readonly}
                className="border-secondary-300 text-primary-600 focus:ring-primary-500"
              />
              {opt.label}
            </label>
          ))
        )}
      </div>
      {field.help_text && !error && (
        <p className="text-xs text-secondary-400">{field.help_text}</p>
      )}
      {error && <p className="text-xs text-danger-500">{error}</p>}
    </div>
  );
}
