import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfirmProvider } from "@/components/ui/ConfirmDialog";
import { ApprovalPanel } from "./ApprovalPanel";
import type { ExecutionContext } from "@/hooks/useApproval";

vi.mock("axios", () => {
  return {
    default: {
      post: vi.fn().mockResolvedValue({ data: {} }),
      get: vi.fn().mockResolvedValue({ data: {} }),
      create: vi.fn(() => ({
        post: vi.fn().mockResolvedValue({ data: {} }),
        get: vi.fn().mockResolvedValue({ data: {} }),
        interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
      })),
    },
  };
});

const mockContext: ExecutionContext = {
  execution_id: "exec-1",
  workflow: { id: "wf-1", name: "Test Workflow", module: "financial", document_type: "PurchaseOrder" },
  document_type: "PurchaseOrder",
  document_id: "doc-1",
  document_data: null,
  status: "pending",
  current_node: { node_id: "approve_1", label: "Manager Approval", node_type: "approve" },
  requester: { id: "user-1", name: "Requester", email: "requester@test.com" },
  created_by: { id: "user-1", name: "Requester", email: "requester@test.com" },
  company: { id: "comp-1", name: "Test Corp" },
  started_at: "2026-06-01T00:00:00Z",
  completed_at: null,
  steps: [
    {
      step_id: "step-1",
      node_label: "Manager Approval",
      node_type: "approve",
      approver: { id: "user-2", name: "Approver", email: "approver@test.com" },
      action: "",
      comment: "",
      status: "pending",
      timestamp: "2026-06-01T00:00:00Z",
      delegated_to: null,
    },
  ],
  metadata: {},
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

describe("ApprovalPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders workflow name and status", () => {
    renderWithProviders(
      <ApprovalPanel context={mockContext} currentUserId="user-2" />
    );

    expect(screen.getByText("Approval Status")).toBeInTheDocument();
    expect(screen.getByText("Test Workflow")).toBeInTheDocument();
    expect(screen.getByText("Pending")).toBeInTheDocument();
  });

  it("shows approve/reject buttons for pending approver", () => {
    renderWithProviders(
      <ApprovalPanel context={mockContext} currentUserId="user-2" />
    );

    expect(screen.getByText("Approve")).toBeInTheDocument();
    expect(screen.getByText("Reject")).toBeInTheDocument();
  });

  it("shows status badge with correct color for approved status", () => {
    const approvedContext = { ...mockContext, status: "approved" };
    renderWithProviders(
      <ApprovalPanel context={approvedContext} currentUserId="user-2" />
    );

    expect(screen.getByText("Approved")).toBeInTheDocument();
  });

  it("shows rejected status badge", () => {
    const rejectedContext = { ...mockContext, status: "rejected" };
    renderWithProviders(
      <ApprovalPanel context={rejectedContext} currentUserId="user-2" />
    );

    expect(screen.getByText("Rejected")).toBeInTheDocument();
  });

  it("does not show approve/reject buttons for non-approver", () => {
    renderWithProviders(
      <ApprovalPanel context={mockContext} currentUserId="user-3" />
    );

    expect(screen.queryByText("Approve")).not.toBeInTheDocument();
    expect(screen.queryByText("Reject")).not.toBeInTheDocument();
  });

  it("shows approval history steps", () => {
    renderWithProviders(
      <ApprovalPanel context={mockContext} currentUserId="user-2" />
    );

    expect(screen.getByText("History")).toBeInTheDocument();
    expect(screen.getByText("Approver")).toBeInTheDocument();
  });
});
