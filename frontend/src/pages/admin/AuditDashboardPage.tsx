import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

// ── Types ──

interface DashboardData {
  total_changes: number;
  period_days: number;
  by_category: Array<{ category: string; count: number; percentage: number }>;
  by_user: Array<{ email: string; full_name: string; count: number }>;
  by_model: Array<{ model_name: string; count: number }>;
  daily_trend: Array<{ date: string; count: number }>;
}

const PERIOD_OPTIONS = [
  { value: 7, label: "7 days" },
  { value: 30, label: "30 days" },
  { value: 90, label: "90 days" },
  { value: 365, label: "365 days" },
] as const;

// ── Helpers ──

function maxCount(items: Array<{ count: number }>): number {
  return Math.max(...items.map((i) => i.count), 1);
}

function barWidth(count: number, max: number): string {
  const pct = (count / max) * 100;
  return `${Math.max(pct, 2)}%`;
}

// ── Component ──

export default function AuditDashboardPage() {
  const [periodDays, setPeriodDays] = useState<number>(30);

  const {
    data: dashboard,
    isLoading,
    error,
  } = useQuery<DashboardData>({
    queryKey: ["audit-dashboard", periodDays],
    queryFn: async () => {
      const { data } = await api.get("/core/admin/audit-logs/dashboard/", {
        params: { period_days: periodDays },
      });
      return data;
    },
    staleTime: 30 * 1000,
  });

  if (isLoading) {
    return (
      <div className="mx-auto max-w-6xl p-4 md:p-6">
        <div className="mb-4 rounded-lg bg-secondary-50 p-3 text-sm text-secondary-600">
          Loading dashboard...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-6xl p-4 md:p-6">
        <div className="mb-4 rounded-lg bg-danger-50 p-3 text-sm text-danger-700">
          Failed to load dashboard:{" "}
          {(error as { response?: { data?: { detail?: string } } })?.response?.data
            ?.detail || "Check server logs"}
        </div>
      </div>
    );
  }

  const userMax = dashboard ? maxCount(dashboard.by_user) : 1;
  const modelMax = dashboard ? maxCount(dashboard.by_model) : 1;
  const trendMax = dashboard ? maxCount(dashboard.daily_trend) : 1;

  return (
    <div className="mx-auto max-w-6xl p-4 md:p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-secondary-900 md:text-2xl">
          Audit Dashboard
        </h1>
        <select
          value={periodDays}
          onChange={(e) => setPeriodDays(Number(e.target.value))}
          className="rounded-lg border border-secondary-300 px-3 py-2 text-sm text-secondary-700 focus:border-primary-500 focus:outline-none"
        >
          {PERIOD_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* KPI Cards */}
      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        {/* Total Changes */}
        <div className="rounded-lg border border-secondary-200 bg-white p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-secondary-500">
            Total Changes
          </p>
          <p className="mt-1 text-2xl font-bold text-secondary-900">
            {dashboard?.total_changes.toLocaleString()}
          </p>
          <p className="mt-0.5 text-xs text-secondary-400">
            Last {dashboard?.period_days} days
          </p>
        </div>

        {/* By Category */}
        {dashboard?.by_category.map((cat) => (
          <div
            key={cat.category}
            className="rounded-lg border border-secondary-200 bg-white p-4"
          >
            <p className="text-xs font-medium uppercase tracking-wide text-secondary-500">
              {cat.category}
            </p>
            <p className="mt-1 text-2xl font-bold text-secondary-900">
              {cat.count.toLocaleString()}
            </p>
            <p className="mt-0.5 text-xs text-secondary-400">
              {cat.percentage.toFixed(1)}% of total
            </p>
          </div>
        ))}
      </div>

      {/* By User & By Model — side by side on desktop */}
      <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* By User */}
        <div className="rounded-lg border border-secondary-200 bg-white p-4">
          <h2 className="mb-3 text-sm font-semibold text-secondary-900">
            Top Users
          </h2>
          <div className="space-y-2">
            {dashboard?.by_user.map((user) => (
              <div key={user.email} className="flex items-center gap-3">
                <span className="w-8 text-right text-xs text-secondary-400">
                  {user.count}
                </span>
                <div className="flex-1">
                  <div
                    className="h-5 rounded bg-primary-200"
                    style={{ width: barWidth(user.count, userMax) }}
                  />
                </div>
                <span className="w-32 truncate text-right text-xs text-secondary-700">
                  {user.full_name || user.email}
                </span>
              </div>
            ))}
            {(!dashboard?.by_user || dashboard.by_user.length === 0) && (
              <p className="text-sm text-secondary-500">No user data.</p>
            )}
          </div>
        </div>

        {/* By Model */}
        <div className="rounded-lg border border-secondary-200 bg-white p-4">
          <h2 className="mb-3 text-sm font-semibold text-secondary-900">
            Top Models
          </h2>
          <div className="space-y-2">
            {dashboard?.by_model.map((m) => (
              <div key={m.model_name} className="flex items-center gap-3">
                <span className="w-8 text-right text-xs text-secondary-400">
                  {m.count}
                </span>
                <div className="flex-1">
                  <div
                    className="h-5 rounded bg-success-500"
                    style={{ width: barWidth(m.count, modelMax) }}
                  />
                </div>
                <span className="w-40 truncate text-right text-xs text-secondary-700">
                  {m.model_name}
                </span>
              </div>
            ))}
            {(!dashboard?.by_model || dashboard.by_model.length === 0) && (
              <p className="text-sm text-secondary-500">No model data.</p>
            )}
          </div>
        </div>
      </div>

      {/* Daily Trend */}
      <div className="rounded-lg border border-secondary-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-secondary-900">
          Daily Trend
        </h2>
        {dashboard?.daily_trend && dashboard.daily_trend.length > 0 ? (
          <div className="flex items-end gap-[2px] overflow-x-auto">
            {dashboard.daily_trend.map((day) => (
              <div
                key={day.date}
                className="flex shrink-0 flex-col items-center"
                title={`${day.date}: ${day.count}`}
              >
                <div
                  className="w-3 rounded-t bg-primary-500"
                  style={{
                    height: `${(day.count / trendMax) * 120}px`,
                    minHeight: day.count > 0 ? "4px" : "0px",
                  }}
                />
                <span className="mt-1 text-[10px] text-secondary-400">
                  {day.date.slice(5)}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-secondary-500">No trend data available.</p>
        )}
      </div>
    </div>
  );
}
