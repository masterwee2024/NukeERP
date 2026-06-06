import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import ReportFilters from "@/components/reports/ReportFilters";
import ReportTable from "@/components/reports/ReportTable";
import ExportButtons from "@/components/reports/ExportButtons";
import DrillDownModal from "@/components/reports/DrillDownModal";

interface ColumnDef {
  key: string;
  label: string;
  type: string;
  align: string;
  format: string;
  width: string;
}

interface ReportResult {
  columns: ColumnDef[];
  rows: Record<string, unknown>[];
  total_rows: number;
  page: number;
  page_size: number;
  generated_at: string;
  summary: Record<string, number> | null;
  group_totals: Array<Record<string, unknown>> | null;
}

export default function TrialBalancePage() {
  const [filters, setFilters] = useState<Record<string, unknown>>({});
  const [drillDown, setDrillDown] = useState<{
    accountId: string;
    periodId: string;
  } | null>(null);

  const { data, isLoading, isError, error } = useQuery<ReportResult>({
    queryKey: ["report", "trial_balance", filters],
    queryFn: () =>
      api
        .get("/api/v1/financial/reports/trial_balance/", { params: filters })
        .then((r) => r.data),
    enabled: Object.keys(filters).length > 0 && !!filters.period_from && !!filters.period_to,
  });

  const handleDrillDown = (row: Record<string, unknown>, _columnKey: string) => {
    const accountId = row.account_id as string || row.id as string;
    const periodId = filters.period_to as string;
    if (accountId && periodId) {
      setDrillDown({ accountId, periodId });
    }
  };

  return (
    <div className="space-y-4 p-4">
      <h1 className="text-xl font-semibold text-gray-900">Trial Balance</h1>

      <ReportFilters reportCode="trial_balance" onRun={setFilters} />

      {isLoading && (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent" />
        </div>
      )}

      {isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          {(error as Error)?.message || "Failed to load report data."}
        </div>
      )}

      {data && !isLoading && (
        <>
          <div className="text-sm text-gray-500">
            Generated: {new Date(data.generated_at).toLocaleString()} &mdash; {data.total_rows} rows
          </div>

          <ReportTable
            columns={data.columns}
            rows={data.rows}
            groupField="account_type"
            summary={data.summary}
            groupTotals={data.group_totals}
            onDrillDown={handleDrillDown}
          />

          <ExportButtons reportCode="trial_balance" filters={filters} />
        </>
      )}

      {!data && !isLoading && !isError && Object.keys(filters).length === 0 && (
        <div className="rounded-lg border border-dashed border-gray-300 p-12 text-center text-gray-500">
          Select period range and click "Apply Filters" to generate the trial balance.
        </div>
      )}

      <DrillDownModal
        open={drillDown !== null}
        onClose={() => setDrillDown(null)}
        reportCode="trial_balance"
        accountId={drillDown?.accountId || ""}
        periodId={drillDown?.periodId || ""}
      />
    </div>
  );
}
