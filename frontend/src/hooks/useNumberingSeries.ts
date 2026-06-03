import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";

export interface NumberingSeries {
  id: string;
  document_type: string;
  prefix: string;
  date_format: string;
  next_number: number;
  reset_period: string;
  padding: number;
  company: string;
  company_name: string;
  description: string;
  is_active: boolean;
  last_reset_at: string | null;
  created_at: string;
  updated_at: string;
  version: number;
}

export interface NumberingSeriesCreate {
  document_type: string;
  prefix?: string;
  date_format?: string;
  next_number?: number;
  reset_period?: string;
  padding?: number;
  company_id: string;
  description?: string;
}

export interface NumberingSeriesUpdate {
  document_type?: string;
  prefix?: string;
  date_format?: string;
  next_number?: number;
  reset_period?: string;
  padding?: number;
  company_id?: string;
  description?: string;
  updated_at?: string;
}

export function useNumberingSeries() {
  const queryClient = useQueryClient();
  const queryKey = ["numbering-series"];

  const { data: seriesList = [], isLoading } = useQuery({
    queryKey,
    queryFn: async (): Promise<NumberingSeries[]> => {
      const { data } = await api.get("/core/admin/numbering-series/");
      return data;
    },
    staleTime: 30 * 1000,
  });

  const createMutation = useMutation({
    mutationFn: async (payload: NumberingSeriesCreate) => {
      const { data } = await api.post("/core/admin/numbering-series/", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, ...payload }: NumberingSeriesUpdate & { id: string }) => {
      const { data } = await api.put(`/core/admin/numbering-series/${id}/`, payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/core/admin/numbering-series/${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });

  return {
    seriesList,
    isLoading,
    create: (data: NumberingSeriesCreate) => createMutation.mutateAsync(data),
    update: (id: string, data: NumberingSeriesUpdate) => updateMutation.mutateAsync({ id, ...data }),
    remove: (id: string) => deleteMutation.mutateAsync(id),
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
}
