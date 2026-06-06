import { useMemo } from "react";

interface ColumnDef {
  key: string;
  label: string;
  type: string;
  align: string;
}

interface ReportTableProps {
  columns: ColumnDef[];
  rows: Record<string, unknown>[];
  groupField?: string;
  summary?: Record<string, number> | null;
  groupTotals?: Array<Record<string, unknown>> | null;
  onDrillDown?: (row: Record<string, unknown>, columnKey: string) => void;
}

export default function ReportTable({
  columns,
  rows,
  groupField,
  summary,
  groupTotals,
  onDrillDown,
}: ReportTableProps) {
  const groupedRows = useMemo(() => {
    if (!groupField) return { groups: null, flat: rows };

    const groups: Record<string, Record<string, unknown>[]> = {};
    for (const row of rows) {
      const gval = String(row[groupField] || "Other");
      if (!groups[gval]) groups[gval] = [];
      groups[gval].push(row);
    }
    return { groups, flat: null };
  }, [rows, groupField]);

  const renderCell = (row: Record<string, unknown>, col: ColumnDef) => {
    const val = row[col.key];
    const isCurrency = col.type === "currency" || col.type === "decimal";
    const display = isCurrency && val != null ? Number(val).toLocaleString("en-MY", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }) : String(val ?? "");

    return (
      <td
        key={col.key}
        className={`whitespace-nowrap px-3 py-2 text-sm ${
          col.align === "right" ? "text-right" : "text-left"
        } ${isCurrency ? "font-mono" : ""}`}
        onClick={() => onDrillDown?.(row, col.key)}
      >
        {display}
      </td>
    );
  };

  const renderTotalRow = (label: string, totals: Record<string, unknown>, isGrand: boolean) => (
    <tr className={`border-t ${isGrand ? "border-gray-400 bg-gray-100 font-bold" : "border-gray-300 bg-gray-50 font-semibold"}`}>
      {columns.map((col) => {
        const val = totals[col.key];
        const isCurrency = col.type === "currency" || col.type === "decimal";
        const display = isCurrency && val != null
          ? Number(val).toLocaleString("en-MY", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
          : col.key === columns[0]?.key ? label : "";
        return (
          <td
            key={col.key}
            className={`whitespace-nowrap px-3 py-2 text-sm ${
              col.align === "right" ? "text-right" : "text-left"
            } ${isCurrency ? "font-mono" : ""}`}
          >
            {display}
          </td>
        );
      })}
    </tr>
  );

  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                className={`px-3 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500 ${
                  col.align === "right" ? "text-right" : "text-left"
                }`}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white">
          {groupedRows.groups
            ? Object.entries(groupedRows.groups).map(([groupName, groupRows]) => (
                <>
                  <tr className="bg-blue-50">
                    <td
                      colSpan={columns.length}
                      className="px-3 py-2 text-sm font-semibold text-blue-800"
                    >
                      {groupName}
                    </td>
                  </tr>
                  {groupRows.map((row, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      {columns.map((col) => renderCell(row, col))}
                    </tr>
                  ))}
                  {groupTotals?.map((gt) => {
                    if (gt.group === groupName) {
                      return renderTotalRow(`Total ${groupName}`, gt, false);
                    }
                    return null;
                  })}
                </>
              ))
            : (groupedRows.flat || rows).map((row, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  {columns.map((col) => renderCell(row, col))}
                </tr>
              ))}
          {summary && renderTotalRow("Grand Total", summary as unknown as Record<string, unknown>, true)}
        </tbody>
      </table>
    </div>
  );
}
