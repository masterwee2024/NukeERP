import { useState, useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import AccountTreeSelect from "./AccountTreeSelect";
import PeriodRangeSelect from "./PeriodRangeSelect";
import FilterPresetManager from "./FilterPresetManager";

interface ParameterDef {
  id: string;
  key: string;
  label: string;
  param_type: string;
  required: boolean;
  default_value: unknown;
  options_source: string;
  validation: Record<string, unknown>;
  sort_order: number;
}

interface ReportFiltersProps {
  reportCode: string;
  onRun: (filters: Record<string, unknown>) => void;
}

export default function ReportFilters({ reportCode, onRun }: ReportFiltersProps) {
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [mobileOpen, setMobileOpen] = useState(false);

  const { data: params = [] } = useQuery<ParameterDef[]>({
    queryKey: ["report-params", reportCode],
    queryFn: () =>
      api
        .get(`/financial/reports/${reportCode}/parameters/`)
        .then((r) => r.data),
  });

  useEffect(() => {
    const defaults: Record<string, unknown> = {};
    for (const p of params) {
      if (p.default_value !== null && p.default_value !== undefined) {
        defaults[p.key] = p.default_value;
      }
    }
    setValues((prev) => ({ ...defaults, ...prev }));
  }, [params]);

  const setValue = useCallback((key: string, value: unknown) => {
    setValues((prev) => ({ ...prev, [key]: value }));
  }, []);

  const handleApply = () => {
    onRun(values);
  };

  const handleLoadPreset = (preset: Record<string, unknown>) => {
    setValues(preset);
  };

  const renderWidget = (p: ParameterDef) => {
    switch (p.param_type) {
      case "period":
        return (
          <PeriodRangeSelect
            key={p.key}
            label={p.label}
            value={values[p.key] as string}
            onChange={(v) => setValue(p.key, v)}
          />
        );
      case "period_range":
        return (
          <div key={p.key} className="space-y-2">
            <label className="text-sm font-medium text-gray-700">{p.label}</label>
            <div className="flex gap-2">
              <PeriodRangeSelect
                label="From"
                value={values[`${p.key}_from`] as string}
                onChange={(v) => setValue(`${p.key}_from`, v)}
              />
              <PeriodRangeSelect
                label="To"
                value={values[`${p.key}_to`] as string}
                onChange={(v) => setValue(`${p.key}_to`, v)}
              />
            </div>
          </div>
        );
      case "account_tree":
        return (
          <AccountTreeSelect
            key={p.key}
            label={p.label}
            values={(values[p.key] as string[]) || []}
            onChange={(v) => setValue(p.key, v)}
          />
        );
      case "checkbox":
        return (
          <label key={p.key} className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={!!values[p.key]}
              onChange={(e) => setValue(p.key, e.target.checked)}
              className="rounded border-gray-300"
            />
            {p.label}
          </label>
        );
      case "select":
        return (
          <div key={p.key} className="space-y-1">
            <label className="text-sm font-medium text-gray-700">{p.label}</label>
            <select
              value={(values[p.key] as string) || ""}
              onChange={(e) => setValue(p.key, e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">Select...</option>
              {(p.options_source || "").split(",").map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </div>
        );
      default:
        return (
          <div key={p.key} className="space-y-1">
            <label className="text-sm font-medium text-gray-700">{p.label}</label>
            <input
              type="text"
              value={(values[p.key] as string) || ""}
              onChange={(e) => setValue(p.key, e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
        );
    }
  };

  return (
    <div className="rounded-lg border bg-white p-4">
      {/* Mobile toggle */}
      <button
        className="mb-2 flex items-center gap-2 text-sm font-medium text-primary-600 md:hidden"
        onClick={() => setMobileOpen(!mobileOpen)}
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
        </svg>
        Filters
      </button>

      <div className={`space-y-3 ${mobileOpen ? "block" : "hidden"} md:block`}>
        {params.map(renderWidget)}

        <div className="flex flex-wrap gap-2 pt-2">
          <button
            onClick={handleApply}
            className="rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
          >
            Apply Filters
          </button>
          <FilterPresetManager
            reportCode={reportCode}
            currentValues={values}
            onLoad={handleLoadPreset}
          />
        </div>
      </div>
    </div>
  );
}
