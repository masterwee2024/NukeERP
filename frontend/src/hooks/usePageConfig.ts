import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";

export interface PageConfig {
  page_key: string;
  page_title: string;
  page_type: string;
  module: string;
  entity_model: string;
  api_endpoint: string;
  layout: string;
  desktop_layout: string;
  mobile_layout: string;
  list_mobile_view: string;
  mobile_group_by: string;
  actions: Array<{
    label: string;
    endpoint: string;
    method: string;
    confirm?: boolean;
    variant?: string;
  }>;
  breadcrumbs: Array<{ label: string; href: string }>;
  page_size: number;
  sort_default: string;
  sort_direction: string;
  fields: PageConfigField[];
}

export interface PageConfigField {
  id: string;
  field_name: string;
  label: string;
  field_type: string;
  required: boolean;
  readonly: boolean;
  show_on_desktop: boolean;
  show_on_mobile: boolean;
  sort_order: number;
}

export function usePageConfig(pageKey: string) {
  return useQuery({
    queryKey: ["pageConfig", pageKey],
    queryFn: async (): Promise<PageConfig> => {
      const { data } = await api.get(`/core/page-configs/${pageKey}/`);
      return data;
    },
    enabled: !!pageKey,
  });
}

export function usePageConfigs(module?: string) {
  return useQuery({
    queryKey: ["pageConfigs", module],
    queryFn: async () => {
      const params = module ? `?module=${module}` : "";
      const { data } = await api.get(`/core/page-configs/${params}`);
      return data;
    },
  });
}

export function usePageConfigMutations() {
  const queryClient = useQueryClient();

  const create = useMutation({
    mutationFn: async (data: Partial<PageConfig>) => {
      const { data: result } = await api.post("/core/page-configs/", data);
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pageConfigs"] });
    },
  });

  const update = useMutation({
    mutationFn: async ({
      pageKey,
      data,
    }: {
      pageKey: string;
      data: Partial<PageConfig>;
    }) => {
      const { data: result } = await api.put(`/core/page-configs/${pageKey}/`, data);
      return result;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["pageConfigs"] });
      queryClient.invalidateQueries({ queryKey: ["pageConfig", variables.pageKey] });
    },
  });

  const remove = useMutation({
    mutationFn: async (pageKey: string) => {
      await api.delete(`/core/page-configs/${pageKey}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pageConfigs"] });
    },
  });

  return { create, update, remove };
}
