import { useState } from "react";
import { useApproval, type ExecutionContext } from "@/hooks/useApproval";

const statusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800 border-yellow-300",
  approved: "bg-green-100 text-green-800 border-green-300",
  rejected: "bg-red-100 text-red-800 border-red-300",
  completed: "bg-blue-100 text-blue-800 border-blue-300",
  cancelled: "bg-gray-100 text-gray-800 border-gray-300",
};

interface ApprovalPanelProps {
  context: ExecutionContext;
  currentUserId: string;
  onActionComplete?: () => void;
}

export function ApprovalPanel({
  context,
  currentUserId,
  onActionComplete,
}: ApprovalPanelProps) {
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");
  const { approve, reject, isPending } = useApproval({
    onApproved: () => {
      setComment("");
      onActionComplete?.();
    },
    onRejected: () => {
      setComment("");
      onActionComplete?.();
    },
    onError: (msg) => setError(msg),
  });

  const isPendingApproval = context.status === "pending";
  const isApprover = context.steps.some(
    (s) =>
      s.status === "pending" &&
      s.approver?.id === currentUserId
  );

  const handleApprove = async () => {
    setError("");
    try {
      await approve({ execution_id: context.execution_id, comment });
    } catch {
      // error handled via callback
    }
  };

  const handleReject = async () => {
    if (!comment.trim()) {
      setError("Comment is required for rejection");
      return;
    }
    setError("");
    try {
      await reject({ execution_id: context.execution_id, comment });
    } catch {
      // error handled via callback
    }
  };

  return (
    <div className="rounded-lg border border-secondary-200 bg-white p-4">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-secondary-700">
          Approval Status
        </h3>
        <span
          className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${statusColors[context.status] || "bg-gray-100 text-gray-800"}`}
        >
          {context.status.charAt(0).toUpperCase() + context.status.slice(1)}
        </span>
      </div>

      <div className="mb-3 space-y-1 text-sm text-secondary-600">
        <div className="flex justify-between">
          <span>Workflow</span>
          <span className="font-medium text-secondary-800">
            {context.workflow.name}
          </span>
        </div>
        <div className="flex justify-between">
          <span>Current Step</span>
          <span className="font-medium text-secondary-800">
            {context.current_node.label || "—"}
          </span>
        </div>
        <div className="flex justify-between">
          <span>Requester</span>
          <span className="font-medium text-secondary-800">
            {context.requester?.name || "—"}
          </span>
        </div>
      </div>

      {isPendingApproval && isApprover && (
        <div className="space-y-3">
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Add a comment..."
            rows={3}
            className="w-full rounded-md border border-secondary-300 p-2 text-sm focus:border-primary-500 focus:outline-none"
          />

          {error && (
            <p className="text-xs text-danger-500">{error}</p>
          )}

          <div className="flex gap-2">
            <button
              onClick={handleApprove}
              disabled={isPending}
              className="flex-1 rounded-md bg-green-600 px-3 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
            >
              {isPending ? "Processing..." : "Approve"}
            </button>
            <button
              onClick={handleReject}
              disabled={isPending || !comment.trim()}
              className="flex-1 rounded-md bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
            >
              {isPending ? "Processing..." : "Reject"}
            </button>
          </div>
        </div>
      )}

      {context.steps.length > 0 && (
        <div className="mt-4 border-t border-secondary-100 pt-3">
          <h4 className="mb-2 text-xs font-semibold uppercase text-secondary-500">
            History
          </h4>
          <div className="space-y-2">
            {context.steps.map((step) => (
              <div
                key={step.step_id}
                className="flex items-start gap-2 text-xs"
              >
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
                    {step.approver?.name || "Unknown"}{" "}
                    <span className="font-normal text-secondary-500">
                      {step.action}
                    </span>
                  </p>
                  {step.comment && (
                    <p className="text-secondary-500">{step.comment}</p>
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
