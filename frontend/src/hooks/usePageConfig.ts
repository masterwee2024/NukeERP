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
  placeholder: string;
  help_text: string;
  field_type: string;
  data_type: string;
  required: boolean;
  readonly: boolean;
  hidden: boolean;
  disabled: boolean;
  default_value: string;
  sort_order: number;
  group_name: string;
  col_span: number;
  width: string;
  show_on_desktop: boolean;
  show_on_mobile: boolean;
  desktop_col_span: number;
  mobile_col_span: number;
  mobile_render_as: string;
  min_length: number | null;
  max_length: number | null;
  min_value: number | null;
  max_value: number | null;
  pattern: string;
  custom_validator: string;
  options_source: string;
  options: Array<{ label: string; value: string }>;
  options_api: string;
  options_label_field: string;
  options_value_field: string;
  option_group_by: string;
  related_entity: string;
  related_display: string;
  related_search: Record<string, unknown>;
  related_fields: string[];
  show_when: Record<string, unknown>;
  depends_on: Record<string, unknown>;
  is_column: boolean;
  column_order: number;
  column_width: string;
  column_align: string;
  sortable: boolean;
  filterable: boolean;
  searchable: boolean;
  aggregate: string;
  render_as: string;
  parent_field: string | null;
  line_entity: string;
  line_fields: PageConfigField[];
  permission_read: string;
  permission_write: string;
  icon: string;
  prefix: string;
  suffix: string;
  format: string;
  badge_color: Record<string, string>;
  css_class: string;
}

export function usePageConfig(pageKey: string) {
  return useQuery({
    queryKey: ["pageConfig", pageKey],
    queryFn: async (): Promise<PageConfig> => {
      const { data } = await api.get(`/core/page-configs/${pageKey}/`);
      return data;
    },
    enabled: !!pageKey,
    staleTime: 1000 * 60 * 60 * 24, // 24 hours
    gcTime: 1000 * 60 * 60 * 24, // 24 hours
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
    staleTime: 1000 * 60 * 60 * 24, // 24 hours
    gcTime: 1000 * 60 * 60 * 24, // 24 hours
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
