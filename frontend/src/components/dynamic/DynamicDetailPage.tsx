import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { PageConfig } from "@/hooks/usePageConfig";
import { useViewport } from "@/hooks/useViewport";
import { useConfirm } from "@/components/ui/ConfirmDialog";

interface DynamicDetailPageProps {
  config: PageConfig;
  recordId?: string;
}

export default function DynamicDetailPage({ config, recordId }: DynamicDetailPageProps) {
  const queryClient = useQueryClient();
  const { confirm } = useConfirm();
  const { isMobile } = useViewport();

  const actionMutation = useMutation({
    mutationFn: async ({ endpoint, method }: { endpoint: string; method: string }) => {
      const url = endpoint.replace(":id", recordId || "");
      if (method.toLowerCase() === "post") {
        const { data } = await api.post(url);
        return data;
      }
      const { data } = await api.put(url);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [config.api_endpoint] });
    },
  });

  const { data: record, isLoading } = useQuery({
    queryKey: [config.api_endpoint, recordId],
    queryFn: async () => {
      const { data } = await api.get(`/${config.api_endpoint}${recordId}/`);
      return data as Record<string, unknown>;
    },
    enabled: !!recordId,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-secondary-200 border-t-primary-600" />
      </div>
    );
  }

  if (!record) {
    return (
      <div className="rounded-md border border-warning-200 bg-warning-50 p-4 text-sm text-warning-700">
        Record not found
      </div>
    );
  }

  const displayFields = config.fields.filter((f) => {
    if (isMobile && !f.show_on_mobile) return false;
    if (!isMobile && !f.show_on_desktop) return false;
    return !f.hidden;
  });

  const grouped = groupFields(displayFields);
  const actionButtons = config.actions;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-secondary-900">{config.page_title}</h2>
        <div className="flex gap-2">
          {actionButtons.map((action) => (
            <button
              key={action.label}
              type="button"
              disabled={actionMutation.isPending}
              onClick={async () => {
                if (action.confirm !== false) {
                  const confirmed = await confirm({
                    title: action.label,
                    message: `Are you sure you want to ${action.label.toLowerCase()}?`,
                    variant: (action.variant as "danger" | "warning" | "info") || "info",
                  });
                  if (!confirmed) return;
                }
                actionMutation.mutate({ endpoint: action.endpoint, method: action.method });
              }}
              className={`rounded-md px-4 py-2 text-sm font-medium ${
                action.variant === "danger"
                  ? "bg-danger-600 text-white hover:bg-danger-700"
                  : action.variant === "warning"
                  ? "bg-warning-600 text-white hover:bg-warning-700"
                  : "bg-primary-600 text-white hover:bg-primary-700"
              } ${actionMutation.isPending ? "opacity-50 cursor-not-allowed" : ""}`}
            >
              {actionMutation.isPending ? "Processing..." : action.label}
            </button>
          ))}
        </div>
      </div>

      {Object.entries(grouped).map(([groupName, fields]) => (
        <div
          key={groupName}
          className="rounded-md border border-secondary-200 bg-white"
        >
          {groupName !== "_ungrouped" && (
            <div className="border-b border-secondary-100 px-4 py-3">
              <h4 className="text-sm font-semibold text-secondary-800">{groupName}</h4>
            </div>
          )}
          <div className={`grid grid-cols-1 gap-4 p-4 sm:grid-cols-2 lg:grid-cols-3`}>
            {fields.map((field) => (
              <DetailField
                key={field.field_name}
                label={field.label}
                value={record[field.field_name]}
                fieldType={field.field_type}
                prefix={field.prefix}
                badgeColor={field.badge_color}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function DetailField({
  label,
  value,
  fieldType,
  prefix,
  badgeColor,
}: {
  label: string;
  value: unknown;
  fieldType: string;
  prefix?: string;
  badgeColor?: Record<string, string>;
}) {
  if (fieldType === "heading" || fieldType === "separator" || fieldType === "spacer") {
    return null;
  }

  const strVal = value === null || value === undefined ? "—" : String(value);

  if (fieldType === "badge") {
    const colorClass = badgeColor?.[strVal] || "bg-secondary-100 text-secondary-700";
    return (
      <div className="space-y-1">
        <label className="block text-xs font-medium text-secondary-500">{label}</label>
        <span
          className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${colorClass}`}
        >
          {strVal}
        </span>
      </div>
    );
  }

  if (fieldType === "currency") {
    const num = Number(value);
    const display = isNaN(num) ? strVal : `${prefix || "RM"} ${num.toFixed(2)}`;
    return (
      <div className="space-y-1">
        <label className="block text-xs font-medium text-secondary-500">{label}</label>
        <p className="text-sm font-medium text-secondary-900">{display}</p>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <label className="block text-xs font-medium text-secondary-500">{label}</label>
      <p className="text-sm text-secondary-800">{strVal}</p>
    </div>
  );
}

function groupFields<T extends { field_name: string; group_name: string }>(
  fields: T[]
) {
  const groups: Record<string, T[]> = {};
  for (const f of fields) {
    const key = f.group_name || "_ungrouped";
    if (!groups[key]) groups[key] = [];
    groups[key].push(f);
  }
  return groups;
}
