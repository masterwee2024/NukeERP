import { useState, useEffect, useMemo } from "react";
import api from "@/lib/api";
import type { PageConfigField } from "@/hooks/usePageConfig";

export interface OptionItem {
  label: string;
  value: string;
  group?: string;
}

export function useOptionsResolver(field: PageConfigField): {
  options: OptionItem[];
  loading: boolean;
} {
  const isApi = field.options_source === "api" && !!field.options_api;

  const syncOptions = useMemo<OptionItem[]>(() => {
    if (isApi) return [];
    return (field.options || []).map((opt) => ({
      label: typeof opt === "string" ? opt : String(opt.label ?? ""),
      value: typeof opt === "string" ? opt : String(opt.value ?? ""),
    }));
  }, [field.options, isApi]);

  const [apiOptions, setApiOptions] = useState<OptionItem[]>([]);
  const [loading, setLoading] = useState(isApi);

  useEffect(() => {
    if (!isApi) return;

    let cancelled = false;
    api
      .get(field.options_api)
      .then(({ data }) => {
        if (cancelled) return;
        const labelKey = field.options_label_field || "label";
        const valueKey = field.options_value_field || "value";
        const groupKey = field.option_group_by || "";
        const items: OptionItem[] = (
          Array.isArray(data) ? data : data.results || []
        ).map((item: Record<string, unknown>) => ({
          label: String(item[labelKey] ?? ""),
          value: String(item[valueKey] ?? ""),
          group: groupKey ? String(item[groupKey] ?? "") : undefined,
        }));
        setApiOptions(items);
        setLoading(false);
      })
      .catch(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [
    isApi,
    field.options_api,
    field.options_label_field,
    field.options_value_field,
    field.option_group_by,
  ]);

  return { options: isApi ? apiOptions : syncOptions, loading };
}
