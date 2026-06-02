import type { DynamicFieldProps } from "./types";

export default function ReadonlyTextField({ field, value }: DynamicFieldProps) {
  return (
    <div className="space-y-1">
      <label className="block text-sm font-medium text-secondary-700">
        {field.label}
      </label>
      <p className="rounded-md border border-secondary-200 bg-secondary-50 px-3 py-2 text-sm text-secondary-800">
        {String(value ?? "") || "—"}
      </p>
    </div>
  );
}
