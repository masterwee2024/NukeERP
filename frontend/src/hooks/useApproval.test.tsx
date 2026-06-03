import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfirmProvider } from "@/components/ui/ConfirmDialog";
import {
  useApproval,
  usePendingApprovals,
} from "@/hooks/useApproval";
import type { ReactNode } from "react";

vi.mock("@/components/ui/ConfirmDialog", () => ({
  useConfirm: () => ({
    confirm: () => Promise.resolve(true),
  }),
  ConfirmProvider: ({ children }: { children: ReactNode }) => children,
}));

vi.mock("axios", () => {
  const mockPost = vi.fn();
  const mockGet = vi.fn();
  return {
    default: {
      post: mockPost,
      get: mockGet,
      create: vi.fn(() => ({
        post: mockPost,
        get: mockGet,
        interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
      })),
    },
  };
});

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <ConfirmProvider>{children}</ConfirmProvider>
      </QueryClientProvider>
    );
  };
}

describe("useApproval", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("provides approve, reject, delegate, execute functions", () => {
    const { result } = renderHook(() => useApproval(), {
      wrapper: createWrapper(),
    });

    expect(result.current.approve).toBeInstanceOf(Function);
    expect(result.current.reject).toBeInstanceOf(Function);
    expect(result.current.delegate).toBeInstanceOf(Function);
    expect(result.current.execute).toBeInstanceOf(Function);
  });

  it("tracks isPending state", () => {
    const { result } = renderHook(() => useApproval(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isPending).toBe(false);
  });

  it("returns no error initially", () => {
    const { result } = renderHook(() => useApproval(), {
      wrapper: createWrapper(),
    });

    expect(result.current.error).toBeNull();
  });
});

describe("usePendingApprovals", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches pending approvals", async () => {
    const pendingData = {
      count: 1,
      results: [
        {
          step_id: "step-1",
          execution_id: "exec-1",
          workflow_name: "Test Workflow",
          document_type: "PO",
          document_id: "doc-1",
          node_label: "Manager Approval",
          node_type: "approve",
          requested_at: "2026-06-01T00:00:00Z",
          requester: { id: "user-1", name: "Requester", email: "r@t.com" },
          company_id: "comp-1",
        },
      ],
    };

    const axios = await import("axios");
    vi.mocked(axios.default.get).mockResolvedValue({ data: pendingData });

    const { result } = renderHook(() => usePendingApprovals(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.count).toBe(1);
    expect(result.current.data?.results[0].workflow_name).toBe("Test Workflow");
  });

  it("returns empty results when no pending approvals", async () => {
    const axios = await import("axios");
    vi.mocked(axios.default.get).mockResolvedValue({
      data: { count: 0, results: [] },
    });

    const { result } = renderHook(() => usePendingApprovals(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.count).toBe(0);
  });
});
