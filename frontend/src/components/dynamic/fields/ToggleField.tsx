import type { DynamicFieldProps } from "./types";

export default function ToggleField({
  field,
  value,
  onChange,
  error,
  disabled,
}: DynamicFieldProps) {
  const checked = Boolean(value);

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-3">
        <button
          type="button"
          role="switch"
          aria-checked={checked}
          onClick={() => onChange(field.field_name, !checked)}
          disabled={disabled || field.readonly}
          className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent outline-none transition-colors ${
            checked ? "bg-primary-600" : "bg-secondary-200"
          } ${disabled || field.readonly ? "opacity-50 cursor-not-allowed" : ""}`}
        >
          <span
            className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
              checked ? "translate-x-5" : "translate-x-0"
            }`}
          />
        </button>
        <label className="text-sm font-medium text-secondary-700">
          {field.label}
          {field.required && <span className="text-danger-500 ml-0.5">*</span>}
        </label>
      </div>
      {field.help_text && !error && (
        <p className="text-xs text-secondary-400">{field.help_text}</p>
      )}
      {error && <p className="text-xs text-danger-500">{error}</p>}
    </div>
  );
}
