import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { useConfirm } from "@/components/ui/ConfirmDialog";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface RequesterBrief {
  id: string | null;
  name: string;
  email: string;
}

export interface PendingApprovalItem {
  execution_id: string;
  step_id: string;
  document_type: string;
  document_id: string;
  document_number: string;
  workflow_name: string;
  module: string;
  requester: RequesterBrief | null;
  company_id: string;
  company_name: string;
  created_at: string;
  overdue: boolean;
}

export interface ModuleStats {
  module: string;
  document_type: string;
  count: number;
}

export interface ApprovalStats {
  total_pending: number;
  overdue_count: number;
  avg_resolution_hours: number | null;
  by_module: ModuleStats[];
}

export interface ActionOut {
  execution_id: string;
  status: string;
  message: string;
  step_id?: string;
  delegated_to?: string;
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export function useApprovalCenterList(opts?: {
  module?: string;
  document_type?: string;
}) {
  const params = new URLSearchParams();
  if (opts?.module) params.set("module", opts.module);
  if (opts?.document_type) params.set("document_type", opts.document_type);

  return useQuery({
    queryKey: ["approval-center-list", opts?.module, opts?.document_type],
    queryFn: async () => {
      const qs = params.toString() ? `?${params.toString()}` : "";
      const { data } = await api.get(`/core/approval-center/${qs}`);
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

export function useApprovalCenterContext(executionId: string | null) {
  return useQuery({
    queryKey: ["approval-center-context", executionId],
    queryFn: async () => {
      const { data } = await api.get(
        `/core/approval-center/${executionId}/context/`
      );
      return data;
    },
    enabled: !!executionId,
  });
}

export function useApprovalCenterActions(opts?: {
  onSuccess?: () => void;
  onError?: (msg: string) => void;
}) {
  const { confirm } = useConfirm();
  const queryClient = useQueryClient();

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["approval-center-list"] });
    queryClient.invalidateQueries({ queryKey: ["approval-center-stats"] });
    queryClient.invalidateQueries({ queryKey: ["approval-center-context"] });
  };

  const approveMutation = useMutation({
    mutationFn: async (params: { execution_id: string; comment?: string }) => {
      const confirmed = await confirm({
        title: "Approve",
        message: "Are you sure you want to approve this document?",
        variant: "warning",
        confirmText: "Approve",
      });
      if (!confirmed) throw new Error("cancelled");
      const { data } = await api.post(
        `/core/approval-center/${params.execution_id}/quick-approve/`,
        { comment: params.comment ?? "" }
      );
      return data as ActionOut;
    },
    onSuccess: () => {
      invalidate();
      opts?.onSuccess?.();
    },
    onError: (err: { response?: { data?: { detail?: string } }; message?: string }) => {
      if (err.message === "cancelled") return;
      opts?.onError?.(err.response?.data?.detail ?? "Failed to approve");
    },
  });

  const rejectMutation = useMutation({
    mutationFn: async (params: { execution_id: string; comment: string }) => {
      const confirmed = await confirm({
        title: "Reject",
        message: "Rejecting this document cannot be undone. Continue?",
        variant: "danger",
        confirmText: "Reject",
      });
      if (!confirmed) throw new Error("cancelled");
      const { data } = await api.post(
        `/core/approval-center/${params.execution_id}/quick-reject/`,
        { comment: params.comment }
      );
      return data as ActionOut;
    },
    onSuccess: () => {
      invalidate();
      opts?.onSuccess?.();
    },
    onError: (err: { response?: { data?: { detail?: string } }; message?: string }) => {
      if (err.message === "cancelled") return;
      opts?.onError?.(err.response?.data?.detail ?? "Failed to reject");
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
        message: "Delegate this approval to the selected user?",
        variant: "info",
        confirmText: "Delegate",
      });
      if (!confirmed) throw new Error("cancelled");
      const { data } = await api.post(
        `/core/approval-center/${params.execution_id}/delegate/`,
        {
          delegated_to_id: params.delegated_to_id,
          comment: params.comment ?? "",
        }
      );
      return data as ActionOut;
    },
    onSuccess: () => {
      invalidate();
      opts?.onSuccess?.();
    },
    onError: (err: { response?: { data?: { detail?: string } }; message?: string }) => {
      if (err.message === "cancelled") return;
      opts?.onError?.(err.response?.data?.detail ?? "Failed to delegate");
    },
  });

  return {
    approve: approveMutation.mutateAsync,
    reject: rejectMutation.mutateAsync,
    delegate: delegateMutation.mutateAsync,
    isApproving: approveMutation.isPending,
    isRejecting: rejectMutation.isPending,
    isDelegating: delegateMutation.isPending,
    isPending:
      approveMutation.isPending ||
      rejectMutation.isPending ||
      delegateMutation.isPending,
  };
}
