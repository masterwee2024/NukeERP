import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import InlineTableField from "./fields/InlineTableField";
import type { PageConfigField } from "@/hooks/usePageConfig";

function makeField(
  overrides: Partial<PageConfigField> = {},
  lineFields: PageConfigField[] = []
): PageConfigField {
  return {
    id: "1",
    field_name: "line_items",
    label: "Line Items",
    placeholder: "",
    help_text: "",
    field_type: "inline_table",
    data_type: "string",
    required: false,
    readonly: false,
    hidden: false,
    disabled: false,
    default_value: "",
    sort_order: 0,
    group_name: "",
    col_span: 12,
    width: "full",
    show_on_desktop: true,
    show_on_mobile: true,
    desktop_col_span: 12,
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
    line_fields: lineFields,
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

const qtyField: PageConfigField = makeField({
  id: "lf1",
  field_name: "qty",
  label: "Qty",
  field_type: "number",
});

const descField: PageConfigField = makeField({
  id: "lf2",
  field_name: "description",
  label: "Description",
  field_type: "text",
});

describe("InlineTableField", () => {
  it("renders empty state with no rows", () => {
    const onChange = vi.fn();
    render(
      <InlineTableField
        field={makeField({}, [qtyField, descField])}
        value={[]}
        onChange={onChange}
      />
    );
    expect(screen.getByText("No items")).toBeDefined();
  });

  it("renders add row button", () => {
    const onChange = vi.fn();
    render(
      <InlineTableField
        field={makeField({}, [qtyField, descField])}
        value={[]}
        onChange={onChange}
      />
    );
    expect(screen.getByText("+ Add Row")).toBeDefined();
  });

  it("adds a row when button clicked", () => {
    const onChange = vi.fn();
    render(
      <InlineTableField
        field={makeField({}, [qtyField, descField])}
        value={[]}
        onChange={onChange}
      />
    );
    fireEvent.click(screen.getByText("+ Add Row"));
    expect(onChange).toHaveBeenCalledWith("line_items", [{ description: "", qty: "" }]);
  });

  it("renders existing rows", () => {
    const onChange = vi.fn();
    const rows = [
      { qty: 2, description: "Item A" },
      { qty: 5, description: "Item B" },
    ];
    render(
      <InlineTableField
        field={makeField({}, [qtyField, descField])}
        value={rows}
        onChange={onChange}
      />
    );
    expect(screen.getByDisplayValue("2")).toBeDefined();
    expect(screen.getByDisplayValue("Item A")).toBeDefined();
    expect(screen.getByDisplayValue("5")).toBeDefined();
    expect(screen.getByDisplayValue("Item B")).toBeDefined();
  });

  it("removes a row", () => {
    const onChange = vi.fn();
    const rows = [{ qty: 2, description: "Item A" }];
    render(
      <InlineTableField
        field={makeField({}, [qtyField, descField])}
        value={rows}
        onChange={onChange}
      />
    );
    const removeButtons = screen.getAllByText("✕");
    fireEvent.click(removeButtons[0]);
    expect(onChange).toHaveBeenCalledWith("line_items", []);
  });

  it("updates a cell value", () => {
    const onChange = vi.fn();
    const rows = [{ qty: 2, description: "Old desc" }];
    render(
      <InlineTableField
        field={makeField({}, [qtyField, descField])}
        value={rows}
        onChange={onChange}
      />
    );
    const inputs = screen.getAllByRole("textbox");
    fireEvent.change(inputs[0], { target: { value: "New desc" } });
    expect(onChange).toHaveBeenCalledWith("line_items", [
      { qty: 2, description: "New desc" },
    ]);
  });

  it("renders column headers from line fields", () => {
    const onChange = vi.fn();
    render(
      <InlineTableField
        field={makeField({}, [qtyField, descField])}
        value={[]}
        onChange={onChange}
      />
    );
    expect(screen.getByText("Qty")).toBeDefined();
    expect(screen.getByText("Description")).toBeDefined();
  });
});
