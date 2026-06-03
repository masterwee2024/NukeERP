import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { DndContext } from "@dnd-kit/core";
import { useBuilderStore, createDefaultField } from "../builderStore";
import ComponentPalette from "../ComponentPalette";

// Wrap palette in DndContext for draggable test
function PaletteWithDnd({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <DndContext>
      <ComponentPalette open={open} onClose={onClose} />
    </DndContext>
  );
}

describe("PageBuilder - ComponentPalette", () => {
  beforeEach(() => {
    useBuilderStore.getState().reset();
  });

  it("renders palette categories", () => {
    render(<PaletteWithDnd open={true} onClose={() => {}} />);
    expect(screen.getByText("Input Fields")).toBeTruthy();
    expect(screen.getByText("Selection")).toBeTruthy();
    expect(screen.getByText("Date/Time")).toBeTruthy();
    expect(screen.getByText("Display")).toBeTruthy();
  });

  it("renders draggable items for Input Fields", () => {
    render(<PaletteWithDnd open={true} onClose={() => {}} />);
    expect(screen.getByText("Text")).toBeTruthy();
    expect(screen.getByText("Number")).toBeTruthy();
    expect(screen.getByText("Email")).toBeTruthy();
    expect(screen.getByText("Textarea")).toBeTruthy();
  });

  it("shows close button on mobile", () => {
    render(<PaletteWithDnd open={true} onClose={() => {}} />);
    const closeBtn = screen.getByLabelText("Close palette");
    expect(closeBtn).toBeTruthy();
  });

  it("renders hidden when open is false", () => {
    const { container } = render(
      <PaletteWithDnd open={false} onClose={() => {}} />
    );
    const aside = container.querySelector("aside");
    expect(aside?.className).toContain("-translate-x-full");
  });

  it("renders visible when open is true", () => {
    const { container } = render(
      <PaletteWithDnd open={true} onClose={() => {}} />
    );
    const aside = container.querySelector("aside");
    expect(aside?.className).toContain("translate-x-0");
  });
});

describe("PageBuilder - builderStore", () => {
  beforeEach(() => {
    useBuilderStore.getState().reset();
  });

  it("starts with empty fields", () => {
    const state = useBuilderStore.getState();
    expect(state.fields).toEqual([]);
    expect(state.selectedFieldId).toBeNull();
    expect(state.isDirty).toBe(false);
  });

  it("adds a field", () => {
    const field = createDefaultField("text", { label: "Test Field" });
    useBuilderStore.getState().addField(field);
    const state = useBuilderStore.getState();
    expect(state.fields).toHaveLength(1);
    expect(state.fields[0].label).toBe("Test Field");
    expect(state.fields[0].field_type).toBe("text");
    expect(state.isDirty).toBe(true);
  });

  it("adds field after a specific field", () => {
    const field1 = createDefaultField("text", { label: "First" });
    const field2 = createDefaultField("number", { label: "Second" });
    useBuilderStore.getState().addField(field1);
    useBuilderStore.getState().addField(field2, field1.id);
    const state = useBuilderStore.getState();
    expect(state.fields).toHaveLength(2);
    expect(state.fields[0].label).toBe("First");
    expect(state.fields[1].label).toBe("Second");
  });

  it("updates a field", () => {
    const field = createDefaultField("text", { label: "Original" });
    useBuilderStore.getState().addField(field);
    useBuilderStore.getState().updateField(field.id, { label: "Updated" });
    const state = useBuilderStore.getState();
    expect(state.fields[0].label).toBe("Updated");
  });

  it("removes a field", () => {
    const field = createDefaultField("text");
    useBuilderStore.getState().addField(field);
    useBuilderStore.getState().removeField(field.id);
    const state = useBuilderStore.getState();
    expect(state.fields).toHaveLength(0);
  });

  it("reorders fields", () => {
    const f1 = createDefaultField("text", { label: "A" });
    const f2 = createDefaultField("number", { label: "B" });
    useBuilderStore.getState().addField(f1);
    useBuilderStore.getState().addField(f2);
    useBuilderStore.getState().reorderFields(0, 1);
    const state = useBuilderStore.getState();
    expect(state.fields[0].label).toBe("B");
    expect(state.fields[1].label).toBe("A");
  });

  it("selects a field", () => {
    const field = createDefaultField("text");
    useBuilderStore.getState().addField(field);
    useBuilderStore.getState().selectField(field.id);
    expect(useBuilderStore.getState().selectedFieldId).toBe(field.id);
  });

  it("clears selection on remove of selected field", () => {
    const field = createDefaultField("text");
    useBuilderStore.getState().addField(field);
    useBuilderStore.getState().selectField(field.id);
    useBuilderStore.getState().removeField(field.id);
    expect(useBuilderStore.getState().selectedFieldId).toBeNull();
  });

  it("sets config", () => {
    useBuilderStore.getState().setConfig({ page_title: "Test Page" });
    expect(useBuilderStore.getState().config.page_title).toBe("Test Page");
    expect(useBuilderStore.getState().isDirty).toBe(true);
  });

  it("sets fields and marks clean", () => {
    const fields = [createDefaultField("text")];
    useBuilderStore.getState().setFields(fields);
    expect(useBuilderStore.getState().fields).toHaveLength(1);
    expect(useBuilderStore.getState().isDirty).toBe(false);
  });

  it("toggles preview mode", () => {
    expect(useBuilderStore.getState().previewMode).toBe("desktop");
    useBuilderStore.getState().setPreviewMode("mobile");
    expect(useBuilderStore.getState().previewMode).toBe("mobile");
  });

  it("resets to initial state", () => {
    useBuilderStore.getState().addField(createDefaultField("text"));
    useBuilderStore.getState().setConfig({ page_title: "Test" });
    useBuilderStore.getState().reset();
    const state = useBuilderStore.getState();
    expect(state.fields).toEqual([]);
    expect(state.selectedFieldId).toBeNull();
    expect(state.config).toEqual({});
    expect(state.isDirty).toBe(false);
  });
});

describe("createDefaultField", () => {
  it("creates field with default values", () => {
    const field = createDefaultField("text");
    expect(field.field_type).toBe("text");
    expect(field.data_type).toBe("string");
    expect(field.required).toBe(false);
    expect(field.col_span).toBe(6);
    expect(field.id).toBeTruthy();
    expect(field.field_name).toBe(`field_${field.id}`);
  });

  it("merges base overrides", () => {
    const field = createDefaultField("number", { label: "My Number", required: true });
    expect(field.field_type).toBe("number");
    expect(field.label).toBe("My Number");
    expect(field.required).toBe(true);
  });

  it("creates field with unique id each time", () => {
    const f1 = createDefaultField("text");
    const f2 = createDefaultField("text");
    expect(f1.id).not.toBe(f2.id);
  });
});
