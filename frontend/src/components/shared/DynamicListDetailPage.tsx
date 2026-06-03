import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useIsMobile } from "@/hooks/useIsMobile";
import { usePageConfig } from "@/hooks/usePageConfig";
import { useConfirm } from "@/components/ui/ConfirmDialog";
import FormPageLayout from "@/components/shared/FormPageLayout";
import DynamicDetailPage from "@/components/dynamic/DynamicDetailPage";
import DynamicFormPage from "@/components/dynamic/DynamicFormPage";
import api from "@/lib/api";
import { ArrowLeft, Plus, Loader2, Pencil, Trash2 } from "lucide-react";

interface ListCard {
  id: string;
  label: string;
  sublabel?: string;
  badge?: { label: string; color: string };
  meta?: { label: string; value: string }[];
}

interface ActionSlots<T> {
  detailHeader?: (record: T, refresh: () => void) => React.ReactNode;
  betweenSections?: (record: T) => React.ReactNode;
  detailFooter?: (record: T) => React.ReactNode;
}

interface DynamicListDetailPageProps<T> {
  title?: string;
  /** Page config key for DB-driven rendering. When set, renderDetail/renderForm are optional. */
  configKey?: string;
  /** Required when configKey not set */
  toCard?: (record: T) => ListCard;
  records?: T[];
  isLoading?: boolean;
  onCreate?: () => void;
  onEdit?: (record: T) => void;
  onDelete?: (record: T) => void;
  renderDetail?: (record: T) => React.ReactNode;
  renderForm?: (record: T | null) => React.ReactNode;
  actionSlots?: ActionSlots<T>;
  selectedRecord?: T | null;
  onSelect?: (record: T) => void;
  viewState?: "list" | "detail" | "edit" | "create";
  onViewStateChange?: (state: "list" | "detail" | "edit" | "create") => void;
  onRefresh?: () => void;
  listHeader?: React.ReactNode;
}

function DynamicListDetailPage<T extends { id: string }>({
  title: titleProp,
  configKey,
  toCard: toCardProp,
  records: recordsProp,
  isLoading: isLoadingProp,
  onCreate,
  onEdit,
  onDelete,
  renderDetail: renderDetailProp,
  renderForm: renderFormProp,
  actionSlots,
  selectedRecord: externalSelected,
  onSelect,
  viewState: externalViewState,
  onViewStateChange,
  onRefresh,
  listHeader: listHeaderProp,
}: DynamicListDetailPageProps<T>) {
  const isMobile = useIsMobile();
  const queryClient = useQueryClient();
  const { confirm } = useConfirm();

  // State (defined before any conditional hooks)
  const [internalSelected, setInternalSelected] = useState<T | null>(null);
  const [internalView, setInternalView] = useState<"list" | "detail" | "edit" | "create">("list");

  const selected = externalSelected ?? internalSelected;
  const view = externalViewState ?? internalView;

  const setView = useCallback(
    (v: "list" | "detail" | "edit" | "create") => {
      if (onViewStateChange) onViewStateChange(v);
      else setInternalView(v);
    },
    [onViewStateChange],
  );

  const selectRecord = useCallback(
    (record: T) => {
      if (onSelect) onSelect(record);
      else setInternalSelected(record);
      setView("detail");
    },
    [onSelect, setView],
  );

  const handleBack = useCallback(() => {
    if (onSelect) onSelect(null as unknown as T);
    else setInternalSelected(null);
    setView("list");
  }, [onSelect, setView]);

  // Config-driven mode
  const { data: config, isLoading: configLoading } = usePageConfig(configKey || "");
  const listEndpoint = config ? `/${config.api_endpoint}/` : "";
  const { data: configRecords, isLoading: recordsLoading } = useQuery({
    queryKey: [config?.api_endpoint],
    queryFn: async (): Promise<T[]> => {
      const { data } = await api.get(listEndpoint);
      return data?.results ?? data ?? [];
    },
    enabled: !!config,
  });
  const deleteMutation = useMutation({
    mutationFn: async (id: string) => { await api.delete(`${listEndpoint}${id}/`); },
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: [config?.api_endpoint] }); setInternalSelected(null); setView("list"); },
  });

  // Auto-derive card fields from config
  const autoToCard = useCallback((record: T): ListCard => {
    const r = record as Record<string, unknown>;
    const labelField = config?.fields.find((f) => f.is_column)?.field_name || "id";
    return {
      id: String(r.id),
      label: String(r[labelField] ?? r.id),
      meta: config?.fields
        .filter((f) => f.is_column && f.field_name !== labelField)
        .slice(0, 3)
        .map((f) => ({ label: f.label, value: String(r[f.field_name] ?? "") })) || [],
    };
  }, [config]);

  const usingConfig = !!(configKey && config);
  const title = titleProp ?? config?.page_title ?? "Records";
  const resolvedRecords = (usingConfig ? (configRecords as T[]) : recordsProp) ?? [];
  const resolvedLoading = usingConfig ? (configLoading || recordsLoading) : (isLoadingProp ?? false);
  const resolvedToCard = usingConfig ? autoToCard : (toCardProp ?? ((r: T): ListCard => ({ id: String(r.id), label: String(r.id) })));
  const resolvedRenderDetail = usingConfig
    ? (record: T) => <DynamicDetailPage config={config!} recordId={String(record.id)} />
    : (renderDetailProp ?? (() => null));
  const resolvedRenderForm = usingConfig
    ? (record: T | null) => <DynamicFormPage config={config!} recordId={record ? String(record.id) : undefined} />
    : renderFormProp;
  const resolvedOnCreate = usingConfig ? (() => setView("create")) : onCreate;
  const resolvedOnEdit = usingConfig ? ((record: T) => { setInternalSelected(record); setView("edit"); }) : onEdit;
  const resolvedOnDelete = usingConfig
    ? async (record: T) => {
        const ok = await confirm({ title: "Delete", message: `Delete this ${title}?`, variant: "danger", confirmText: "Delete" });
        if (ok) deleteMutation.mutate(record.id);
      }
    : onDelete;
  const resolvedListHeader = usingConfig ? null : listHeaderProp;
  const refresh = onRefresh ?? (() => { queryClient.invalidateQueries({ queryKey: [config?.api_endpoint] }); });

  // ── Render functions ───────────────────────────────────

  function renderListView() {
    return (
      <div className="space-y-2">
        {resolvedRecords.length === 0 ? (
          <div className="py-8 text-center text-sm text-secondary-500">No {title.toLowerCase()} found.</div>
        ) : (
          resolvedRecords.map((record) => {
            const card = resolvedToCard(record);
            return (
              <div
                key={record.id}
                className="cursor-pointer rounded-lg border border-secondary-200 bg-white p-3"
                onClick={() => selectRecord(record)}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-secondary-900">{card.label}</span>
                  {card.badge && (
                    <span className={`rounded-full px-1.5 py-0.5 text-xs font-medium ${card.badge.color}`}>
                      {card.badge.label}
                    </span>
                  )}
                </div>
                {card.sublabel && <div className="mt-1 text-xs text-secondary-500">{card.sublabel}</div>}
                {card.meta && card.meta.length > 0 && (
                  <div className="mt-1 flex items-center gap-2 text-xs text-secondary-500">
                    {card.meta.map((m, i) => (
                      <span key={i}>{m.label ? `${m.label}: ${m.value}` : m.value}</span>
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
      return <div className="flex h-48 items-center justify-center text-sm text-secondary-400">Select a record to view</div>;
    }
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          {resolvedOnEdit && (
            <button onClick={() => resolvedOnEdit(selected)}
              className="inline-flex items-center gap-1 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700">
              {isMobile && <Pencil className="h-4 w-4" />} Edit
            </button>
          )}
          {resolvedOnDelete && (
            <button onClick={() => resolvedOnDelete(selected)}
              className="inline-flex items-center gap-1 rounded-lg bg-danger-600 px-4 py-2 text-sm font-medium text-white hover:bg-danger-700">
              {isMobile && <Trash2 className="h-4 w-4" />} Delete
            </button>
          )}
          {actionSlots?.detailHeader?.(selected, refresh)}
        </div>
        {resolvedRenderDetail(selected)}
        {actionSlots?.betweenSections?.(selected)}
        {actionSlots?.detailFooter?.(selected)}
      </div>
    );
  }

  function renderFormView() {
    if (!resolvedRenderForm) return null;
    const isEdit = view === "edit";
    return (
      <div>
        <h2 className="mb-4 text-lg font-semibold text-secondary-900">
          {isEdit ? `Edit ${title}` : `Create ${title}`}
        </h2>
        {resolvedRenderForm(isEdit ? selected : null)}
      </div>
    );
  }

  function renderRightPanel() {
    switch (view) {
      case "create": case "edit": return renderFormView();
      case "detail": return renderDetailView();
      default: return <div className="flex h-48 items-center justify-center text-sm text-secondary-400">Select a record to view</div>;
    }
  }

  function renderLeftPanel() {
    return (
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h1 className="text-xl font-bold text-secondary-900">{title}</h1>
          {resolvedOnCreate && (
            <button onClick={resolvedOnCreate}
              className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700">
              + New
            </button>
          )}
        </div>
        {resolvedListHeader}
        {renderListView()}
      </div>
    );
  }

  if (resolvedLoading) {
    return <div className="flex h-48 items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-primary-500" /></div>;
  }

  // Mobile
  if (isMobile) {
    if (view === "list") {
      return (
        <div className="p-4">
          <div className="mb-4 flex items-center justify-between">
            <h1 className="text-xl font-bold text-secondary-900">{title}</h1>
            {resolvedOnCreate && (
              <button onClick={resolvedOnCreate}
                className="inline-flex items-center justify-center rounded-lg bg-primary-600 p-2 text-white hover:bg-primary-700">
                <Plus className="h-5 w-5" />
              </button>
            )}
          </div>
          {resolvedListHeader}
          {renderListView()}
        </div>
      );
    }
    return (
      <div className="p-4">
        <div className="mb-4 flex items-center gap-2">
          <button onClick={handleBack}
            className="inline-flex items-center gap-1 text-sm font-medium text-secondary-600 hover:text-secondary-900">
            <ArrowLeft className="h-4 w-4" /> Back
          </button>
          <h1 className="text-lg font-bold text-secondary-900">
            {view === "create" ? `New ${title}` : view === "edit" ? `Edit ${title}` : "Detail"}
          </h1>
        </div>
        {renderRightPanel()}
      </div>
    );
  }

  // Desktop
  return (
    <div className="p-4 md:p-6 h-[calc(100vh-4rem)]">
      <FormPageLayout
        leftPanel={{ id: "list", label: title, content: renderLeftPanel() }}
        rightPanel={{ id: "detail", label: "Detail", content: renderRightPanel() }}
      />
    </div>
  );
}

export default DynamicListDetailPage;
