import { useState, useMemo, useRef, useCallback } from "react";
import { ChevronRight } from "lucide-react";

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
  groupTotals?: Array<Record<string, unknown>>;
  onDrillDown?: (row: Record<string, unknown>, columnKey: string) => void;
  page?: number;
  pageSize?: number;
  totalRows?: number;
  onPageChange?: (page: number) => void;
}

function formatGroupName(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function ReportTable({
  columns,
  rows,
  groupField,
  summary,
  groupTotals,
  onDrillDown,
  page = 1,
  pageSize = 100,
  totalRows = 0,
  onPageChange,
}: ReportTableProps) {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const [columnWidths, setColumnWidths] = useState<Record<string, number>>({});
  const [resizing, setResizing] = useState<{
    key: string;
    startX: number;
    startWidth: number;
  } | null>(null);
  const tableRef = useRef<HTMLTableElement>(null);

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

  const toggleGroup = useCallback((name: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }, []);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent, colKey: string) => {
      e.preventDefault();
      const th = (e.target as HTMLElement).closest("th");
      const startWidth = th?.offsetWidth || 100;
      setResizing({ key: colKey, startX: e.clientX, startWidth });
    },
    [],
  );

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!resizing) return;
      const diff = e.clientX - resizing.startX;
      const newWidth = Math.max(60, resizing.startWidth + diff);
      setColumnWidths((prev) => ({ ...prev, [resizing.key]: newWidth }));
    },
    [resizing],
  );

  const handleMouseUp = useCallback(() => {
    setResizing(null);
  }, []);

  useMemo(() => {
    if (resizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    }
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, [resizing, handleMouseMove, handleMouseUp]);

  const totalPages = Math.max(1, Math.ceil(totalRows / pageSize));
  const fromRow = (page - 1) * pageSize + 1;
  const toRow = Math.min(page * pageSize, totalRows);

  const renderCell = (row: Record<string, unknown>, col: ColumnDef) => {
    const val = row[col.key];
    const isCurrency = col.type === "currency" || col.type === "decimal";
    const display =
      isCurrency && val != null
        ? Number(val).toLocaleString("en-MY", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })
        : String(val ?? "");

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

  const renderTotalRow = (
    label: string,
    totals: Record<string, unknown>,
    isGrand: boolean,
  ) => (
    <tr
      className={`border-t ${
        isGrand
          ? "border-secondary-400 bg-secondary-100 font-bold"
          : "border-secondary-300 bg-secondary-50 font-semibold"
      }`}
    >
      {columns.map((col) => {
        const val = totals[col.key];
        const isCurrency = col.type === "currency" || col.type === "decimal";
        const display =
          isCurrency && val != null
            ? Number(val).toLocaleString("en-MY", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })
            : col.key === columns[0]?.key
              ? label
              : "";
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
    <div className="overflow-x-auto rounded-lg border border-secondary-200">
      <table ref={tableRef} className="min-w-full divide-y divide-secondary-200">
        <thead className="bg-secondary-50 sticky top-0 z-10">
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                className={`relative px-3 py-3 text-xs font-semibold uppercase tracking-wider text-secondary-500 ${
                  col.align === "right" ? "text-right" : "text-left"
                }`}
                style={
                  columnWidths[col.key]
                    ? { width: columnWidths[col.key] }
                    : undefined
                }
              >
                {col.label}
                <div
                  onMouseDown={(e) => handleMouseDown(e, col.key)}
                  className="absolute right-0 top-0 h-full w-1.5 cursor-col-resize hover:bg-primary-400 active:bg-primary-500"
                />
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-secondary-200 bg-white">
          {groupedRows.groups
            ? Object.entries(groupedRows.groups).map(
                ([groupName, groupRows]) => {
                  const isExpanded = expandedGroups.has(groupName);
                  return (
                    <>
                      <tr
                        key={groupName}
                        className="bg-secondary-50 cursor-pointer"
                        onClick={() => toggleGroup(groupName)}
                      >
                        <td
                          colSpan={columns.length}
                          className="px-3 py-2 text-sm font-semibold text-secondary-700"
                        >
                          <ChevronRight
                            className={`inline-block h-4 w-4 mr-1 transition-transform ${
                              isExpanded ? "rotate-90" : ""
                            }`}
                          />
                          {formatGroupName(groupName)} ({groupRows.length}{" "}
                          accounts)
                        </td>
                      </tr>
                      {isExpanded &&
                        groupRows.map((row, i) => (
                          <tr key={i} className="hover:bg-secondary-50">
                            {columns.map((col) => renderCell(row, col))}
                          </tr>
                        ))}
                      {isExpanded &&
                        groupTotals?.map((gt) => {
                          if (gt.group === groupName) {
                            return renderTotalRow(
                              `Total ${formatGroupName(groupName)}`,
                              gt,
                              false,
                            );
                          }
                          return null;
                        })}
                    </>
                  );
                },
              )
            : (groupedRows.flat || rows).map((row, i) => (
                <tr key={i} className="hover:bg-secondary-50">
                  {columns.map((col) => renderCell(row, col))}
                </tr>
              ))}
          {summary &&
            renderTotalRow(
              "Grand Total",
              summary as unknown as Record<string, unknown>,
              true,
            )}
        </tbody>
      </table>

      {totalRows > 0 && onPageChange && (
        <div className="flex items-center justify-between border-t border-secondary-200 bg-white px-4 py-3">
          <div className="text-sm text-secondary-500">
            Showing {fromRow}-{toRow} of {totalRows}
          </div>
          <div className="flex items-center gap-2">
            <button
              disabled={page <= 1}
              onClick={() => onPageChange(page - 1)}
              className="rounded-md border border-secondary-300 bg-white px-3 py-1 text-sm font-medium text-secondary-700 hover:bg-secondary-50 disabled:opacity-50"
            >
              &lt; Prev
            </button>
            <span className="text-sm text-secondary-500">
              Page {page} of {totalPages}
            </span>
            <button
              disabled={page >= totalPages}
              onClick={() => onPageChange(page + 1)}
              className="rounded-md border border-secondary-300 bg-white px-3 py-1 text-sm font-medium text-secondary-700 hover:bg-secondary-50 disabled:opacity-50"
            >
              Next &gt;
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
