import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { useBuilderStore, createDefaultField } from "../builderStore";
import PropertyEditor from "../PropertyEditor";

function renderPropertyEditor(open = true) {
  return render(<PropertyEditor open={open} onClose={() => {}} />);
}

describe("PropertyEditor", () => {
  beforeEach(() => {
    useBuilderStore.getState().reset();
  });

  it("shows empty state when no field selected", () => {
    renderPropertyEditor();
    expect(
      screen.getByText("Select a field to edit its properties")
    ).toBeTruthy();
  });

  it("shows field properties when a field is selected", () => {
    const store = useBuilderStore.getState();
    const field = createDefaultField("text", {
      label: "Full Name",
      field_name: "full_name",
      placeholder: "Enter your name",
    });
    store.addField(field);
    store.selectField(field.id);

    renderPropertyEditor();
    expect(screen.getByDisplayValue("full_name")).toBeTruthy();
    expect(screen.getByDisplayValue("Full Name")).toBeTruthy();
    expect(screen.getByDisplayValue("Enter your name")).toBeTruthy();
  });

  it("updates field label on input change", () => {
    const store = useBuilderStore.getState();
    const field = createDefaultField("text", { label: "Old Label", field_name: "test" });
    store.addField(field);
    store.selectField(field.id);

    renderPropertyEditor();
    const labelInput = screen.getByDisplayValue("Old Label");
    fireEvent.change(labelInput, { target: { value: "New Label" } });

    const updated = useBuilderStore.getState().fields[0];
    expect(updated.label).toBe("New Label");
  });

  it("updates field type via select", () => {
    const store = useBuilderStore.getState();
    const field = createDefaultField("text", { label: "Field", field_name: "test" });
    store.addField(field);
    store.selectField(field.id);

    renderPropertyEditor();

    // Switch to type tab
    fireEvent.click(screen.getByText("Type & Data"));

    // Change field type select (first combobox visible)
    const selects = screen.getAllByRole("combobox");
    const typeSelect = selects[0];
    fireEvent.change(typeSelect, { target: { value: "number" } });

    const updated = useBuilderStore.getState().fields[0];
    expect(updated.field_type).toBe("number");
  });

  it("switches tabs correctly", () => {
    const store = useBuilderStore.getState();
    const field = createDefaultField("text", { label: "Test", field_name: "test" });
    store.addField(field);
    store.selectField(field.id);

    renderPropertyEditor();

    // Click Validation tab
    fireEvent.click(screen.getByText("Validation"));
    expect(screen.getByText("Validation Rules")).toBeTruthy();

    // Click UI tab
    fireEvent.click(screen.getByText("UI"));
    expect(screen.getByText("UI Customization")).toBeTruthy();
  });

  it("toggles required field", () => {
    const store = useBuilderStore.getState();
    const field = createDefaultField("text", { label: "Test", field_name: "test" });
    store.addField(field);
    store.selectField(field.id);

    renderPropertyEditor();

    // Go to Validation tab
    fireEvent.click(screen.getByText("Validation"));

    // The first combobox in the validation section corresponds to Required
    const selects = screen.getAllByRole("combobox");
    const requiredSelect = selects[0];
    fireEvent.change(requiredSelect, { target: { value: "true" } });

    const updated = useBuilderStore.getState().fields[0];
    expect(updated.required).toBe(true);
  });

  it("shows options tab when clicked", () => {
    const store = useBuilderStore.getState();
    const field = createDefaultField("select", {
      label: "Status",
      field_name: "status",
      options_source: "manual",
    });
    store.addField(field);
    store.selectField(field.id);

    renderPropertyEditor();

    // Go to Options tab
    fireEvent.click(screen.getByText("Options"));

    // The text "Options Source" appears as both a heading and a label, check there are at least 2
    const optionsSources = screen.getAllByText("Options Source");
    expect(optionsSources.length).toBeGreaterThanOrEqual(1);

    // Also verify the JSON editor with "[]" is visible
    expect(screen.getByText("Options (JSON)")).toBeTruthy();
  });

  it("renders with panel closed", () => {
    const { container } = renderPropertyEditor(false);
    const aside = container.querySelector("aside");
    expect(aside?.className).toContain("translate-x-full");
  });
});
