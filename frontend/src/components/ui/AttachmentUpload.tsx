import { useState, useRef, useCallback, type DragEvent, type ChangeEvent } from "react";

const ALLOWED_TYPES = [
  "application/pdf",
  "image/jpeg",
  "image/png",
  "image/gif",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/vnd.ms-excel",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
];

const ALLOWED_EXTENSIONS = ["pdf", "jpg", "jpeg", "png", "gif", "doc", "docx", "xls", "xlsx"];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB

interface AttachmentUploadProps {
  onUpload: (file: File, description?: string) => Promise<void>;
  isUploading: boolean;
}

function getFileExtension(name: string): string {
  return name.split(".").pop()?.toLowerCase() || "";
}

function validateFile(file: File): string | null {
  const ext = getFileExtension(file.name);
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    return `File type ".${ext}" is not allowed. Allowed: ${ALLOWED_EXTENSIONS.join(", ")}`;
  }
  if (file.size > MAX_FILE_SIZE) {
    return `File size exceeds 10 MB limit (${(file.size / 1024 / 1024).toFixed(1)} MB)`;
  }
  return null;
}

function getFileIcon(mimeType: string): string {
  if (mimeType.startsWith("image/")) return "🖼";
  if (mimeType.includes("pdf")) return "📄";
  if (mimeType.includes("word") || mimeType.includes("document")) return "📝";
  if (mimeType.includes("excel") || mimeType.includes("spreadsheet")) return "📊";
  return "📎";
}

export function AttachmentUpload({ onUpload, isUploading }: AttachmentUploadProps) {
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [description, setDescription] = useState("");
  const [progress, setProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const reset = useCallback(() => {
    setSelectedFile(null);
    setDescription("");
    setProgress(0);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }, []);

  const handleFile = useCallback((file: File) => {
    setError(null);
    const err = validateFile(file);
    if (err) {
      setError(err);
      setSelectedFile(null);
      return;
    }
    setSelectedFile(file);
  }, []);

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      setDragOver(false);
      const files = e.dataTransfer.files;
      if (files.length > 0) handleFile(files[0]);
    },
    [handleFile]
  );

  const handleInputChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) handleFile(files[0]);
    },
    [handleFile]
  );

  const handleUpload = useCallback(async () => {
    if (!selectedFile) return;
    setError(null);
    setProgress(50);
    try {
      await onUpload(selectedFile, description || undefined);
      setProgress(100);
      setTimeout(reset, 1000);
    } catch {
      setError("Upload failed. Please try again.");
      setProgress(0);
    }
  }, [selectedFile, description, onUpload, reset]);

  return (
    <div className="space-y-3">
      {error && (
        <div className="rounded-md bg-danger-50 p-3 text-sm text-danger-700">{error}</div>
      )}

      {!selectedFile ? (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 transition-colors ${
            dragOver
              ? "border-primary-500 bg-primary-50"
              : "border-secondary-300 hover:border-secondary-400 bg-secondary-50"
          }`}
          onClick={() => fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click();
          }}
        >
          <svg className="mb-2 h-8 w-8 text-secondary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          <p className="text-sm text-secondary-600">
            <span className="font-medium text-primary-600">Click to upload</span> or drag and drop
          </p>
          <p className="mt-1 text-xs text-secondary-500">
            PDF, JPG, PNG, GIF, DOC, DOCX, XLS, XLSX up to 10 MB
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept={ALLOWED_TYPES.join(",")}
            className="hidden"
            onChange={handleInputChange}
          />
        </div>
      ) : (
        <div className="rounded-lg border border-secondary-200 bg-white p-4">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{getFileIcon(selectedFile.type || "application/octet-stream")}</span>
            <div className="flex-1 min-w-0">
              <p className="truncate text-sm font-medium text-secondary-900">{selectedFile.name}</p>
              <p className="text-xs text-secondary-500">{(selectedFile.size / 1024).toFixed(1)} KB</p>
            </div>
            <button
              onClick={reset}
              className="rounded p-1 text-secondary-400 hover:text-secondary-600"
              title="Remove file"
              type="button"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Add a description (optional)"
            className="mt-2 w-full rounded-md border border-secondary-300 px-3 py-1.5 text-sm focus:border-primary-500 focus:outline-none"
            disabled={isUploading}
          />

          {isUploading && (
            <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-secondary-200">
              <div
                className="h-full rounded-full bg-primary-500 transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          )}

          <div className="mt-3 flex justify-end gap-2">
            <button
              onClick={reset}
              className="rounded-md border border-secondary-300 px-3 py-1.5 text-sm text-secondary-700 hover:bg-secondary-50"
              disabled={isUploading}
              type="button"
            >
              Cancel
            </button>
            <button
              onClick={handleUpload}
              disabled={isUploading}
              className="rounded-md bg-primary-600 px-4 py-1.5 text-sm text-white hover:bg-primary-700 disabled:opacity-50"
              type="button"
            >
              {isUploading ? "Uploading..." : "Upload"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
