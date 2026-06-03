import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";

export interface CompanyAssignment {
  id: string;
  company_id: string;
  company_name: string;
  next_number: number;
  reset_period: string;
  last_reset_at: string | null;
  is_active: boolean;
  updated_at: string;
  version: number;
}

export interface NumberingPolicy {
  id: string;
  document_type: string;
  prefix: string;
  date_format: string;
  padding: number;
  description: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  version: number;
  company_assignments: CompanyAssignment[];
}

export interface PolicyListItem {
  id: string;
  document_type: string;
  prefix: string;
  date_format: string;
  padding: number;
  description: string;
  is_active: boolean;
}

export interface PolicyCreatePayload {
  document_type: string;
  prefix?: string;
  date_format?: string;
  padding?: number;
  description?: string;
}

export interface PolicyUpdatePayload {
  document_type?: string;
  prefix?: string;
  date_format?: string;
  padding?: number;
  description?: string;
  updated_at?: string;
}

export interface AssignPayload {
  company_id: string;
}

export interface AssignmentUpdatePayload {
  next_number?: number;
  reset_period?: string;
  updated_at?: string;
}

export function useNumberingPolicy(id: string) {
  return useQuery({
    queryKey: ["numbering-policy", id],
    queryFn: async (): Promise<NumberingPolicy> => {
      const { data } = await api.get(`/core/admin/numbering-policies/${id}/`);
      return data;
    },
    enabled: !!id,
    staleTime: 15 * 1000,
  });
}

export function useNumberingPolicies() {
  const queryClient = useQueryClient();
  const queryKey = ["numbering-policies"];

  const { data: policies = [], isLoading } = useQuery({
    queryKey,
    queryFn: async (): Promise<PolicyListItem[]> => {
      const { data } = await api.get("/core/admin/numbering-policies/");
      return data;
    },
    staleTime: 30 * 1000,
  });

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["numbering-policies"] });

  const createMutation = useMutation({
    mutationFn: async (payload: PolicyCreatePayload) => {
      const { data } = await api.post("/core/admin/numbering-policies/", payload);
      return data;
    },
    onSuccess: invalidate,
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, ...payload }: PolicyUpdatePayload & { id: string }) => {
      const { data } = await api.put(`/core/admin/numbering-policies/${id}/`, payload);
      return data;
    },
    onSuccess: () => {
      invalidate();
      queryClient.invalidateQueries({ queryKey: ["numbering-policy"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/core/admin/numbering-policies/${id}/`);
    },
    onSuccess: invalidate,
  });

  const assignMutation = useMutation({
    mutationFn: async ({
      policyId,
      ...payload
    }: AssignPayload & { policyId: string }) => {
      const { data } = await api.post(
        `/core/admin/numbering-policies/${policyId}/assign/`,
        payload
      );
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["numbering-policy"] }),
  });

  const updateAssignmentMutation = useMutation({
    mutationFn: async ({
      policyId,
      assignmentId,
      ...payload
    }: AssignmentUpdatePayload & { policyId: string; assignmentId: string }) => {
      const { data } = await api.put(
        `/core/admin/numbering-policies/${policyId}/assign/${assignmentId}/`,
        payload
      );
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["numbering-policy"] }),
  });

  const unassignMutation = useMutation({
    mutationFn: async ({
      policyId,
      assignmentId,
    }: {
      policyId: string;
      assignmentId: string;
    }) => {
      await api.delete(
        `/core/admin/numbering-policies/${policyId}/assign/${assignmentId}/`
      );
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["numbering-policy"] }),
  });

  return {
    policies,
    isLoading,
    create: (data: PolicyCreatePayload) => createMutation.mutateAsync(data),
    update: (id: string, data: PolicyUpdatePayload) =>
      updateMutation.mutateAsync({ id, ...data }),
    remove: (id: string) => deleteMutation.mutateAsync(id),
    assign: (policyId: string, companyId: string) =>
      assignMutation.mutateAsync({ policyId, company_id: companyId }),
    updateAssignment: (
      policyId: string,
      assignmentId: string,
      data: AssignmentUpdatePayload
    ) =>
      updateAssignmentMutation.mutateAsync({
        policyId,
        assignmentId,
        ...data,
      }),
    unassign: (policyId: string, assignmentId: string) =>
      unassignMutation.mutateAsync({ policyId, assignmentId }),
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
  };
}
