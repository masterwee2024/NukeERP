import { useSearchParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useIsMobile } from "@/hooks/useIsMobile";
import { usePageConfig } from "@/hooks/usePageConfig";
import { useConfirm } from "@/components/ui/ConfirmDialog";
import FormPageLayout from "@/components/shared/FormPageLayout";
import DynamicDetailPage from "@/components/dynamic/DynamicDetailPage";
import DynamicFormPage from "@/components/dynamic/DynamicFormPage";
import api from "@/lib/api";
import { ArrowLeft, Plus, Loader2, Pencil, Trash2 } from "lucide-react";

interface ActionSlots {
  detailHeader?: (
    record: Record<string, unknown>,
    refresh: () => void
  ) => React.ReactNode;
  betweenSections?: (record: Record<string, unknown>) => React.ReactNode;
  detailFooter?: (record: Record<string, unknown>) => React.ReactNode;
}

interface Props {
  /** Page config key (e.g. "admin.users") */
  configKey: string;
  /** Override page title */
  title?: string;
  /** Extra action slots */
  actionSlots?: ActionSlots;
}

export default function DynamicListDetailPage({
  configKey,
  title: titleProp,
  actionSlots,
}: Props) {
  const isMobile = useIsMobile();
  const queryClient = useQueryClient();
  const { confirm } = useConfirm();

  const [searchParams, setSearchParams] = useSearchParams();
  const selectedId = searchParams.get("id");
  const view = (searchParams.get("view") || "list") as
    | "list"
    | "detail"
    | "edit"
    | "create";

  const navigate = (
    v: "list" | "detail" | "edit" | "create",
    id: string | null = null
  ) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set("view", v);
      if (id) {
        next.set("id", id);
      } else {
        next.delete("id");
      }
      if (v === "list" || v === "create") {
        next.delete("id");
      }
      return next;
    });
  };

  // Fetch page config
  const { data: config, isLoading: configLoading } = usePageConfig(configKey);

  // Flatten custom_fields into records
  function mergeCustom(rec: Record<string, unknown>): Record<string, unknown> {
    return {
      ...((rec.custom_fields as Record<string, unknown>) ?? {}),
      ...rec,
      custom_fields: undefined,
    };
  }

  // Fetch records
  const endpoint = config ? `/${config.api_endpoint}/` : "";
  const { data: rawData, isLoading: recordsLoading } = useQuery({
    queryKey: [config?.api_endpoint],
    queryFn: async (): Promise<Record<string, unknown>[]> => {
      const { data: res } = await api.get(endpoint);
      const list: Record<string, unknown>[] = res?.results ?? res ?? [];
      return list.map(mergeCustom);
    },
    enabled: !!config,
  });
  const records: Record<string, unknown>[] = rawData ?? [];

  // Delete mutation (config-driven)
  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`${endpoint}${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [config?.api_endpoint] });
      navigate("list");
    },
  });

  const title = titleProp ?? config?.page_title ?? "Records";
  const selected = records.find((r) => String(r.id) === selectedId) ?? null;
  const isLoading = configLoading || recordsLoading;
  const hasAction = (label: string) =>
    config?.actions?.some((a) => a.label.toLowerCase() === label.toLowerCase());
  const hasCreate = hasAction("create");
  const hasEdit = hasAction("edit");
  const hasDelete = hasAction("delete");

  // Fetch detail record for actionSlots (contains nested data like company_assignments)
  const { data: detailRecord } = useQuery({
    queryKey: [config?.api_endpoint, selectedId],
    queryFn: async (): Promise<Record<string, unknown>> => {
      const { data } = await api.get(`${endpoint}${selectedId}/`);
      return mergeCustom(data);
    },
    enabled: !!config && !!selectedId && view === "detail",
  });

  // ── Helpers ───────────────────────────────────────

  const columnFields = (config?.fields.filter((f) => f.is_column) ?? []).sort(
    (a, b) => a.column_order - b.column_order
  );

  function toCard(record: Record<string, unknown>) {
    const cols = columnFields.map((f) => ({
      name: f.field_name,
      val: String(record[f.field_name] ?? ""),
      type: f.field_type,
    }));
    const label = cols[0]?.val || String(record.id);
    const meta = cols.slice(1);
    return {
      id: String(record.id),
      label,
      meta,
    };
  }

  async function handleDelete(record: Record<string, unknown>) {
    const ok = await confirm({
      title: "Delete",
      message: `Delete this ${title}?`,
      variant: "danger",
      confirmText: "Delete",
    });
    if (ok) deleteMutation.mutate(String(record.id));
  }

  const refresh = () =>
    queryClient.invalidateQueries({ queryKey: [config?.api_endpoint] });

  // ── Render ────────────────────────────────────────

  function renderListView() {
    return (
      <div className="space-y-2">
        {records.length === 0 ? (
          <div className="py-8 text-center text-sm text-secondary-500">
            No {title.toLowerCase()} found.
          </div>
        ) : (
          records.map((record) => {
            const card = toCard(record);
            return (
              <div
                key={card.id}
                className="cursor-pointer rounded-lg border border-secondary-200 bg-white p-3"
                onClick={() => {
                  navigate("detail", card.id);
                }}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-secondary-900">
                    {card.label}
                  </span>
                </div>
                {card.meta.length > 0 && (
                  <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-secondary-500">
                    {card.meta.map((m, i) => (
                      <span key={i} className="inline-flex items-center gap-1">
                        {m.type === "badge" ? (
                          <span className="rounded-full bg-secondary-100 px-1.5 py-0.5 text-secondary-600">
                            {m.val}
                          </span>
                        ) : (
                          <span>{m.val || "\u2014"}</span>
                        )}
                        {i < card.meta.length - 1 && (
                          <span className="text-secondary-300">|</span>
                        )}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    );
  }

  function renderDetailView() {
    if (!selected) {
      return (
        <div className="flex h-48 items-center justify-center text-sm text-secondary-400">
          Select a record to view
        </div>
      );
    }
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          {hasEdit && (
            <button
              onClick={() => navigate("edit", selectedId)}
              className="inline-flex items-center gap-1 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
            >
              {isMobile && <Pencil className="h-4 w-4" />} Edit
            </button>
          )}
          {hasDelete && (
            <button
              onClick={() => handleDelete(selected)}
              className="inline-flex items-center gap-1 rounded-lg bg-danger-600 px-4 py-2 text-sm font-medium text-white hover:bg-danger-700"
            >
              {isMobile && <Trash2 className="h-4 w-4" />} Delete
            </button>
          )}
          {actionSlots?.detailHeader?.(detailRecord ?? selected, refresh)}
        </div>
        <DynamicDetailPage config={config!} recordId={String(selected.id)} />
        {actionSlots?.betweenSections?.(detailRecord ?? selected)}
        {actionSlots?.detailFooter?.(detailRecord ?? selected)}
      </div>
    );
  }

  function renderFormView() {
    if (view === "create") {
      return (
        <div>
          <h2 className="mb-4 text-lg font-semibold text-secondary-900">New {title}</h2>
          <DynamicFormPage config={config!} />
        </div>
      );
    }
    return (
      <div>
        <h2 className="mb-4 text-lg font-semibold text-secondary-900">Edit {title}</h2>
        <DynamicFormPage config={config!} recordId={selectedId ?? undefined} />
      </div>
    );
  }

  function renderRightPanel() {
    switch (view) {
      case "create":
      case "edit":
        return renderFormView();
      case "detail":
        return renderDetailView();
      default:
        return (
          <div className="flex h-48 items-center justify-center text-sm text-secondary-400">
            Select a record to view
          </div>
        );
    }
  }

  function renderLeftPanel() {
    return (
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h1 className="text-xl font-bold text-secondary-900">{title}</h1>
          {hasCreate && (
            <button
              onClick={() => navigate("create")}
              className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
            >
              + New
            </button>
          )}
        </div>
        {renderListView()}
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex h-48 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
      </div>
    );
  }

  if (isMobile) {
    if (view === "list") {
      return (
        <div className="p-4">
          <div className="mb-4 flex items-center justify-between">
            <h1 className="text-xl font-bold text-secondary-900">{title}</h1>
            {hasCreate && (
              <button
                onClick={() => navigate("create")}
                className="inline-flex items-center justify-center rounded-lg bg-primary-600 p-2 text-white hover:bg-primary-700"
              >
                <Plus className="h-5 w-5" />
              </button>
            )}
          </div>
          {renderListView()}
        </div>
      );
    }
    return (
      <div className="p-4">
        <div className="mb-4 flex items-center gap-2">
          <button
            onClick={() => {
              navigate("list");
            }}
            className="inline-flex items-center gap-1 text-sm font-medium text-secondary-600 hover:text-secondary-900"
          >
            <ArrowLeft className="h-4 w-4" /> Back
          </button>
          <h1 className="text-lg font-bold text-secondary-900">
            {view === "create"
              ? `New ${title}`
              : view === "edit"
                ? `Edit ${title}`
                : "Detail"}
          </h1>
        </div>
        {renderRightPanel()}
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 h-[calc(100vh-4rem)]">
      <FormPageLayout
        leftPanel={{ id: "list", label: title, content: renderLeftPanel() }}
        rightPanel={{
          id: "detail",
          label: "Detail",
          content: renderRightPanel(),
        }}
      />
    </div>
  );
}
