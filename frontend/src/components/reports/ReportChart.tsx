import { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

interface ColumnDef {
  key: string;
  label: string;
  type: string;
  align: string;
}

interface ReportChartProps {
  columns: ColumnDef[];
  rows: Record<string, unknown>[];
  groupField?: string;
}

function formatValue(value: number): string {
  return value.toLocaleString("en-MY", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export default function ReportChart({
  rows,
  groupField,
}: ReportChartProps) {
  const chartData = useMemo(() => {
    if (!groupField) return [];
    const groups: Record<string, { debit: number; credit: number }> = {};
    for (const row of rows) {
      const group = String(row[groupField] || "Other");
      if (!groups[group]) groups[group] = { debit: 0, credit: 0 };
      groups[group].debit += Number(row.closing_debit || row.debit || 0);
      groups[group].credit += Number(row.closing_credit || row.credit || 0);
    }
    return Object.entries(groups).map(([name, vals]) => ({
      name,
      debit: vals.debit,
      credit: vals.credit,
    }));
  }, [rows, groupField]);

  if (chartData.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-secondary-300 p-12 text-center text-secondary-500">
        No data available for chart view.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-secondary-200 bg-white p-4">
      <ResponsiveContainer width="100%" height={400}>
        <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 12, fill: "#6B7280" }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 12, fill: "#6B7280" }}
            tickLine={false}
            tickFormatter={formatValue}
          />
          <Tooltip
            contentStyle={{
              borderRadius: "8px",
              border: "1px solid #E5E7EB",
              fontSize: "12px",
            }}
          />
          <Legend />
          <Bar dataKey="debit" name="Debit" fill="#3B82F6" radius={[4, 4, 0, 0]} />
          <Bar dataKey="credit" name="Credit" fill="#F59E0B" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
