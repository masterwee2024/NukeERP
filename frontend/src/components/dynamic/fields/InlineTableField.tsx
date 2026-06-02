import type { PageConfigField } from "@/hooks/usePageConfig";
import type { DynamicFieldProps } from "./types";

export default function InlineTableField({
  field,
  value,
  onChange,
  disabled,
}: DynamicFieldProps) {
  const rows: Record<string, unknown>[] = Array.isArray(value) ? value : [];
  const lineFields: PageConfigField[] = field.line_fields || [];

  function addRow() {
    const newRow: Record<string, unknown> = {};
    for (const lf of lineFields) {
      newRow[lf.field_name] = lf.default_value || "";
    }
    onChange(field.field_name, [...rows, newRow]);
  }

  function removeRow(index: number) {
    const next = rows.filter((_, i) => i !== index);
    onChange(field.field_name, next);
  }

  function updateRow(index: number, rowField: string, rowValue: unknown) {
    const next = rows.map((row, i) =>
      i === index ? { ...row, [rowField]: rowValue } : row
    );
    onChange(field.field_name, next);
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-secondary-700">
          {field.label}
          {field.required && <span className="text-danger-500 ml-0.5">*</span>}
        </label>
        {!disabled && !field.readonly && (
          <button
            type="button"
            onClick={addRow}
            className="rounded-md bg-primary-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-700"
          >
            + Add Row
          </button>
        )}
      </div>

      <div className="overflow-x-auto rounded-md border border-secondary-200">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-secondary-50">
              {lineFields.map((lf) => (
                <th
                  key={lf.field_name}
                  className="px-3 py-2 text-left font-medium text-secondary-600"
                >
                  {lf.label}
                </th>
              ))}
              {!disabled && !field.readonly && <th className="px-3 py-2 w-12" />}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td
                  colSpan={lineFields.length + (disabled || field.readonly ? 0 : 1)}
                  className="px-3 py-4 text-center text-secondary-400"
                >
                  No items
                </td>
              </tr>
            )}
            {rows.map((row, rowIndex) => (
              <tr
                key={rowIndex}
                className="border-t border-secondary-100 hover:bg-secondary-50"
              >
                {lineFields.map((lf) => (
                  <td key={lf.field_name} className="px-3 py-1.5">
                    <input
                      type={
                        lf.field_type === "number" || lf.field_type === "decimal"
                          ? "number"
                          : "text"
                      }
                      step={lf.field_type === "decimal" ? "0.01" : undefined}
                      value={String(row[lf.field_name] ?? "")}
                      onChange={(e) => {
                        const val =
                          lf.field_type === "number" || lf.field_type === "decimal"
                            ? e.target.value === ""
                              ? null
                              : Number(e.target.value)
                            : e.target.value;
                        updateRow(rowIndex, lf.field_name, val);
                      }}
                      disabled={disabled || field.readonly}
                      className="w-full rounded border-0 bg-transparent px-1 py-1 text-sm outline-none focus:ring-0"
                      placeholder={lf.placeholder}
                    />
                  </td>
                ))}
                {!disabled && !field.readonly && (
                  <td className="px-3 py-1.5">
                    <button
                      type="button"
                      onClick={() => removeRow(rowIndex)}
                      className="text-danger-500 hover:text-danger-600 text-sm"
                    >
                      ✕
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
