import type { DynamicFieldProps } from "./types";

export default function CheckboxField({
  field,
  value,
  onChange,
  error,
  disabled,
}: DynamicFieldProps) {
  const checked = Boolean(value);

  return (
    <div className="space-y-1">
      <label className="flex cursor-pointer items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(field.field_name, e.target.checked)}
          disabled={disabled || field.readonly}
          className="rounded border-secondary-300 text-primary-600 focus:ring-primary-500"
        />
        <span className="font-medium text-secondary-700">
          {field.label}
          {field.required && <span className="text-danger-500 ml-0.5">*</span>}
        </span>
      </label>
      {field.help_text && !error && (
        <p className="text-xs text-secondary-400">{field.help_text}</p>
      )}
      {error && <p className="text-xs text-danger-500">{error}</p>}
    </div>
  );
}
