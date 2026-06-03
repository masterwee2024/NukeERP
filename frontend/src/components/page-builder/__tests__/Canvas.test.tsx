import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { useBuilderStore, createDefaultField } from "../builderStore";
import Canvas from "../Canvas";

// Mock requestAnimationFrame and cancelAnimationFrame for jsdom
beforeEach(() => {
  vi.useFakeTimers();
  let rafId = 0;
  const rafCalls: Array<FrameRequestCallback> = [];
  vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb: FrameRequestCallback) => {
    rafId += 1;
    rafCalls.push(cb);
    return rafId;
  });
  vi.spyOn(window, "cancelAnimationFrame").mockImplementation((_id: number) => {
    // no-op
  });
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

function renderCanvas() {
  return render(<Canvas />);
}

describe("Canvas", () => {
  beforeEach(() => {
    useBuilderStore.getState().reset();
  });

  it("shows empty state when no fields", () => {
    renderCanvas();
    expect(screen.getByText("Empty Form")).toBeTruthy();
    expect(
      screen.getByText("Drag components from the palette to start building")
    ).toBeTruthy();
  });

  it("renders fields from store", () => {
    const store = useBuilderStore.getState();
    const field = createDefaultField("text", {
      label: "Username",
      field_name: "username",
      placeholder: "Enter username",
    });
    store.addField(field);

    renderCanvas();
    expect(screen.getByText("Username")).toBeTruthy();
    expect(screen.getByText("Enter username")).toBeTruthy();
  });

  it("renders field type label", () => {
    const store = useBuilderStore.getState();
    const field = createDefaultField("number", { label: "Age" });
    store.addField(field);

    renderCanvas();
    expect(screen.getByText("Number")).toBeTruthy();
  });

  it("shows required indicator for required fields", () => {
    const store = useBuilderStore.getState();
    const field = createDefaultField("text", { label: "Email", required: true });
    store.addField(field);

    renderCanvas();
    expect(screen.getByText("*")).toBeTruthy();
  });

  it("shows Hidden badge for hidden fields", () => {
    const store = useBuilderStore.getState();
    const field = createDefaultField("text", { label: "Hidden Field", hidden: true });
    store.addField(field);

    renderCanvas();
    expect(screen.getByText("Hidden")).toBeTruthy();
  });

  it("selects field on click", () => {
    const store = useBuilderStore.getState();
    const field = createDefaultField("text", { label: "Clickable" });
    store.addField(field);

    renderCanvas();
    const fieldEl = screen.getByText("Clickable");
    fireEvent.click(fieldEl);

    expect(useBuilderStore.getState().selectedFieldId).toBe(field.id);
  });

  it("removes field when remove button clicked", () => {
    const store = useBuilderStore.getState();
    const field = createDefaultField("text", { label: "Remove Me" });
    store.addField(field);

    renderCanvas();
    const removeBtn = screen.getByLabelText(`Remove ${field.field_name}`);
    fireEvent.click(removeBtn);

    expect(screen.queryByText("Remove Me")).toBeNull();
    expect(useBuilderStore.getState().fields).toHaveLength(0);
  });

  it("renders fields in a group", () => {
    const store = useBuilderStore.getState();
    const f1 = createDefaultField("text", { label: "Grouped Field", group_name: "Details" });
    store.addField(f1);

    renderCanvas();
    expect(screen.getByText("Details")).toBeTruthy();
    expect(screen.getByText("Grouped Field")).toBeTruthy();
  });

  it("renders ungrouped fields without group header", () => {
    const store = useBuilderStore.getState();
    const f1 = createDefaultField("text", { label: "Ungrouped" });
    store.addField(f1);

    renderCanvas();
    expect(screen.queryByText("_UNGROUPED")).toBeNull();
  });
});
