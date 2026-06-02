import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { ConfirmProvider } from "@/components/ui/ConfirmDialog";
import DynamicFormPage from "./DynamicFormPage";
import type { PageConfig } from "@/hooks/usePageConfig";

const mockConfig: PageConfig = {
  page_key: "test_form",
  page_title: "Test Form",
  page_type: "form",
  module: "core",
  entity_model: "TestModel",
  api_endpoint: "core/test",
  layout: "single",
  desktop_layout: "single",
  mobile_layout: "single",
  list_mobile_view: "card",
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
      help_text: "Enter your name",
      field_type: "text",
      data_type: "string",
      required: true,
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
      is_column: false,
      column_order: 0,
      column_width: "",
      column_align: "left",
      sortable: false,
      filterable: false,
      searchable: false,
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
    {
      id: "f2",
      field_name: "email",
      label: "Email",
      placeholder: "",
      help_text: "",
      field_type: "email",
      data_type: "string",
      required: true,
      readonly: false,
      hidden: false,
      disabled: false,
      default_value: "",
      sort_order: 1,
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
      is_column: false,
      column_order: 0,
      column_width: "",
      column_align: "left",
      sortable: false,
      filterable: false,
      searchable: false,
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
      <BrowserRouter>
        <ConfirmProvider>{ui}</ConfirmProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

describe("DynamicFormPage", () => {
  it("renders page title for new record", () => {
    renderWithProviders(<DynamicFormPage config={mockConfig} />);
    expect(screen.getByText("New Test Form")).toBeDefined();
  });

  it("renders field labels from config", () => {
    renderWithProviders(<DynamicFormPage config={mockConfig} />);
    expect(screen.getByText("Name")).toBeDefined();
    expect(screen.getByText("Email")).toBeDefined();
  });

  it("shows help text for fields", () => {
    renderWithProviders(<DynamicFormPage config={mockConfig} />);
    expect(screen.getByText("Enter your name")).toBeDefined();
  });

  it("renders with submit button when save action exists", () => {
    const configWithAction = {
      ...mockConfig,
      actions: [
        {
          label: "Save",
          endpoint: "",
          method: "post",
          confirm: true,
          variant: "warning",
        },
      ],
    };
    renderWithProviders(<DynamicFormPage config={configWithAction} />);
    expect(screen.getByText("Save")).toBeDefined();
  });
});
