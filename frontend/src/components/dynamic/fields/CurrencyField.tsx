import type { DynamicFieldProps } from "./types";

export default function CurrencyField({
  field,
  value,
  onChange,
  error,
  disabled,
}: DynamicFieldProps) {
  const prefix = field.prefix || "RM";

  return (
    <div className="space-y-1">
      <label className="block text-sm font-medium text-secondary-700">
        {field.label}
        {field.required && <span className="text-danger-500 ml-0.5">*</span>}
      </label>
      <div className="relative">
        <span className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-sm text-secondary-500">
          {prefix}
        </span>
        <input
          type="number"
          step="0.01"
          value={value as number}
          onChange={(e) =>
            onChange(
              field.field_name,
              e.target.value === "" ? null : Number(e.target.value)
            )
          }
          placeholder={field.placeholder}
          disabled={disabled || field.readonly}
          className={`w-full rounded-md border pl-10 pr-3 py-2 text-sm outline-none transition-colors ${
            error
              ? "border-danger-500 focus:border-danger-500"
              : "border-secondary-300 focus:border-primary-500"
          } ${disabled || field.readonly ? "bg-secondary-50 text-secondary-400" : "bg-white"}`}
        />
      </div>
      {field.help_text && !error && (
        <p className="text-xs text-secondary-400">{field.help_text}</p>
      )}
      {error && <p className="text-xs text-danger-500">{error}</p>}
    </div>
  );
}
