import { useState, useMemo } from "react";
import {
  useApprovalCenter,
  useApprovalCenterStats,
  useQuickApprove,
  useQuickReject,
  useBatchApprove,
  useApprovalContext,
} from "@/hooks/useApprovalCenter";

function ApprovalStatsWidget() {
  const { data: stats, isLoading } = useApprovalCenterStats();

  if (isLoading || !stats) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-24 animate-pulse rounded-lg bg-secondary-100" />
        ))}
      </div>
    );
  }

  const cards = [
    {
      label: "Pending",
      value: stats.total_pending,
      color: "text-yellow-600",
      bg: "bg-yellow-50",
      border: "border-yellow-200",
    },
    {
      label: "Overdue",
      value: stats.overdue_count,
      color: "text-red-600",
      bg: "bg-red-50",
      border: "border-red-200",
    },
    {
      label: "Avg Resolution",
      value: stats.avg_resolution_hours != null ? `${stats.avg_resolution_hours}h` : "—",
      color: "text-blue-600",
      bg: "bg-blue-50",
      border: "border-blue-200",
    },
    {
      label: "Modules",
      value: stats.by_module.length,
      color: "text-green-600",
      bg: "bg-green-50",
      border: "border-green-200",
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <div
          key={card.label}
          className={`rounded-lg border ${card.bg} ${card.border} p-4`}
        >
          <p className="text-xs font-medium uppercase tracking-wide text-secondary-500">
            {card.label}
          </p>
          <p className={`mt-1 text-2xl font-bold ${card.color}`}>{card.value}</p>
        </div>
      ))}
    </div>
  );
}

function ApprovalCard({
  item,
  selected,
  onSelect,
  onSelectToggle,
  onApprove,
  onReject,
  isProcessing,
}: {
  item: {
    execution_id: string;
    document_type: string;
    document_number: string;
    workflow_name: string;
    module: string;
    requester: { name: string } | null;
    created_at: string;
    overdue: boolean;
  };
  selected: boolean;
  onSelect: (id: string) => void;
  onSelectToggle: (id: string) => void;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  isProcessing: boolean;
}) {
  return (
    <div
      className={`rounded-lg border bg-white p-4 transition hover:shadow-md ${
        selected ? "border-primary-500 ring-1 ring-primary-500" : "border-secondary-200"
      } ${item.overdue ? "border-l-4 border-l-red-500" : ""}`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <input
            type="checkbox"
            checked={selected}
            onClick={(e) => e.stopPropagation()}
            onChange={() => onSelectToggle(item.execution_id)}
            className="h-4 w-4 rounded border-secondary-300 text-primary-600"
          />
          <div>
            <p className="font-medium text-secondary-800">{item.workflow_name}</p>
            <p className="text-sm text-secondary-500">
              {item.document_type} — {item.document_number}
            </p>
          </div>
        </div>
        <div className="text-right text-xs text-secondary-400">
          <p>{item.requester?.name || "Unknown"}</p>
          <p>{new Date(item.created_at).toLocaleDateString()}</p>
          {item.overdue && (
            <span className="mt-1 inline-block rounded bg-red-100 px-1.5 py-0.5 text-xs font-medium text-red-700">
              Overdue
            </span>
          )}
        </div>
      </div>

      <div className="mt-3 flex items-center gap-2">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onApprove(item.execution_id);
          }}
          disabled={isProcessing}
          className="rounded bg-green-600 px-3 py-1 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-50"
        >
          Approve
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onReject(item.execution_id);
          }}
          disabled={isProcessing}
          className="rounded bg-red-600 px-3 py-1 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50"
        >
          Reject
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onSelect(item.execution_id);
          }}
          className="rounded bg-secondary-100 px-3 py-1 text-xs font-medium text-secondary-600 hover:bg-secondary-200"
        >
          Details
        </button>
      </div>
    </div>
  );
}

function ApprovalContextPanel({ executionId }: { executionId: string }) {
  const { data: context, isLoading, error } = useApprovalContext(executionId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-500 border-t-transparent" />
      </div>
    );
  }

  if (error || !context) {
    return (
      <div className="p-4 text-center text-sm text-danger-500">
        Failed to load context
      </div>
    );
  }

  const excluded = ["id", "created_at", "updated_at", "version"];

  return (
    <div className="rounded-lg border border-secondary-200 bg-white p-4">
      <div className="mb-4">
        <h3 className="text-base font-semibold text-secondary-800">
          {context.document_type}
        </h3>
        <p className="text-sm text-secondary-500">
          #{context.document_id.slice(0, 8)} &middot; {context.workflow.name}
        </p>
      </div>

      {context.document_data && (
        <div className="mb-4 grid grid-cols-2 gap-3">
          {Object.entries(context.document_data).map(([key, value]) => {
            if (excluded.includes(key)) return null;
            return (
              <div key={key}>
                <dt className="text-xs font-medium uppercase text-secondary-400">
                  {key.replace(/_/g, " ")}
                </dt>
                <dd className="text-sm text-secondary-700">
                  {String(value ?? "—")}
                </dd>
              </div>
            );
          })}
        </div>
      )}

      {context.steps.length > 0 && (
        <div className="border-t border-secondary-100 pt-3">
          <h4 className="mb-2 text-xs font-semibold uppercase text-secondary-500">
            History
          </h4>
          <div className="space-y-2">
            {context.steps.map((step) => (
              <div key={step.step_id} className="flex items-start gap-2 text-xs">
                <span
                  className={`mt-0.5 inline-block h-2 w-2 shrink-0 rounded-full ${
                    step.status === "completed"
                      ? "bg-green-500"
                      : step.status === "skipped"
                        ? "bg-gray-400"
                        : "bg-yellow-400"
                  }`}
                />
                <div>
                  <p className="font-medium text-secondary-700">
                    {step.approver?.name || "Unknown"} &mdash; {step.action}
                  </p>
                  {step.comment && (
                    <p className="text-secondary-500">&ldquo;{step.comment}&rdquo;</p>
                  )}
                  <p className="text-secondary-400">
                    {new Date(step.timestamp).toLocaleString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function ApprovalCenterPage() {
  const { data, isLoading, error } = useApprovalCenter();
  const quickApprove = useQuickApprove();
  const quickReject = useQuickReject();
  const batchApprove = useBatchApprove();

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [focusedId, setFocusedId] = useState<string | null>(null);
  const [filterModule, setFilterModule] = useState("");
  const [filterDocType, setFilterDocType] = useState("");

  const items = data?.results || [];

  const modules = useMemo(
    () => [...new Set(items.map((i) => i.module))],
    [items]
  );
  const docTypes = useMemo(
    () => [...new Set(items.map((i) => i.document_type))],
    [items]
  );

  const filtered = useMemo(
    () =>
      items.filter((i) => {
        if (filterModule && i.module !== filterModule) return false;
        if (filterDocType && i.document_type !== filterDocType) return false;
        return true;
      }),
    [items, filterModule, filterDocType]
  );

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleQuickApprove = async (execution_id: string) => {
    try {
      await quickApprove.mutateAsync({ execution_id });
    } catch {
      /* cancelled or error */
    }
  };

  const handleQuickReject = async (execution_id: string) => {
    const comment = window.prompt("Reason for rejection:");
    if (!comment) return;
    try {
      await quickReject.mutateAsync({ execution_id, comment });
    } catch {
      /* cancelled or error */
    }
  };

  const handleBatchApprove = async () => {
    if (selectedIds.size === 0) return;
    try {
      await batchApprove.mutateAsync({ execution_ids: Array.from(selectedIds) });
      setSelectedIds(new Set());
    } catch {
      /* cancelled or error */
    }
  };

  return (
    <div className="mx-auto max-w-7xl p-4 sm:p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-secondary-800">
          Approval Center
        </h1>
        <p className="mt-1 text-sm text-secondary-500">
          Review and manage all pending approvals
        </p>
      </div>

      <div className="mb-6">
        <ApprovalStatsWidget />
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <select
          value={filterModule}
          onChange={(e) => setFilterModule(e.target.value)}
          className="rounded-md border border-secondary-300 px-3 py-1.5 text-sm focus:border-primary-500 focus:outline-none"
        >
          <option value="">All Modules</option>
          {modules.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>

        <select
          value={filterDocType}
          onChange={(e) => setFilterDocType(e.target.value)}
          className="rounded-md border border-secondary-300 px-3 py-1.5 text-sm focus:border-primary-500 focus:outline-none"
        >
          <option value="">All Document Types</option>
          {docTypes.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>

        {selectedIds.size > 0 && (
          <button
            onClick={handleBatchApprove}
            disabled={batchApprove.isPending}
            className="rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            Approve {selectedIds.size} Selected
          </button>
        )}

        <span className="text-xs text-secondary-400">
          {filtered.length} of {items.length} items
        </span>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center p-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent" />
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-danger-200 bg-danger-50 p-4 text-center text-danger-600">
          Failed to load approvals
        </div>
      )}

      {!isLoading && !error && filtered.length === 0 && (
        <div className="rounded-lg border border-secondary-200 bg-white p-8 text-center text-secondary-500">
          No pending approvals
        </div>
      )}

      {!isLoading && !error && filtered.length > 0 && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="space-y-3 lg:col-span-2">
            {filtered.map((item) => (
              <ApprovalCard
                key={item.execution_id}
                item={item}
                selected={selectedIds.has(item.execution_id)}
                onSelect={setFocusedId}
                onSelectToggle={toggleSelect}
                onApprove={handleQuickApprove}
                onReject={handleQuickReject}
                isProcessing={quickApprove.isPending || quickReject.isPending}
              />
            ))}
          </div>

          {focusedId && (
            <div className="space-y-4">
              <ApprovalContextPanel executionId={focusedId} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
