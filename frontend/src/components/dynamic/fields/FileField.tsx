import { useRef } from "react";
import type { DynamicFieldProps } from "./types";

export default function FileField({
  field,
  value,
  onChange,
  error,
  disabled,
}: DynamicFieldProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const fileName = value
    ? typeof value === "string"
      ? value.split("/").pop() || value
      : "File selected"
    : "";

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
      <div className="flex items-center gap-2">
        <input
          ref={inputRef}
          type="file"
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
          Browse...
        </button>
        <span className="text-sm text-secondary-500 truncate max-w-[200px]">
          {fileName || field.placeholder || "No file chosen"}
        </span>
        {fileName && (
          <button
            type="button"
            onClick={() => onChange(field.field_name, null)}
            className="text-sm text-danger-500 hover:text-danger-600"
          >
            Clear
          </button>
        )}
      </div>
      {field.help_text && !error && (
        <p className="text-xs text-secondary-400">{field.help_text}</p>
      )}
      {error && <p className="text-xs text-danger-500">{error}</p>}
    </div>
  );
}
