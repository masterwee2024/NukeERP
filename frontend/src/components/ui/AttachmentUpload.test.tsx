import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfirmProvider } from "@/components/ui/ConfirmDialog";
import { AttachmentUpload } from "@/components/ui/AttachmentUpload";
import { AttachmentList } from "@/components/ui/AttachmentList";
import type { ReactNode } from "react";

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

function makeFile(
  name: string,
  size: number = 1024,
  type: string = "application/pdf"
): File {
  return new File([new ArrayBuffer(size)], name, { type });
}

describe("AttachmentUpload", () => {
  const mockUpload = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders drag-and-drop zone", () => {
    render(<AttachmentUpload onUpload={mockUpload} isUploading={false} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText(/Click to upload/i)).toBeDefined();
    expect(screen.getByText(/drag and drop/i)).toBeDefined();
    expect(screen.getByText(/PDF, JPG, PNG, GIF/i)).toBeDefined();
  });

  it("accepts a valid file via click and shows file info", () => {
    render(<AttachmentUpload onUpload={mockUpload} isUploading={false} />, {
      wrapper: createWrapper(),
    });

    const file = makeFile("document.pdf", 2048, "application/pdf");
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput).not.toBeNull();

    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText("document.pdf")).toBeDefined();
    expect(screen.getByText(/2.0 KB/)).toBeDefined();
    expect(screen.getByText("Upload")).toBeDefined();
    expect(screen.getByText("Cancel")).toBeDefined();
  });

  it("shows error for invalid file type", () => {
    render(<AttachmentUpload onUpload={mockUpload} isUploading={false} />, {
      wrapper: createWrapper(),
    });

    const file = makeFile("script.exe", 1024, "application/x-msdownload");
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;

    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText(/.exe.*not allowed/i)).toBeDefined();
  });

  it("shows error for file exceeding size limit", () => {
    render(<AttachmentUpload onUpload={mockUpload} isUploading={false} />, {
      wrapper: createWrapper(),
    });

    const file = makeFile("large.pdf", 11 * 1024 * 1024, "application/pdf");
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;

    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText(/exceeds 10 MB/i)).toBeDefined();
  });

  it("calls onUpload when upload button is clicked", async () => {
    mockUpload.mockResolvedValueOnce(undefined);

    render(<AttachmentUpload onUpload={mockUpload} isUploading={false} />, {
      wrapper: createWrapper(),
    });

    const file = makeFile("doc.pdf", 4096, "application/pdf");
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [file] } });

    fireEvent.click(screen.getByText("Upload"));

    expect(mockUpload).toHaveBeenCalledWith(file, undefined);
  });

  it("shows uploading indicator after file is selected", () => {
    render(<AttachmentUpload onUpload={mockUpload} isUploading={true} />, {
      wrapper: createWrapper(),
    });

    const file = makeFile("doc.pdf", 4096, "application/pdf");
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText("Uploading...")).toBeDefined();
  });

  it("adds description and passes it to onUpload", async () => {
    mockUpload.mockResolvedValueOnce(undefined);

    render(<AttachmentUpload onUpload={mockUpload} isUploading={false} />, {
      wrapper: createWrapper(),
    });

    const file = makeFile("doc.pdf", 4096, "application/pdf");
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [file] } });

    const descInput = screen.getByPlaceholderText(/Add a description/i);
    fireEvent.change(descInput, { target: { value: "Invoice document" } });

    fireEvent.click(screen.getByText("Upload"));

    expect(mockUpload).toHaveBeenCalledWith(file, "Invoice document");
  });
});

describe("AttachmentList", () => {
  const mockAttachments = [
    {
      id: "1",
      file_name: "invoice.pdf",
      file_size: 524288,
      mime_type: "application/pdf",
      description: "Invoice document",
      uploaded_by_name: "John Doe",
      uploaded_by_id: "u1",
      created_at: "2026-06-01T10:00:00Z",
      download_url: "/api/v1/core/attachments/download/1/",
    },
    {
      id: "2",
      file_name: "photo.jpg",
      file_size: 1048576,
      mime_type: "image/jpeg",
      description: "Product photo",
      uploaded_by_name: "Jane Smith",
      uploaded_by_id: "u2",
      created_at: "2026-06-02T14:30:00Z",
      download_url: "/api/v1/core/attachments/download/2/",
    },
  ];

  const mockRemove = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders list of attachments", () => {
    render(<AttachmentList attachments={mockAttachments} onRemove={mockRemove} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("invoice.pdf")).toBeDefined();
    expect(screen.getByText("photo.jpg")).toBeDefined();
    expect(screen.getByText(/John Doe/)).toBeDefined();
    expect(screen.getByText(/Jane Smith/)).toBeDefined();
  });

  it("shows file sizes formatted", () => {
    render(<AttachmentList attachments={mockAttachments} onRemove={mockRemove} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText(/512.0 KB/)).toBeDefined();
    expect(screen.getByText(/1.0 MB/)).toBeDefined();
  });

  it("shows empty state when no attachments", () => {
    render(<AttachmentList attachments={[]} onRemove={mockRemove} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText(/No attachments yet/i)).toBeDefined();
  });

  it("shows loading spinner when isLoading is true", () => {
    const { container } = render(
      <AttachmentList attachments={[]} onRemove={mockRemove} isLoading={true} />,
      { wrapper: createWrapper() }
    );

    const spinner = container.querySelector(".animate-spin");
    expect(spinner).toBeDefined();
  });

  it("renders download links", () => {
    render(<AttachmentList attachments={mockAttachments} onRemove={mockRemove} />, {
      wrapper: createWrapper(),
    });

    const links = document.querySelectorAll("a[download]");
    expect(links.length).toBe(2);
    expect(links[0].getAttribute("href")).toBe("/api/v1/core/attachments/download/1/");
  });
});
