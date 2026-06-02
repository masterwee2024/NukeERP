import { useRef } from "react";
import type { DynamicFieldProps } from "./types";

export default function ImageField({
  field,
  value,
  onChange,
  error,
  disabled,
}: DynamicFieldProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const previewUrl = typeof value === "string" ? value : "";

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) {
      onChange(field.field_name, file);
    }
  }

  return (
    <div className="space-y-1">
      <label className="block text-sm font-medium text-secondary-700">
        {field.label}
        {field.required && <span className="text-danger-500 ml-0.5">*</span>}
      </label>
      <div className="flex items-start gap-3">
        {previewUrl && (
          <img
            src={previewUrl}
            alt={field.label}
            className="h-16 w-16 rounded-md object-cover border border-secondary-200"
          />
        )}
        <div className="flex-1">
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            onChange={handleChange}
            disabled={disabled || field.readonly}
            className="hidden"
          />
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={disabled || field.readonly}
            className={`rounded-md border px-3 py-2 text-sm outline-none transition-colors ${
              error ? "border-danger-500" : "border-secondary-300 hover:bg-secondary-50"
            } ${disabled || field.readonly ? "cursor-not-allowed opacity-50" : "cursor-pointer bg-white"}`}
          >
            {previewUrl ? "Change..." : "Upload..."}
          </button>
          {previewUrl && (
            <button
              type="button"
              onClick={() => onChange(field.field_name, null)}
              className="ml-2 text-sm text-danger-500 hover:text-danger-600"
            >
              Remove
            </button>
          )}
        </div>
      </div>
      {field.help_text && !error && (
        <p className="text-xs text-secondary-400">{field.help_text}</p>
      )}
      {error && <p className="text-xs text-danger-500">{error}</p>}
    </div>
  );
}
