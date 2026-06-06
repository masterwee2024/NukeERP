import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import FormPageLayout from "@/components/shared/FormPageLayout";
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
        .get("/financial/reports/trial_balance/", { params: filters })
        .then((r) => r.data),
    enabled: Object.keys(filters).length > 0 && !!filters.period_from && !!filters.period_to,
  });

  const handleDrillDown = (row: Record<string, unknown>, _columnKey: string) => {
    const accountId = (row.account_id as string) || (row.id as string);
    const periodId = filters.period_to as string;
    if (accountId && periodId) {
      setDrillDown({ accountId, periodId });
    }
  };

  const renderReportContent = () => {
    if (isLoading) {
      return (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent" />
        </div>
      );
    }

    if (isError) {
      return (
        <div className="rounded-lg border border-danger-200 bg-danger-50 p-4 text-danger-700">
          {(error as Error)?.message || "Failed to load report data."}
        </div>
      );
    }

    if (data && !isLoading) {
      return (
        <div className="space-y-4">
          <div className="text-sm text-secondary-500">
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
        </div>
      );
    }

    return (
      <div className="rounded-lg border border-dashed border-secondary-300 p-12 text-center text-secondary-500">
        Select period range and click "Apply Filters" to generate the trial balance.
      </div>
    );
  };

  return (
    <div className="h-full">
      <div className="border-b border-secondary-200 px-4 py-3 xl:px-6">
        <h1 className="text-xl font-semibold text-secondary-900">Trial Balance</h1>
      </div>

      <FormPageLayout
        leftPanel={{
          id: "filters",
          label: "Filters",
          content: (
            <div className="p-4">
              <ReportFilters reportCode="trial_balance" onRun={setFilters} />
            </div>
          ),
        }}
        rightPanel={{
          id: "report",
          label: "Report",
          content: <div className="h-full overflow-auto p-4 xl:p-6">{renderReportContent()}</div>,
        }}
      />

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
