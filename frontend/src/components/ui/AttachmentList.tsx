import { useConfirm } from "@/components/ui/ConfirmDialog";
import type { Attachment } from "@/hooks/useAttachments";

interface AttachmentListProps {
  attachments: Attachment[];
  onRemove: (id: string) => Promise<void>;
  onDownload?: (attachment: Attachment) => void;
  isLoading?: boolean;
}

function formatFileSize(bytes: number): string {
  if (bytes >= 1048576) return `${(bytes / 1048576).toFixed(1)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${bytes} B`;
}

function getFileIcon(mimeType: string): string {
  if (mimeType.startsWith("image/")) return "🖼";
  if (mimeType.includes("pdf")) return "📄";
  if (mimeType.includes("word") || mimeType.includes("document")) return "📝";
  if (mimeType.includes("excel") || mimeType.includes("spreadsheet")) return "📊";
  return "📎";
}

function formatDate(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString("en-MY", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function AttachmentList({
  attachments,
  onRemove,
  isLoading,
}: AttachmentListProps) {
  const { confirm } = useConfirm();

  async function handleDelete(attachment: Attachment) {
    const confirmed = await confirm({
      title: "Delete Attachment",
      message: `Are you sure you want to delete "${attachment.file_name}"?`,
      variant: "danger",
      confirmText: "Yes, delete",
      cancelText: "Cancel",
    });
    if (confirmed) {
      await onRemove(attachment.id);
    }
  }

  function handlePreview(attachment: Attachment) {
    if (attachment.mime_type.startsWith("image/")) {
      window.open(attachment.download_url, "_blank");
    } else if (attachment.mime_type.includes("pdf")) {
      window.open(attachment.download_url, "_blank");
    } else {
      window.open(attachment.download_url, "_blank");
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-500 border-t-transparent" />
      </div>
    );
  }

  if (attachments.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-secondary-500">
        No attachments yet
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {attachments.map((attachment) => (
        <div
          key={attachment.id}
          className="flex items-center gap-3 rounded-lg border border-secondary-200 bg-white p-3 transition-colors hover:bg-secondary-50"
        >
          <button
            onClick={() => handlePreview(attachment)}
            className="shrink-0 text-2xl hover:opacity-75"
            title="Preview"
            type="button"
          >
            {getFileIcon(attachment.mime_type)}
          </button>

          <div className="flex-1 min-w-0">
            <p className="truncate text-sm font-medium text-secondary-900">
              {attachment.file_name}
            </p>
            <p className="text-xs text-secondary-500">
              {formatFileSize(attachment.file_size)}
              {attachment.uploaded_by_name ? ` by ${attachment.uploaded_by_name}` : ""}
              {attachment.created_at ? ` · ${formatDate(attachment.created_at)}` : ""}
            </p>
          </div>

          <div className="flex shrink-0 items-center gap-1">
            <a
              href={attachment.download_url}
              target="_blank"
              rel="noopener noreferrer"
              download={attachment.file_name}
              className="rounded p-1.5 text-secondary-400 hover:bg-secondary-100 hover:text-secondary-600"
              title="Download"
            >
              <svg
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </a>
            <button
              onClick={() => handleDelete(attachment)}
              className="rounded p-1.5 text-secondary-400 hover:bg-danger-50 hover:text-danger-600"
              title="Delete"
              type="button"
            >
              <svg
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
