import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  useApproval,
  useExecutionContext,
  usePendingApprovals,
} from "@/hooks/useApproval";
import { ApprovalPanel } from "./ApprovalPanel";

interface ApprovalPageProps {
  currentUserId: string;
}

export function ApprovalPage({ currentUserId }: ApprovalPageProps) {
  const { executionId } = useParams<{ executionId: string }>();
  const [activeTab, setActiveTab] = useState<"approval" | "history">("approval");

  const { data: context, isLoading, error } = useExecutionContext(executionId);
  const { data: pendingData } = usePendingApprovals();
  const { delegate, isPending } = useApproval();
  const [delegateUserId, setDelegateUserId] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  if (!executionId) {
    return (
      <div className="p-6">
        <h1 className="mb-6 text-2xl font-bold text-secondary-800">Approval Center</h1>
        <PendingList items={pendingData?.results || []} />
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent" />
      </div>
    );
  }

  if (error || !context) {
    return (
      <div className="p-6 text-center text-danger-500">
        Failed to load approval context.
      </div>
    );
  }

  const handleDelegate = async () => {
    if (!delegateUserId) {
      setErrorMsg("Please select a user to delegate to");
      return;
    }
    setErrorMsg("");
    try {
      await delegate({
        execution_id: context.execution_id,
        delegated_to_id: delegateUserId,
      });
      setDelegateUserId("");
    } catch {
      setErrorMsg("Failed to delegate");
    }
  };

  return (
    <div className="mx-auto max-w-5xl p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-secondary-800">
          Approval: {context.document_type}
        </h1>
        <p className="mt-1 text-sm text-secondary-500">
          Document #{context.document_id.slice(0, 8)}
          {" · "}
          {context.workflow.name}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="mb-4 border-b border-secondary-200">
            <button
              onClick={() => setActiveTab("approval")}
              className={`mr-4 border-b-2 px-1 pb-2 text-sm font-medium ${
                activeTab === "approval"
                  ? "border-primary-500 text-primary-600"
                  : "border-transparent text-secondary-500 hover:text-secondary-700"
              }`}
            >
              Document Details
            </button>
            <button
              onClick={() => setActiveTab("history")}
              className={`mr-4 border-b-2 px-1 pb-2 text-sm font-medium ${
                activeTab === "history"
                  ? "border-primary-500 text-primary-600"
                  : "border-transparent text-secondary-500 hover:text-secondary-700"
              }`}
            >
              Approval History
            </button>
          </div>

          {activeTab === "approval" && (
            <div className="rounded-lg border border-secondary-200 bg-white p-6">
              {context.document_data ? (
                <DocumentView data={context.document_data} />
              ) : (
                <p className="text-secondary-500">Document data not available.</p>
              )}
            </div>
          )}

          {activeTab === "history" && (
            <div className="rounded-lg border border-secondary-200 bg-white p-6">
              {context.steps.length === 0 ? (
                <p className="text-secondary-500">No steps yet.</p>
              ) : (
                <div className="space-y-4">
                  {context.steps.map((step) => (
                    <div
                      key={step.step_id}
                      className="border-l-4 border-secondary-200 pl-4"
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="font-medium text-secondary-800">
                            {step.approver?.name || "Unknown"}
                          </p>
                          <p className="text-sm text-secondary-500">
                            {step.node_label} — {step.action}
                          </p>
                        </div>
                        <span
                          className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                            step.status === "completed"
                              ? "bg-green-100 text-green-700"
                              : step.status === "skipped"
                                ? "bg-gray-100 text-gray-600"
                                : "bg-yellow-100 text-yellow-700"
                          }`}
                        >
                          {step.status}
                        </span>
                      </div>
                      {step.comment && (
                        <p className="mt-1 text-sm text-secondary-600">
                          &ldquo;{step.comment}&rdquo;
                        </p>
                      )}
                      <p className="mt-1 text-xs text-secondary-400">
                        {new Date(step.timestamp).toLocaleString()}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="space-y-4">
          <ApprovalPanel context={context} currentUserId={currentUserId} />

          {context.status === "pending" && (
            <div className="rounded-lg border border-secondary-200 bg-white p-4">
              <h4 className="mb-3 text-sm font-semibold text-secondary-700">
                Delegate
              </h4>
              <input
                type="text"
                value={delegateUserId}
                onChange={(e) => setDelegateUserId(e.target.value)}
                placeholder="User ID to delegate to"
                className="mb-2 w-full rounded-md border border-secondary-300 p-2 text-sm focus:border-primary-500 focus:outline-none"
              />
              {errorMsg && <p className="mb-2 text-xs text-danger-500">{errorMsg}</p>}
              <button
                onClick={handleDelegate}
                disabled={isPending || !delegateUserId}
                className="w-full rounded-md bg-primary-600 px-3 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
              >
                {isPending ? "Processing..." : "Delegate"}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function PendingList({
  items,
}: {
  items: Array<{
    execution_id: string;
    workflow_name: string;
    document_type: string;
    document_id: string;
    requester: { name: string } | null;
    requested_at: string;
  }>;
}) {
  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-secondary-200 bg-white p-8 text-center text-secondary-500">
        No pending approvals
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {items.map((item) => (
        <a
          key={item.execution_id}
          href={`/app/approvals/${item.execution_id}`}
          className="block rounded-lg border border-secondary-200 bg-white p-4 transition hover:shadow-md"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-secondary-800">{item.workflow_name}</p>
              <p className="text-sm text-secondary-500">
                {item.document_type} — {item.document_id.slice(0, 8)}
              </p>
            </div>
            <div className="text-right text-sm text-secondary-500">
              <p>{item.requester?.name || "Unknown"}</p>
              <p>{new Date(item.requested_at).toLocaleDateString()}</p>
            </div>
          </div>
        </a>
      ))}
    </div>
  );
}

function DocumentView({ data }: { data: Record<string, unknown> }) {
  const excluded = ["id", "created_at", "updated_at", "version"];
  return (
    <div className="grid grid-cols-2 gap-4">
      {Object.entries(data).map(([key, value]) => {
        if (excluded.includes(key)) return null;
        return (
          <div key={key}>
            <dt className="text-xs font-medium uppercase text-secondary-500">
              {key.replace(/_/g, " ")}
            </dt>
            <dd className="mt-1 text-sm text-secondary-800">{String(value ?? "—")}</dd>
          </div>
        );
      })}
    </div>
  );
}
