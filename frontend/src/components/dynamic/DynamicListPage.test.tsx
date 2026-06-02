import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import DynamicListPage from "./DynamicListPage";
import type { PageConfig } from "@/hooks/usePageConfig";

const mockConfig: PageConfig = {
  page_key: "test_list",
  page_title: "Test List",
  page_type: "list",
  module: "core",
  entity_model: "TestModel",
  api_endpoint: "core/test",
  layout: "single",
  desktop_layout: "single",
  mobile_layout: "single",
  list_mobile_view: "table",
  mobile_group_by: "",
  actions: [],
  breadcrumbs: [],
  page_size: 25,
  sort_default: "",
  sort_direction: "asc",
  fields: [
    {
      id: "f1",
      field_name: "name",
      label: "Name",
      placeholder: "",
      help_text: "",
      field_type: "text",
      data_type: "string",
      required: false,
      readonly: false,
      hidden: false,
      disabled: false,
      default_value: "",
      sort_order: 0,
      group_name: "",
      col_span: 6,
      width: "full",
      show_on_desktop: true,
      show_on_mobile: true,
      desktop_col_span: 6,
      mobile_col_span: 12,
      mobile_render_as: "text",
      min_length: null,
      max_length: null,
      min_value: null,
      max_value: null,
      pattern: "",
      custom_validator: "",
      options_source: "",
      options: [],
      options_api: "",
      options_label_field: "",
      options_value_field: "",
      option_group_by: "",
      related_entity: "",
      related_display: "",
      related_search: {},
      related_fields: [],
      show_when: {},
      depends_on: {},
      is_column: true,
      column_order: 0,
      column_width: "",
      column_align: "left",
      sortable: true,
      filterable: false,
      searchable: true,
      aggregate: "",
      render_as: "",
      parent_field: null,
      line_entity: "",
      line_fields: [],
      permission_read: "",
      permission_write: "",
      icon: "",
      prefix: "",
      suffix: "",
      format: "",
      badge_color: {},
      css_class: "",
    },
  ],
};

function renderWithProviders(ui: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{ui}</BrowserRouter>
    </QueryClientProvider>
  );
}

describe("DynamicListPage", () => {
  it("renders page title", () => {
    renderWithProviders(<DynamicListPage config={mockConfig} />);
    expect(screen.getByText("Test List")).toBeDefined();
  });

  it("renders search input", () => {
    renderWithProviders(<DynamicListPage config={mockConfig} />);
    expect(screen.getByPlaceholderText("Search...")).toBeDefined();
  });

  it("renders column headers from config", () => {
    renderWithProviders(<DynamicListPage config={mockConfig} />);
    expect(screen.getByText("Name")).toBeDefined();
  });

  it("renders create button when action exists", () => {
    const configWithAction = {
      ...mockConfig,
      actions: [
        {
          label: "Create",
          endpoint: "",
          method: "post",
          confirm: false,
          variant: "info",
        },
      ],
    };
    renderWithProviders(<DynamicListPage config={configWithAction} />);
    expect(screen.getByText("Create")).toBeDefined();
  });

  it("shows loading state", () => {
    renderWithProviders(<DynamicListPage config={mockConfig} />);
    expect(screen.getByText("Loading...")).toBeDefined();
  });
});
