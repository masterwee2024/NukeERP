import { useState, useCallback } from "react";
import { useIsMobile } from "@/hooks/useIsMobile";
import FormPageLayout from "@/components/shared/FormPageLayout";
import { ArrowLeft, Plus, Loader2, Pencil, Trash2 } from "lucide-react";

interface ListCard {
  id: string;
  label: string;
  sublabel?: string;
  badge?: { label: string; color: string };
  meta?: { label: string; value: string }[];
}

interface ActionSlots<T> {
  /** Extra buttons in the detail header */
  detailHeader?: (record: T, refresh: () => void) => React.ReactNode;
  /** Custom content between sections (e.g. sub-lists) */
  betweenSections?: (record: T) => React.ReactNode;
  /** Content at the bottom of the detail view */
  detailFooter?: (record: T) => React.ReactNode;
}

interface DynamicListDetailPageProps<T> {
  title: string;
  /** Convert a record to a card for the list */
  toCard: (record: T) => ListCard;
  /** List of records */
  records: T[];
  /** Loading state */
  isLoading: boolean;
  /** Create a new record */
  onCreate?: () => void;
  /** Edit button handler */
  onEdit?: (record: T) => void;
  /** Delete handler */
  onDelete?: (record: T) => void;
  /** Render the detail view (read-only) */
  renderDetail: (record: T) => React.ReactNode;
  /** Render the create/edit form */
  renderForm?: (record: T | null) => React.ReactNode;
  /** Extra action slots */
  actionSlots?: ActionSlots<T>;
  /** Currently selected record (for external control) */
  selectedRecord?: T | null;
  /** Called when a record is selected */
  onSelect?: (record: T) => void;
  /** Current view state */
  viewState?: "list" | "detail" | "edit" | "create";
  /** Called when view state changes */
  onViewStateChange?: (state: "list" | "detail" | "edit" | "create") => void;
  /** Refresh callback */
  onRefresh?: () => void;
  /** Extra content between the title and the card list */
  listHeader?: React.ReactNode;
}

function DynamicListDetailPage<T extends { id: string }>({
  title,
  toCard,
  records,
  isLoading,
  onCreate,
  onEdit,
  onDelete,
  renderDetail,
  renderForm,
  actionSlots,
  selectedRecord: externalSelected,
  onSelect,
  viewState: externalViewState,
  onViewStateChange,
  onRefresh,
  listHeader,
}: DynamicListDetailPageProps<T>) {
  const isMobile = useIsMobile();

  const [internalSelected, setInternalSelected] = useState<T | null>(null);
  const [internalView, setInternalView] = useState<"list" | "detail" | "edit" | "create">("list");

  const selected = externalSelected ?? internalSelected;
  const view = externalViewState ?? internalView;

  const setView = useCallback(
    (v: "list" | "detail" | "edit" | "create") => {
      if (onViewStateChange) {
        onViewStateChange(v);
      } else {
        setInternalView(v);
      }
    },
    [onViewStateChange],
  );

  const selectRecord = useCallback(
    (record: T) => {
      if (onSelect) {
        onSelect(record);
      } else {
        setInternalSelected(record);
      }
      setView("detail");
    },
    [onSelect, setView],
  );

  const handleCreate = useCallback(() => {
    if (onCreate) onCreate();
    else setView("create");
  }, [onCreate, setView]);

  const handleBack = useCallback(() => {
    if (onSelect) onSelect(null as unknown as T);
    else setInternalSelected(null);
    setView("list");
  }, [onSelect, setView]);

  const refresh = onRefresh ?? (() => {});

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
                key={record.id}
                className="cursor-pointer rounded-lg border border-secondary-200 bg-white p-3"
                onClick={() => selectRecord(record)}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-secondary-900">
                    {card.label}
                  </span>
                  {card.badge && (
                    <span
                      className={`rounded-full px-1.5 py-0.5 text-xs font-medium ${card.badge.color}`}
                    >
                      {card.badge.label}
                    </span>
                  )}
                </div>
                {card.meta && card.meta.length > 0 && (
                  <div className="mt-1 flex items-center gap-2 text-xs text-secondary-500">
                    {card.meta.map((m, i) => (
                      <span key={i}>
                        {m.label}: {m.value}
                      </span>
                    ))}
                  </div>
                )}
                {card.sublabel && (
                  <div className="mt-1 text-xs text-secondary-500">{card.sublabel}</div>
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
          {onEdit && (
            <button
              onClick={() => onEdit(selected)}
              className="inline-flex items-center gap-1 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
            >
              {isMobile && <Pencil className="h-4 w-4" />}
              Edit
            </button>
          )}
          {onDelete && (
            <button
              onClick={() => onDelete(selected)}
              className="inline-flex items-center gap-1 rounded-lg bg-danger-600 px-4 py-2 text-sm font-medium text-white hover:bg-danger-700"
            >
              {isMobile && <Trash2 className="h-4 w-4" />}
              Delete
            </button>
          )}
          {actionSlots?.detailHeader?.(selected, refresh)}
        </div>

        {renderDetail(selected)}

        {actionSlots?.betweenSections?.(selected)}

        {actionSlots?.detailFooter?.(selected)}
      </div>
    );
  }

  function renderFormView() {
    if (!renderForm) return null;
    const isEdit = view === "edit";
    return (
      <div>
        <h2 className="mb-4 text-lg font-semibold text-secondary-900">
          {isEdit ? `Edit ${title}` : `Create ${title}`}
        </h2>
        {renderForm(view === "edit" ? selected : null)}
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
          {onCreate && (
            <button
              onClick={handleCreate}
              className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
            >
              + New
            </button>
          )}
        </div>
        {listHeader}
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

  // Mobile: full-page views with back navigation
  if (isMobile) {
    if (view === "list") {
      return (
        <div className="p-4">
          <div className="mb-4 flex items-center justify-between">
            <h1 className="text-xl font-bold text-secondary-900">{title}</h1>
            {onCreate && (
              <button
                onClick={handleCreate}
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
            onClick={handleBack}
            className="inline-flex items-center gap-1 text-sm font-medium text-secondary-600 hover:text-secondary-900"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
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

  // Desktop: split-pane
  return (
    <div className="p-4 md:p-6 h-[calc(100vh-4rem)]">
      <FormPageLayout
        leftPanel={{
          id: "list",
          label: title,
          content: renderLeftPanel(),
        }}
        rightPanel={{
          id: "detail",
          label: "Detail",
          content: renderRightPanel(),
        }}
      />
    </div>
  );
}

export default DynamicListDetailPage;
