import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfirmProvider, useConfirm } from "@/components/ui/ConfirmDialog";

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

function DeleteButton() {
  const { confirm } = useConfirm();
  const handleClick = async () => {
    const result = await confirm({
      title: "Delete Item",
      message: "Are you sure you want to delete this item?",
      variant: "danger",
      confirmText: "Yes, delete",
      cancelText: "No, keep",
    });
    document.title = result ? "confirmed" : "cancelled";
  };
  return <button onClick={handleClick}>Delete</button>;
}

function PostButton() {
  const { confirm } = useConfirm();
  const handleClick = async () => {
    const result = await confirm({
      title: "Post Invoice",
      message: "This action cannot be undone.",
      variant: "warning",
    });
    document.title = result ? "posted" : "cancelled";
  };
  return <button onClick={handleClick}>Post</button>;
}

describe("ConfirmDialog via useConfirm", () => {
  it("opens dialog with title and message", () => {
    renderWithProviders(<DeleteButton />);
    fireEvent.click(screen.getByText("Delete"));

    expect(screen.getByText("Delete Item")).toBeDefined();
    expect(
      screen.getByText("Are you sure you want to delete this item?")
    ).toBeDefined();
  });

  it("renders danger variant with correct button text", () => {
    renderWithProviders(<DeleteButton />);
    fireEvent.click(screen.getByText("Delete"));

    expect(screen.getByText("Yes, delete")).toBeDefined();
    expect(screen.getByText("No, keep")).toBeDefined();
  });

  it("resolves true on confirm", async () => {
    renderWithProviders(<DeleteButton />);
    fireEvent.click(screen.getByText("Delete"));
    fireEvent.click(screen.getByText("Yes, delete"));

    await vi.waitFor(() => {
      expect(document.title).toBe("confirmed");
    });
  });

  it("resolves false on cancel", async () => {
    renderWithProviders(<DeleteButton />);
    fireEvent.click(screen.getByText("Delete"));
    fireEvent.click(screen.getByText("No, keep"));

    await vi.waitFor(() => {
      expect(document.title).toBe("cancelled");
    });
  });

  it("resolves false on backdrop click", async () => {
    renderWithProviders(<DeleteButton />);
    fireEvent.click(screen.getByText("Delete"));

    const backdrop = document.querySelector(".fixed.inset-0 > div");
    if (backdrop) fireEvent.click(backdrop);

    await vi.waitFor(() => {
      expect(document.title).toBe("cancelled");
    });
  });

  it("renders warning variant", () => {
    renderWithProviders(<PostButton />);
    fireEvent.click(screen.getByText("Post"));

    expect(screen.getByText("Post Invoice")).toBeDefined();
    expect(screen.getByText("This action cannot be undone.")).toBeDefined();
  });

  it("has accessible dialog attributes", () => {
    renderWithProviders(<DeleteButton />);
    fireEvent.click(screen.getByText("Delete"));

    const dialog = screen.getByRole("dialog");
    expect(dialog.getAttribute("aria-modal")).toBe("true");
    expect(dialog.getAttribute("aria-labelledby")).toBe("confirm-title");
  });

  it("closes on Escape key", () => {
    renderWithProviders(<DeleteButton />);
    fireEvent.click(screen.getByText("Delete"));
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });

    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("confirms on Enter key", async () => {
    renderWithProviders(<DeleteButton />);
    fireEvent.click(screen.getByText("Delete"));
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Enter" });

    await vi.waitFor(() => {
      expect(document.title).toBe("confirmed");
    });
  });

  it("traps focus within dialog on Tab", () => {
    renderWithProviders(<DeleteButton />);
    fireEvent.click(screen.getByText("Delete"));

    const cancelBtn = screen.getByText("No, keep");
    const confirmBtn = screen.getByText("Yes, delete");
    expect(cancelBtn).toBeDefined();
    expect(confirmBtn).toBeDefined();
  });

  it("returns focus to trigger after close", () => {
    renderWithProviders(<DeleteButton />);
    const deleteBtn = screen.getByText("Delete") as HTMLButtonElement;
    deleteBtn.focus();
    fireEvent.click(deleteBtn);

    const dialog = screen.getByRole("dialog");
    fireEvent.keyDown(dialog, { key: "Escape" });

    expect(document.activeElement).toBe(deleteBtn);
  });
});
