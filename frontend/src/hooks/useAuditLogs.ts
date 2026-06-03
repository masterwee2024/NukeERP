import { useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";

export interface AuditLog {
  id: string;
  model_name: string;
  record_id: string;
  action: "create" | "update" | "delete";
  changes: Record<string, { old: unknown; new: unknown }>;
  user_name: string;
  ip_address: string | null;
  company_name: string;
  timestamp: string;
}

interface AuditListResponse {
  count: number;
  results: AuditLog[];
}

interface AuditFilters {
  page?: number;
  pageSize?: number;
  modelName?: string;
  action?: string;
  userId?: string;
  recordId?: string;
  dateFrom?: string;
  dateTo?: string;
  search?: string;
}

export function useAuditLogs(filters: AuditFilters = {}) {
  const queryClient = useQueryClient();
  const queryKey = ["audit-logs", filters];

  const params = new URLSearchParams();
  if (filters.page) params.set("page", String(filters.page));
  if (filters.pageSize) params.set("page_size", String(filters.pageSize));
  if (filters.modelName) params.set("model_name", filters.modelName);
  if (filters.action) params.set("action", filters.action);
  if (filters.userId) params.set("user_id", filters.userId);
  if (filters.recordId) params.set("record_id", filters.recordId);
  if (filters.dateFrom) params.set("date_from", filters.dateFrom);
  if (filters.dateTo) params.set("date_to", filters.dateTo);
  if (filters.search) params.set("search", filters.search);

  const { data, isLoading } = useQuery({
    queryKey,
    queryFn: async (): Promise<AuditListResponse> => {
      const { data } = await api.get(`/core/admin/audit-logs/?${params.toString()}`);
      return data;
    },
    staleTime: 15 * 1000,
  });

  return {
    logs: data?.results ?? [],
    totalCount: data?.count ?? 0,
    isLoading,
    refresh: () => queryClient.invalidateQueries({ queryKey: ["audit-logs"] }),
  };
}

export function useRecordAuditTrail(modelName: string, recordId: string) {
  return useQuery({
    queryKey: ["audit-trail", modelName, recordId],
    queryFn: async (): Promise<AuditLog[]> => {
      const { data } = await api.get(
        `/core/admin/audit-logs/model/${modelName}/${recordId}/`
      );
      return data;
    },
    enabled: !!modelName && !!recordId,
    staleTime: 30 * 1000,
  });
}
