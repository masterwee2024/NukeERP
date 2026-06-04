import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { useConfirm } from "@/components/ui/ConfirmDialog";

export interface PendingApprovalItem {
  execution_id: string;
  step_id: string;
  document_type: string;
  document_id: string;
  document_number: string;
  workflow_name: string;
  module: string;
  requester: { id: string; name: string; email: string } | null;
  company_id: string;
  company_name: string;
  created_at: string;
  overdue: boolean;
}

export interface ApprovalStats {
  total_pending: number;
  overdue_count: number;
  avg_resolution_hours: number | null;
  by_module: { module: string; document_type: string; count: number }[];
}

export interface ApprovalContext {
  execution_id: string;
  workflow: { id: string; name: string; module: string; document_type: string };
  document_type: string;
  document_id: string;
  document_data: Record<string, unknown> | null;
  status: string;
  current_node: { node_id: string | null; label: string; node_type: string };
  requester: { id: string; name: string; email: string } | null;
  company: { id: string; name: string };
  started_at: string;
  completed_at: string | null;
  steps: {
    step_id: string;
    node_label: string;
    node_type: string;
    approver: { id: string | null; name: string; email: string } | null;
    action: string;
    comment: string;
    status: string;
    timestamp: string;
  }[];
  metadata: Record<string, unknown>;
}

export interface QuickActionResponse {
  execution_id: string;
  status: string;
  message: string;
  step_id?: string;
}

export function useApprovalCenter() {
  return useQuery({
    queryKey: ["approval-center"],
    queryFn: async () => {
      const { data } = await api.get("/core/approval-center/");
      return data as { count: number; results: PendingApprovalItem[] };
    },
    refetchInterval: 30_000,
  });
}

export function useApprovalCenterStats() {
  return useQuery({
    queryKey: ["approval-center-stats"],
    queryFn: async () => {
      const { data } = await api.get("/core/approval-center/stats/");
      return data as ApprovalStats;
    },
    refetchInterval: 60_000,
  });
}

export function useApprovalContext(executionId: string | undefined) {
  return useQuery({
    queryKey: ["approval-context", executionId],
    queryFn: async () => {
      if (!executionId) throw new Error("Execution ID required");
      const { data } = await api.get(`/core/approval-center/${executionId}/context/`);
      return data as ApprovalContext;
    },
    enabled: !!executionId,
  });
}

export function useQuickApprove() {
  const queryClient = useQueryClient();
  const { confirm } = useConfirm();

  return useMutation({
    mutationFn: async (params: { execution_id: string; comment?: string }) => {
      const confirmed = await confirm({
        title: "Approve",
        message: "Are you sure you want to approve this?",
        variant: "warning",
        confirmText: "Approve",
      });
      if (!confirmed) throw new Error("cancelled");

      const { data } = await api.post(
        `/core/approval-center/${params.execution_id}/quick-approve/`,
        { comment: params.comment || "" }
      );
      return data as QuickActionResponse;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approval-center"] });
      queryClient.invalidateQueries({ queryKey: ["approval-center-stats"] });
    },
  });
}

export function useQuickReject() {
  const queryClient = useQueryClient();
  const { confirm } = useConfirm();

  return useMutation({
    mutationFn: async (params: { execution_id: string; comment: string }) => {
      const confirmed = await confirm({
        title: "Reject",
        message: "Are you sure you want to reject this?",
        variant: "danger",
        confirmText: "Reject",
      });
      if (!confirmed) throw new Error("cancelled");

      const { data } = await api.post(
        `/core/approval-center/${params.execution_id}/quick-reject/`,
        { comment: params.comment }
      );
      return data as QuickActionResponse;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approval-center"] });
      queryClient.invalidateQueries({ queryKey: ["approval-center-stats"] });
    },
  });
}

export function useBatchApprove() {
  const queryClient = useQueryClient();
  const { confirm } = useConfirm();

  return useMutation({
    mutationFn: async (params: { execution_ids: string[]; comment?: string }) => {
      const confirmed = await confirm({
        title: "Batch Approve",
        message: `Are you sure you want to approve ${params.execution_ids.length} items?`,
        variant: "warning",
        confirmText: "Approve All",
      });
      if (!confirmed) throw new Error("cancelled");

      const results: QuickActionResponse[] = [];
      for (const execution_id of params.execution_ids) {
        try {
          const { data } = await api.post(
            `/core/approval-center/${execution_id}/quick-approve/`,
            { comment: params.comment || "" }
          );
          results.push(data as QuickActionResponse);
        } catch {
          results.push({
            execution_id,
            status: "error",
            message: "Failed to approve",
          });
        }
      }
      return results;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approval-center"] });
      queryClient.invalidateQueries({ queryKey: ["approval-center-stats"] });
    },
  });
}
