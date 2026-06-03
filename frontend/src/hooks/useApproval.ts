import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { useConfirm } from "@/components/ui/ConfirmDialog";

export interface ApproverInfo {
  id: string | null;
  name: string;
  email: string;
}

export interface StepInfo {
  step_id: string;
  node_label: string;
  node_type: string;
  approver: ApproverInfo | null;
  action: string;
  comment: string;
  status: string;
  timestamp: string;
  delegated_to: ApproverInfo | null;
}

export interface ExecutionContext {
  execution_id: string;
  workflow: {
    id: string;
    name: string;
    module: string;
    document_type: string;
  };
  document_type: string;
  document_id: string;
  document_data: Record<string, unknown> | null;
  status: string;
  current_node: {
    node_id: string | null;
    label: string;
    node_type: string;
  };
  requester: ApproverInfo | null;
  created_by: ApproverInfo | null;
  company: { id: string; name: string };
  started_at: string;
  completed_at: string | null;
  steps: StepInfo[];
  metadata: Record<string, unknown>;
}

export interface PendingItem {
  step_id: string;
  execution_id: string;
  workflow_name: string;
  document_type: string;
  document_id: string;
  node_label: string;
  node_type: string;
  requested_at: string;
  requester: ApproverInfo | null;
  company_id: string;
}

export interface ActionResponse {
  execution_id: string;
  status: string;
  message: string;
  step_id?: string;
}

export interface HistoryItem {
  execution_id: string;
  workflow_name: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  steps: StepInfo[];
}

function getCompanyId(): string | undefined {
  return localStorage.getItem("current_company_id") ?? undefined;
}

export function useApproval(config?: {
  onApproved?: () => void;
  onRejected?: () => void;
  onError?: (error: string) => void;
}) {
  const { confirm } = useConfirm();
  const queryClient = useQueryClient();

  const executeMutation = useMutation({
    mutationFn: async (params: {
      workflow_id: string;
      document_type: string;
      document_id: string;
    }) => {
      const { data } = await api.post("/core/workflows/execute/", params, {
        headers: { "X-Company-Id": getCompanyId() },
      });
      return data as { execution_id: string; status: string; message: string };
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      config?.onError?.(
        err.response?.data?.detail || "Failed to submit for approval"
      );
    },
  });

  const approveMutation = useMutation({
    mutationFn: async (params: {
      execution_id: string;
      comment?: string;
    }) => {
      const confirmed = await confirm({
        title: "Approve",
        message: "Are you sure you want to approve this?",
        variant: "warning",
        confirmText: "Approve",
      });
      if (!confirmed) throw new Error("cancelled");

      const { data } = await api.post(
        `/core/workflows/executions/${params.execution_id}/approve/`,
        { comment: params.comment || "" }
      );
      return data as ActionResponse;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approval-pending"] });
      queryClient.invalidateQueries({ queryKey: ["approval-context"] });
      config?.onApproved?.();
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      config?.onError?.(
        err.response?.data?.detail || "Failed to approve"
      );
    },
  });

  const rejectMutation = useMutation({
    mutationFn: async (params: {
      execution_id: string;
      comment: string;
    }) => {
      const confirmed = await confirm({
        title: "Reject",
        message: "Are you sure you want to reject this?",
        variant: "danger",
        confirmText: "Reject",
      });
      if (!confirmed) throw new Error("cancelled");

      const { data } = await api.post(
        `/core/workflows/executions/${params.execution_id}/reject/`,
        { comment: params.comment }
      );
      return data as ActionResponse;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approval-pending"] });
      queryClient.invalidateQueries({ queryKey: ["approval-context"] });
      config?.onRejected?.();
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      config?.onError?.(
        err.response?.data?.detail || "Failed to reject"
      );
    },
  });

  const delegateMutation = useMutation({
    mutationFn: async (params: {
      execution_id: string;
      delegated_to_id: string;
      comment?: string;
    }) => {
      const confirmed = await confirm({
        title: "Delegate",
        message: "Are you sure you want to delegate this approval?",
        variant: "info",
        confirmText: "Delegate",
      });
      if (!confirmed) throw new Error("cancelled");

      const { data } = await api.post(
        `/core/workflows/executions/${params.execution_id}/delegate/`,
        {
          delegated_to_id: params.delegated_to_id,
          comment: params.comment || "",
        }
      );
      return data as ActionResponse;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approval-pending"] });
      config?.onApproved?.();
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      config?.onError?.(
        err.response?.data?.detail || "Failed to delegate"
      );
    },
  });

  return {
    execute: executeMutation.mutateAsync,
    approve: approveMutation.mutateAsync,
    reject: rejectMutation.mutateAsync,
    delegate: delegateMutation.mutateAsync,
    isPending:
      executeMutation.isPending ||
      approveMutation.isPending ||
      rejectMutation.isPending ||
      delegateMutation.isPending,
    error:
      executeMutation.error ||
      approveMutation.error ||
      rejectMutation.error ||
      delegateMutation.error,
  };
}

export function usePendingApprovals() {
  return useQuery({
    queryKey: ["approval-pending"],
    queryFn: async () => {
      const { data } = await api.get("/core/workflows/executions/pending/");
      return data as { count: number; results: PendingItem[] };
    },
    refetchInterval: 30_000,
  });
}

export function useExecutionContext(executionId: string | undefined) {
  return useQuery({
    queryKey: ["approval-context", executionId],
    queryFn: async () => {
      if (!executionId) throw new Error("Execution ID required");
      const { data } = await api.get(
        `/core/workflows/executions/${executionId}/context/`
      );
      return data as ExecutionContext;
    },
    enabled: !!executionId,
  });
}

export function useApprovalHistory(
  documentType: string | undefined,
  documentId: string | undefined
) {
  return useQuery({
    queryKey: ["approval-history", documentType, documentId],
    queryFn: async () => {
      if (!documentType || !documentId)
        throw new Error("Document type and ID required");
      const { data } = await api.get(
        `/core/workflows/history/${documentType}/${documentId}/`
      );
      return data as HistoryItem[];
    },
    enabled: !!documentType && !!documentId,
  });
}
