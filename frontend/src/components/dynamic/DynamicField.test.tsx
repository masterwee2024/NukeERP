import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import DynamicField from "./fields/DynamicField";
import type { PageConfigField } from "@/hooks/usePageConfig";

function makeField(overrides: Partial<PageConfigField> = {}): PageConfigField {
  return {
    id: "1",
    field_name: "test_field",
    label: "Test Field",
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
    ...overrides,
  };
}

describe("DynamicField", () => {
  it("renders text field", () => {
    const onChange = vi.fn();
    render(
      <DynamicField
        field={makeField({ field_type: "text" })}
        value=""
        onChange={onChange}
      />
    );
    expect(screen.getByText("Test Field")).toBeDefined();
  });

  it("calls onChange when text input changes", () => {
    const onChange = vi.fn();
    render(
      <DynamicField
        field={makeField({ field_type: "text" })}
        value=""
        onChange={onChange}
      />
    );
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "hello" } });
    expect(onChange).toHaveBeenCalledWith("test_field", "hello");
  });

  it("shows required indicator", () => {
    const onChange = vi.fn();
    render(
      <DynamicField
        field={makeField({ field_type: "text", required: true })}
        value=""
        onChange={onChange}
      />
    );
    expect(screen.getByText("*")).toBeDefined();
  });

  it("shows error message", () => {
    const onChange = vi.fn();
    render(
      <DynamicField
        field={makeField({ field_type: "text" })}
        value=""
        onChange={onChange}
        error="Field is required"
      />
    );
    expect(screen.getByText("Field is required")).toBeDefined();
  });

  it("shows help text when no error", () => {
    const onChange = vi.fn();
    render(
      <DynamicField
        field={makeField({ field_type: "text", help_text: "Enter your name" })}
        value=""
        onChange={onChange}
      />
    );
    expect(screen.getByText("Enter your name")).toBeDefined();
  });

  it("renders number field", () => {
    const onChange = vi.fn();
    render(
      <DynamicField
        field={makeField({ field_type: "number" })}
        value={42}
        onChange={onChange}
      />
    );
    const input = screen.getByRole("spinbutton");
    expect(input).toBeDefined();
  });

  it("renders decimal field", () => {
    const onChange = vi.fn();
    render(
      <DynamicField
        field={makeField({ field_type: "decimal" })}
        value={42.5}
        onChange={onChange}
      />
    );
    expect(screen.getByRole("spinbutton")).toBeDefined();
  });

  it("renders textarea field", () => {
    const onChange = vi.fn();
    render(
      <DynamicField
        field={makeField({ field_type: "textarea" })}
        value=""
        onChange={onChange}
      />
    );
    expect(screen.getByRole("textbox")).toBeDefined();
  });

  it("renders select field with options", () => {
    const onChange = vi.fn();
    render(
      <DynamicField
        field={makeField({
          field_type: "select",
          options_source: "static",
          options: [
            { label: "Option A", value: "a" },
            { label: "Option B", value: "b" },
          ],
        })}
        value=""
        onChange={onChange}
      />
    );
    expect(screen.getByText("Option A")).toBeDefined();
    expect(screen.getByText("Option B")).toBeDefined();
  });

  it("renders checkbox field", () => {
    const onChange = vi.fn();
    render(
      <DynamicField
        field={makeField({ field_type: "checkbox" })}
        value={false}
        onChange={onChange}
      />
    );
    expect(screen.getByRole("checkbox")).toBeDefined();
  });

  it("renders date field", () => {
    const onChange = vi.fn();
    render(
      <DynamicField
        field={makeField({ field_type: "date" })}
        value=""
        onChange={onChange}
      />
    );
    expect(screen.getByDisplayValue("")).toBeDefined();
  });

  it("renders toggle field", () => {
    const onChange = vi.fn();
    render(
      <DynamicField
        field={makeField({ field_type: "toggle" })}
        value={false}
        onChange={onChange}
      />
    );
    expect(screen.getByRole("switch")).toBeDefined();
  });

  it("renders radio field", () => {
    const onChange = vi.fn();
    render(
      <DynamicField
        field={makeField({
          field_type: "radio",
          options_source: "static",
          options: [{ label: "Yes", value: "yes" }],
        })}
        value=""
        onChange={onChange}
      />
    );
    expect(screen.getByText("Yes")).toBeDefined();
  });

  it("renders heading field", () => {
    const onChange = vi.fn();
    render(
      <DynamicField
        field={makeField({ field_type: "heading" })}
        value=""
        onChange={onChange}
      />
    );
    expect(screen.getByText("Test Field")).toBeDefined();
  });

  it("renders readonly text field", () => {
    const onChange = vi.fn();
    render(
      <DynamicField
        field={makeField({ field_type: "readonly_text" })}
        value="Readonly value"
        onChange={onChange}
      />
    );
    expect(screen.getByText("Readonly value")).toBeDefined();
  });

  it("renders badge field", () => {
    const onChange = vi.fn();
    render(
      <DynamicField
        field={makeField({ field_type: "badge" })}
        value="posted"
        onChange={onChange}
      />
    );
    expect(screen.getByText("posted")).toBeDefined();
  });

  it("renders currency field with prefix", () => {
    const onChange = vi.fn();
    render(
      <DynamicField
        field={makeField({ field_type: "currency", prefix: "RM" })}
        value={100}
        onChange={onChange}
      />
    );
    expect(screen.getByText("RM")).toBeDefined();
  });

  it("renders percentage field with suffix", () => {
    const onChange = vi.fn();
    render(
      <DynamicField
        field={makeField({ field_type: "percentage", suffix: "%" })}
        value={50}
        onChange={onChange}
      />
    );
    expect(screen.getByText("%")).toBeDefined();
  });

  it("renders multi-select field", () => {
    const onChange = vi.fn();
    render(
      <DynamicField
        field={makeField({
          field_type: "multi_select",
          options_source: "static",
          options: [
            { label: "X", value: "x" },
            { label: "Y", value: "y" },
          ],
        })}
        value={[]}
        onChange={onChange}
      />
    );
    expect(screen.getByText("X")).toBeDefined();
    expect(screen.getByText("Y")).toBeDefined();
  });

  it("shows unknown field type message", () => {
    const onChange = vi.fn();
    render(
      <DynamicField
        field={makeField({ field_type: "unknown_type" })}
        value=""
        onChange={onChange}
      />
    );
    expect(screen.getByText(/unknown field type/i)).toBeDefined();
  });
});
