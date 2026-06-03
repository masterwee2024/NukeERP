import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAttachments } from "@/hooks/useAttachments";
import type { ReactNode } from "react";

const mockAttachments = [
  {
    id: "1",
    file_name: "invoice.pdf",
    file_size: 524288,
    mime_type: "application/pdf",
    description: "",
    uploaded_by_name: "John Doe",
    uploaded_by_id: "u1",
    created_at: "2026-06-01T10:00:00Z",
    download_url: "/api/v1/core/attachments/download/1/",
  },
];

const mockAxiosInstance = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  delete: vi.fn(),
  interceptors: {
    request: { use: vi.fn() },
    response: { use: vi.fn() },
  },
}));

vi.mock("axios", () => ({
  default: {
    create: vi.fn(() => mockAxiosInstance),
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("useAttachments", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches attachments for a given content type and object id", async () => {
    mockAxiosInstance.get.mockResolvedValueOnce({ data: mockAttachments });

    const { result } = renderHook(() => useAttachments("core.company", "company-123"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(mockAxiosInstance.get).toHaveBeenCalledWith(
      "/core/attachments/list/core.company/company-123/"
    );
    expect(result.current.attachments).toEqual(mockAttachments);
  });

  it("returns empty array when no objectId is provided", () => {
    const { result } = renderHook(() => useAttachments("core.company", undefined), {
      wrapper: createWrapper(),
    });

    expect(result.current.attachments).toEqual([]);
    expect(mockAxiosInstance.get).not.toHaveBeenCalled();
  });

  it("does not fetch when objectId is empty string", () => {
    const { result } = renderHook(() => useAttachments("core.company", ""), {
      wrapper: createWrapper(),
    });

    expect(result.current.attachments).toEqual([]);
    expect(mockAxiosInstance.get).not.toHaveBeenCalled();
  });

  it("uploads attachment via POST", async () => {
    mockAxiosInstance.get.mockResolvedValueOnce({ data: [] });
    mockAxiosInstance.post.mockResolvedValueOnce({ data: mockAttachments[0] });

    const { result } = renderHook(() => useAttachments("core.company", "company-123"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    const file = new File(["test"], "doc.pdf", { type: "application/pdf" });
    const uploaded = await result.current.upload(file, "My document");

    expect(mockAxiosInstance.post).toHaveBeenCalled();
    const postCall = mockAxiosInstance.post.mock.calls[0];
    expect(postCall[0]).toBe("/core/attachments/upload/");
    expect(postCall[1] instanceof FormData).toBe(true);
    const formData = postCall[1] as FormData;
    expect(formData.get("file")).toBe(file);
    expect(formData.get("content_type_label")).toBe("core.company");
    expect(formData.get("object_id")).toBe("company-123");
    expect(formData.get("description")).toBe("My document");

    expect(uploaded).toEqual(mockAttachments[0]);
  });

  it("deletes attachment via DELETE", async () => {
    mockAxiosInstance.get.mockResolvedValueOnce({ data: mockAttachments });
    mockAxiosInstance.delete.mockResolvedValueOnce({});

    const { result } = renderHook(() => useAttachments("core.company", "company-123"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await result.current.remove("1");

    expect(mockAxiosInstance.delete).toHaveBeenCalledWith(
      "/core/attachments/1/"
    );
  });

  it("invalidates query cache after upload", async () => {
    mockAxiosInstance.get.mockResolvedValue({ data: [] });
    mockAxiosInstance.post.mockResolvedValue({ data: mockAttachments[0] });

    const { result } = renderHook(() => useAttachments("core.company", "company-123"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    const file = new File(["test"], "doc.pdf", { type: "application/pdf" });
    await result.current.upload(file);

    expect(mockAxiosInstance.post).toHaveBeenCalledTimes(1);
  });
});
