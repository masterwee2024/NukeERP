import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAction } from "@/components/ui/ConfirmDialog";
import api from "@/lib/api";
import {
  Lock,
  Unlock,
  ChevronDown,
  ChevronRight,
  Loader2,
  AlertTriangle,
  Calendar,
} from "lucide-react";

interface Period {
  id: string;
  financial_year_id: string | null;
  name: string;
  start_date: string;
  end_date: string;
  is_open: boolean;
  is_closed: boolean;
}

interface FinancialYear {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  is_closed: boolean;
  periods: Period[];
}

function formatDate(d: string): string {
  if (!d) return "—";
  try {
    return new Intl.DateTimeFormat("en-MY", {
      day: "numeric",
      month: "short",
      year: "numeric",
    }).format(new Date(d + "T00:00:00"));
  } catch {
    return d;
  }
}

function StatusBadge({ isOpen, isClosed }: { isOpen: boolean; isClosed: boolean }) {
  if (isClosed) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-gray-300 bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
        <Lock className="h-3 w-3" />
        Year-End Closed
      </span>
    );
  }
  if (isOpen) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-green-200 bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700">
        <Unlock className="h-3 w-3" />
        Open
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">
      <Lock className="h-3 w-3" />
      Closed
    </span>
  );
}

function YearCard({
  year,
  onClosePeriod,
  onReopenPeriod,
  onYearEndClose,
}: {
  year: FinancialYear;
  onClosePeriod: (p: Period) => void;
  onReopenPeriod: (p: Period) => void;
  onYearEndClose: (year: FinancialYear) => void;
}) {
  const [expanded, setExpanded] = useState(true);
  const allClosed = year.periods.every((p) => !p.is_open || p.is_closed);
  const openCount = year.periods.filter((p) => p.is_open && !p.is_closed).length;

  return (
    <div className="rounded-lg border border-secondary-200 bg-white">
      {/* Year header */}
      <div
        className="flex cursor-pointer items-center justify-between px-4 py-3 hover:bg-secondary-50"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-secondary-400" />
          ) : (
            <ChevronRight className="h-4 w-4 text-secondary-400" />
          )}
          <div>
            <span className="font-semibold text-secondary-900">{year.name}</span>
            <span className="ml-2 text-xs text-secondary-500">
              {formatDate(year.start_date)} – {formatDate(year.end_date)}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {year.is_closed ? (
            <span className="inline-flex items-center gap-1 rounded-full border border-gray-300 bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
              <Lock className="h-3 w-3" />
              Closed
            </span>
          ) : (
            <>
              <span className="text-xs text-secondary-500">
                {openCount} / {year.periods.length} open
              </span>
              {allClosed && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onYearEndClose(year);
                  }}
                  className="rounded-lg bg-primary-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-700"
                >
                  Year-End Close
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {/* Period list */}
      {expanded && (
        <div className="divide-y divide-secondary-100 border-t border-secondary-200">
          {year.periods.map((period) => (
            <div
              key={period.id}
              className="flex items-center justify-between px-4 py-2.5 pl-12"
            >
              <div className="flex items-center gap-3">
                <Calendar className="h-4 w-4 text-secondary-400" />
                <div>
                  <span className="text-sm font-medium text-secondary-900">
                    {period.name}
                  </span>
                  <span className="ml-2 text-xs text-secondary-500">
                    {formatDate(period.start_date)} – {formatDate(period.end_date)}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <StatusBadge
                  isOpen={period.is_open}
                  isClosed={period.is_closed}
                />
                {!period.is_closed && period.is_open && (
                  <button
                    onClick={() => onClosePeriod(period)}
                    className="rounded border border-amber-300 px-2 py-1 text-xs font-medium text-amber-600 hover:bg-amber-50"
                  >
                    Close
                  </button>
                )}
                {!period.is_closed && !period.is_open && (
                  <button
                    onClick={() => onReopenPeriod(period)}
                    className="rounded border border-secondary-300 px-2 py-1 text-xs font-medium text-secondary-600 hover:bg-secondary-50"
                  >
                    Reopen
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function PeriodManagementPage() {
  const { execute } = useAction();

  const {
    data: years,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["financial-years"],
    queryFn: async (): Promise<FinancialYear[]> => {
      const { data } = await api.get("/financial/financial-years/");
      return data;
    },
    staleTime: 10_000,
  });

  const noPeriods = years && years.length === 0;

  const handleInitPeriods = useCallback(async () => {
    await execute({
      confirm: {
        title: "Initialize Periods",
        message:
          "Create a financial year with 12 monthly periods? This is a one-time setup.",
        variant: "info",
        confirmText: "Initialize",
      },
      action: async () => {
        const { data } = await api.post("/financial/init-periods/");
        return data;
      },
      success: {
        title: "Periods Created",
        message: "Financial year with 12 periods has been created.",
        variant: "info",
      },
      onSuccess: () => {
        refetch();
      },
    });
  }, [execute, refetch]);

  const handleClosePeriod = useCallback(
    async (period: Period) => {
      await execute({
        confirm: {
          title: "Close Period",
          message: `Close "${period.name}"? No further postings will be allowed in this period.`,
          variant: "warning",
          confirmText: "Close Period",
        },
        action: async () => {
          const { data } = await api.post(
            `/financial/periods/${period.id}/close/`
          );
          return data;
        },
        success: {
          title: "Period Closed",
          message: `"${period.name}" has been closed.`,
          variant: "info",
        },
        onSuccess: () => {
          refetch();
        },
      });
    },
    [execute, refetch]
  );

  const handleReopenPeriod = useCallback(
    async (period: Period) => {
      await execute({
        confirm: {
          title: "Reopen Period",
          message: `Reopen "${period.name}"? Postings will be allowed again.`,
          variant: "warning",
          confirmText: "Reopen",
        },
        action: async () => {
          const { data } = await api.post(
            `/financial/periods/${period.id}/reopen/`
          );
          return data;
        },
        success: {
          title: "Period Reopened",
          message: `"${period.name}" has been reopened.`,
          variant: "info",
        },
        onSuccess: () => {
          refetch();
        },
      });
    },
    [execute, refetch]
  );

  const handleYearEndClose = useCallback(
    async (year: FinancialYear) => {
    await execute({
        confirm: {
          title: "Year-End Close",
          message: `Close "${year.name}"? This will:\n• Transfer P&L balances to retained earnings\n• Create a new financial year with 12 periods\n• Lock the current year\n\nThis action cannot be reversed.`,
          variant: "danger",
          confirmText: "Close Year",
        },
        action: async () => {
          const { data } = await api.post(
            `/financial/financial-years/${year.id}/year-end-close/`
          );
          return data;
        },
        success: {
          title: "Year-End Close Complete",
          message: `"${year.name}" has been closed. A new financial year has been created.`,
          variant: "info",
        },
        onSuccess: () => {
          refetch();
        },
      });
    },
    [execute, refetch]
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-primary-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <AlertTriangle className="mx-auto h-8 w-8 text-danger-400" />
          <p className="mt-2 text-sm text-danger-600">
            Failed to load financial periods.
          </p>
        </div>
      </div>
    );
  }

  if (noPeriods) {
    return (
      <div className="p-4 md:p-6">
        <div className="mx-auto max-w-md text-center">
          <Calendar className="mx-auto h-12 w-12 text-secondary-300" />
          <h2 className="mt-4 text-lg font-semibold text-secondary-900">
            No Financial Periods
          </h2>
          <p className="mt-1 text-sm text-secondary-500">
            Create a financial year with 12 monthly periods to get started.
          </p>
          <button
            onClick={handleInitPeriods}
            className="mt-4 rounded-lg bg-primary-600 px-6 py-2 text-sm font-medium text-white hover:bg-primary-700"
          >
            Initialize Periods
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-secondary-900">
            Period Management
          </h1>
          <p className="mt-0.5 text-sm text-secondary-500">
            Manage financial periods and year-end close
          </p>
        </div>
        {years && years.length > 0 && (
          <button
            onClick={handleInitPeriods}
            className="rounded-lg border border-secondary-300 px-3 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-50"
          >
            + Add Year
          </button>
        )}
      </div>

      <div className="space-y-3">
        {years?.map((year) => (
          <YearCard
            key={year.id}
            year={year}
            onClosePeriod={handleClosePeriod}
            onReopenPeriod={handleReopenPeriod}
            onYearEndClose={handleYearEndClose}
          />
        ))}
      </div>
    </div>
  );
}
