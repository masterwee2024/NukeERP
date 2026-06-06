import { useState, useMemo } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import api from "@/lib/api";
import FormPageLayout from "@/components/shared/FormPageLayout";
import ReportFilters from "@/components/reports/ReportFilters";
import ReportTable from "@/components/reports/ReportTable";
import ExportButtons from "@/components/reports/ExportButtons";
import DrillDownModal from "@/components/reports/DrillDownModal";
import ActiveFilterBadges from "@/components/reports/ActiveFilterBadges";
import ViewSwitcher from "@/components/reports/ViewSwitcher";
import ReportChart from "@/components/reports/ReportChart";
import { useIsMobile } from "@/hooks/useIsMobile";

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

interface ReportDefinitionOut {
  id: string;
  code: string;
  name: string;
  module: string;
  category: string;
  compute_type: string;
  group_field: string;
}

const filterParamLabels: Record<string, string> = {
  period_from: "Period From",
  period_to: "Period To",
  account_ids: "Accounts",
  show_zero_balances: "Show Zero",
};

function SummaryCard({
  title,
  value,
  variant,
}: {
  title: string;
  value: number;
  variant?: "success" | "danger" | "default";
}) {
  const colors = {
    success: "border-green-200 bg-green-50 text-green-700",
    danger: "border-red-200 bg-red-50 text-red-700",
    default: "border-secondary-200 bg-white text-secondary-900",
  };
  return (
    <div className={`rounded-lg border p-4 ${colors[variant || "default"]}`}>
      <p className="text-xs font-medium uppercase tracking-wide">{title}</p>
      <p className="mt-1 text-xl font-bold font-mono">
        {value.toLocaleString("en-MY", { minimumFractionDigits: 2 })}
      </p>
    </div>
  );
}

export default function ReportPage() {
  const { reportCode: rawCode } = useParams<{ reportCode: string }>();
  const reportCode = rawCode?.replace(/-/g, "_") || "";
  const [filters, setFilters] = useState<Record<string, unknown>>({});
  const [view, setView] = useState<"table" | "chart">("table");
  const [page, setPage] = useState(1);
  const [drillDown, setDrillDown] = useState<{
    accountId: string;
    periodId: string;
  } | null>(null);

  const { data: reportsList } = useQuery<ReportDefinitionOut[]>({
    queryKey: ["reports-list"],
    queryFn: () => api.get("/financial/reports/").then((r) => r.data),
    staleTime: 60_000,
  });
  const reportDef = reportsList?.find((r) => r.code === reportCode);

  const { data: periods } = useQuery<Array<{ id: string; name: string }>>({
    queryKey: ["periods"],
    queryFn: () => api.get("/financial/periods/").then((r) => r.data),
    staleTime: 60_000,
  });
  const periodMap = new Map(periods?.map((p) => [p.id, p.name]));

  const { data: companyInfo } = useQuery<{ name: string }>({
    queryKey: ["current-company"],
    queryFn: () => api.get("/core/companies/current/").then((r) => r.data),
    staleTime: 60_000,
  });

  const { data, isLoading, isError, error, refetch } = useQuery<ReportResult>(
    {
      queryKey: ["report", reportCode, filters, page],
      queryFn: () =>
      api
        .get(`/financial/reports/${reportCode}/`, {
          params: { ...filters, page, page_size: 100 },
        })
        .then((r) => r.data),
      enabled:
        Object.keys(filters).length > 0 &&
        !!filters.period_from &&
        !!filters.period_to,
    },
  );

  const isMobile = useIsMobile();

  const handleDrillDown = (row: Record<string, unknown>, _columnKey: string) => {
    const accountId = (row.account_id as string) || (row.id as string);
    const periodId = filters.period_to as string;
    if (accountId && periodId) {
      setDrillDown({ accountId, periodId });
    }
  };

  const handleClearFilter = (key: string) => {
    setFilters((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
  };

  const handleClearAllFilters = () => {
    setFilters({});
    setPage(1);
  };

  const summaryCards = useMemo(() => {
    if (!data?.summary) return null;
    const closingDebit = data.summary.closing_debit || 0;
    const closingCredit = data.summary.closing_credit || 0;
    const balance = closingDebit - closingCredit;
    return { totalDebit: closingDebit, totalCredit: closingCredit, balance };
  }, [data]);

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

    if (!data) {
      return (
        <div className="rounded-lg border border-dashed border-secondary-300 p-12 text-center text-secondary-500">
          Select period range and click "Apply Filters" to generate the report.
        </div>
      );
    }

    if (isMobile) {
      return (
        <div className="space-y-4 p-4">
          <div className="border-b border-secondary-200 pb-3">
            <h2 className="text-lg font-bold text-secondary-900">{reportDef?.name || "Report"}</h2>
            <p className="text-xs text-secondary-400">
              Generated: {new Date(data.generated_at).toLocaleString()} &mdash;{" "}
              {data.total_rows} rows
            </p>
          </div>
          <div className="flex flex-col gap-3">
            <ExportButtons reportCode={reportCode || ""} filters={filters} />
          </div>
        </div>
      );
    }

    const activeParams = Object.keys(filters)
      .filter((k) => k !== "page" && k !== "page_size")
      .map((k) => ({
        key: k,
        label: filterParamLabels[k] || k,
      }));

    const groupField = reportDef?.group_field || data.columns.find((c) => c.key === "account_type")?.key;

    const periodFromName = filters.period_from ? periodMap.get(filters.period_from as string) : null;
    const periodToName = filters.period_to ? periodMap.get(filters.period_to as string) : null;
    const periodLabel = periodFromName && periodToName
      ? `${periodFromName} — ${periodToName}`
      : periodFromName || periodToName || "";

    return (
      <div className="space-y-4">
        {/* Report Header */}
        <div className="border-b border-secondary-200 pb-3">
          <div className="flex justify-between items-start">
            <div>
              {companyInfo?.name && (
                <p className="text-sm font-semibold text-secondary-600">{companyInfo.name}</p>
              )}
              <h2 className="text-lg font-bold text-secondary-900">{reportDef?.name || "Report"}</h2>
              {periodLabel && (
                <p className="text-sm text-secondary-500">Period: {periodLabel}</p>
              )}
              <p className="text-xs text-secondary-400">
                Generated: {new Date(data.generated_at).toLocaleString()} &mdash;{" "}
                {data.total_rows} rows
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between">
          <ViewSwitcher view={view} onChange={setView} />
          <div className="flex items-center gap-2">
            <ExportButtons reportCode={reportCode || ""} filters={filters} />
            <button
              onClick={() => refetch()}
              className="rounded-md border border-secondary-300 bg-white px-3 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-50"
            >
              <RefreshCw className="inline-block h-4 w-4 mr-1" />
              Refresh
            </button>
          </div>
        </div>

        <ActiveFilterBadges
          params={activeParams}
          values={filters}
          onClear={handleClearFilter}
          onClearAll={handleClearAllFilters}
        />

        {summaryCards && (
          <div className="grid grid-cols-3 gap-4">
            <SummaryCard title="Total Debit" value={summaryCards.totalDebit} />
            <SummaryCard title="Total Credit" value={summaryCards.totalCredit} />
            <SummaryCard
              title="Balance"
              value={summaryCards.balance}
              variant={summaryCards.balance === 0 ? "success" : "danger"}
            />
          </div>
        )}

        {view === "table" ? (
          <ReportTable
            columns={data.columns}
            rows={data.rows}
            groupField={groupField}
            summary={data.summary}
            groupTotals={data.group_totals || []}
            onDrillDown={handleDrillDown}
            page={data.page}
            pageSize={data.page_size}
            totalRows={data.total_rows}
            onPageChange={setPage}
          />
        ) : (
          <ReportChart
            columns={data.columns}
            rows={data.rows}
            groupField={groupField}
          />
        )}

        {/* Report Footer */}
        <div className="border-t border-secondary-200 pt-3 flex justify-between text-xs text-secondary-400">
          <span>End of Report &mdash; {data.total_rows} rows</span>
          <span>Page {data.page} of {Math.ceil(data.total_rows / data.page_size)}</span>
        </div>
      </div>
    );
  };

  return (
    <div className="h-full">
      <div className="border-b border-secondary-200 px-4 py-3 xl:px-6">
        <h1 className="text-xl font-semibold text-secondary-900">
          {reportDef?.name || "Report"}
        </h1>
      </div>

      <FormPageLayout
        leftPanel={{
          id: "filters",
          label: "Filters",
          content: (
            <div className="p-4">
              <ReportFilters
                reportCode={reportCode || ""}
                onRun={(vals) => {
                  setFilters(vals);
                  setPage(1);
                }}
              />
            </div>
          ),
        }}
        rightPanel={{
          id: "report",
          label: "Report",
          content: (
            <div className="h-full overflow-auto p-4 xl:p-6">
              {renderReportContent()}
            </div>
          ),
        }}
      />

      <DrillDownModal
        open={drillDown !== null}
        onClose={() => setDrillDown(null)}
        reportCode={reportCode || ""}
        accountId={drillDown?.accountId || ""}
        periodId={drillDown?.periodId || ""}
      />
    </div>
  );
}
