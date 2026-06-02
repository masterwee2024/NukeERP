import type { DynamicFieldProps } from "./types";

export default function TextField({
  field,
  value,
  onChange,
  error,
  disabled,
}: DynamicFieldProps) {
  return (
    <div className="space-y-1">
      <label className="block text-sm font-medium text-secondary-700">
        {field.label}
        {field.required && <span className="text-danger-500 ml-0.5">*</span>}
      </label>
      <input
        type={field.field_type === "email" ? "email" : "text"}
        value={String(value ?? "")}
        onChange={(e) => onChange(field.field_name, e.target.value)}
        placeholder={field.placeholder}
        disabled={disabled || field.readonly}
        className={`w-full rounded-md border px-3 py-2 text-sm outline-none transition-colors ${
          error
            ? "border-danger-500 focus:border-danger-500"
            : "border-secondary-300 focus:border-primary-500"
        } ${disabled || field.readonly ? "bg-secondary-50 text-secondary-400" : "bg-white"}`}
      />
      {field.help_text && !error && (
        <p className="text-xs text-secondary-400">{field.help_text}</p>
      )}
      {error && <p className="text-xs text-danger-500">{error}</p>}
    </div>
  );
}
