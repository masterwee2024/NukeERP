import { useState, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { useConfirm } from "@/components/ui/ConfirmDialog";
import api from "@/lib/api";
import {
  Upload,
  Download,
  CheckCircle,
  RotateCcw,
  X,
  Loader2,
} from "lucide-react";

interface ImportTemplate {
  id: string;
  name: string;
  entity_type: string;
  column_definitions: { name: string; label: string; rules?: Record<string, unknown> }[];
}

interface ImportJob {
  id: string;
  template_name: string;
  file_name: string;
  status: string;
  total_rows: number;
  success_count: number;
  error_count: number;
  warning_count: number;
  rows: ImportRow[];
}

interface ImportRow {
  id: string;
  row_number: number;
  status: string;
  errors: { field: string; message: string }[];
}

interface Props {
  configKey: string;
  onClose: () => void;
  onImportComplete: () => void;
}

type Step = "template" | "upload" | "validate" | "result";

export default function ImportModal({ configKey, onClose, onImportComplete }: Props) {
  const { confirm } = useConfirm();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [step, setStep] = useState<Step>("template");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [importResult, setImportResult] = useState<Record<string, unknown> | null>(null);

  const { data: template, isLoading: templateLoading } = useQuery({
    queryKey: ["import-template-by-page", configKey],
    queryFn: async (): Promise<ImportTemplate> => {
      const { data } = await api.get(`/core/import/templates/by-page/${configKey}/`);
      return data;
    },
    retry: false,
  });

  const { data: currentJob } = useQuery({
    queryKey: ["import-job", currentJobId],
    queryFn: async (): Promise<ImportJob> => {
      const { data } = await api.get(`/core/import/jobs/${currentJobId}/`);
      return data;
    },
    enabled: !!currentJobId,
    refetchInterval: (query) => {
      const job = query.state.data;
      if (job && (job.status === "validating" || job.status === "importing")) return 2000;
      return false;
    },
  });

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  }

  async function handleUpload() {
    if (!template || !selectedFile) return;
    const ok = await confirm({
      title: "Upload CSV",
      message: `Upload "${selectedFile.name}" for ${template.name}?`,
      variant: "info",
      confirmText: "Upload",
    });
    if (!ok) return;

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("entity_type", template.entity_type);

    try {
      const { data } = await api.post("/core/import/upload/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setCurrentJobId((data as { job_id: string }).job_id);
      setStep("validate");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Upload failed";
      await confirm({ title: "Upload Failed", message: msg, variant: "danger", confirmText: "OK" });
    }
  }

  async function handleValidate() {
    if (!currentJobId) return;
    try {
      await api.post(`/core/import/jobs/${currentJobId}/validate/`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Validation failed";
      await confirm({ title: "Error", message: msg, variant: "danger", confirmText: "OK" });
    }
  }

  async function handleImport() {
    if (!currentJobId) return;
    const ok = await confirm({
      title: "Execute Import",
      message: "Import all valid rows? This cannot be undone.",
      variant: "warning",
      confirmText: "Import",
    });
    if (!ok) return;

    try {
      const { data } = await api.post(`/core/import/jobs/${currentJobId}/import/`);
      setImportResult(data as Record<string, unknown>);
      setStep("result");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Import failed";
      await confirm({ title: "Error", message: msg, variant: "danger", confirmText: "OK" });
    }
  }

  async function handleRollback() {
    if (!currentJobId) return;
    const ok = await confirm({
      title: "Rollback Import",
      message: "Delete all records imported by this job?",
      variant: "danger",
      confirmText: "Rollback",
    });
    if (!ok) return;

    try {
      await api.post(`/core/import/jobs/${currentJobId}/rollback/`);
      setStep("template");
      setCurrentJobId(null);
      setSelectedFile(null);
      onImportComplete();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Rollback failed";
      await confirm({ title: "Error", message: msg, variant: "danger", confirmText: "OK" });
    }
  }

  function handleDone() {
    onImportComplete();
    onClose();
  }

  if (templateLoading) {
    return (
      <Overlay onClose={onClose}>
        <div className="flex h-48 items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-primary-500" />
        </div>
      </Overlay>
    );
  }

  if (!template) {
    return (
      <Overlay onClose={onClose}>
        <div className="p-6 text-center">
          <p className="text-sm text-secondary-500">No import template available for this page.</p>
          <button onClick={onClose} className="mt-4 rounded-lg bg-primary-600 px-4 py-2 text-sm text-white">
            Close
          </button>
        </div>
      </Overlay>
    );
  }

  return (
    <Overlay onClose={onClose}>
      <div className="p-4 md:p-6">
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-secondary-900">
            Import {template.name}
          </h2>
          <button onClick={onClose} className="rounded p-1 text-secondary-400 hover:text-secondary-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        {step === "template" && (
          <div className="space-y-4">
            <div className="rounded-lg border border-secondary-200 bg-secondary-50 p-3">
              <p className="text-sm text-secondary-700">{template.column_definitions.length} columns</p>
              <div className="mt-2 flex flex-wrap gap-1">
                {template.column_definitions.map((col) => (
                  <span key={col.name} className="rounded bg-white px-2 py-0.5 text-xs text-secondary-600">
                    {col.label}
                  </span>
                ))}
              </div>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-secondary-700">CSV File</label>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                onChange={handleFileChange}
                className="w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm"
              />
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={handleUpload}
                disabled={!selectedFile}
                className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
              >
                <Upload className="h-4 w-4" />
                Upload & Validate
              </button>
              <a
                href={`/api/v1/core/import/templates/${template.entity_type}/csv/`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sm text-primary-600 hover:text-primary-700"
              >
                <Download className="h-3 w-3" /> CSV Template
              </a>
            </div>
          </div>
        )}

        {step === "validate" && currentJob && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-secondary-500">File:</span>{" "}
                <span className="font-medium">{currentJob.file_name}</span>
              </div>
              <div>
                <span className="text-secondary-500">Rows:</span>{" "}
                <span className="font-medium">{currentJob.total_rows}</span>
              </div>
              <div>
                <span className="text-secondary-500">Errors:</span>{" "}
                <span className={`font-medium ${currentJob.error_count > 0 ? "text-danger-600" : "text-success-600"}`}>
                  {currentJob.error_count}
                </span>
              </div>
              <div>
                <span className="text-secondary-500">Status:</span>{" "}
                <span className="font-medium">{statusLabel(currentJob.status)}</span>
              </div>
            </div>

            {currentJob.status === "uploaded" && (
              <button
                onClick={handleValidate}
                className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
              >
                <CheckCircle className="h-4 w-4" /> Validate Rows
              </button>
            )}

            {(currentJob.status === "validating" || currentJob.status === "importing") && (
              <div className="flex items-center gap-2 text-sm text-secondary-600">
                <Loader2 className="h-4 w-4 animate-spin" /> Processing...
              </div>
            )}

            {currentJob.status === "uploaded" && currentJob.error_count > 0 && (
              <div className="max-h-40 overflow-y-auto rounded-lg border border-danger-200 bg-danger-50 p-3">
                <p className="mb-1 text-xs font-semibold text-danger-700">Validation Errors</p>
                {currentJob.rows
                  ?.filter((r) => r.status === "error")
                  .slice(0, 10)
                  .map((r) => (
                    <p key={r.id} className="text-xs text-danger-600">
                      Row {r.row_number}: {r.errors?.map((e) => e.message).join("; ")}
                    </p>
                  ))}
              </div>
            )}

            {currentJob.status === "uploaded" && currentJob.error_count === 0 && currentJob.total_rows > 0 && (
              <button
                onClick={handleImport}
                className="inline-flex items-center gap-2 rounded-lg bg-success-600 px-4 py-2 text-sm font-medium text-white hover:bg-success-700"
              >
                <Upload className="h-4 w-4" /> Import {currentJob.total_rows} Rows
              </button>
            )}

            {currentJob.status === "completed" && (
              <div className="space-y-3">
                <div className="rounded-lg border border-success-200 bg-success-50 p-3">
                  <p className="text-sm font-medium text-success-700">
                    {currentJob.success_count} rows imported successfully.
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handleDone}
                    className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
                  >
                    Done
                  </button>
                  <button
                    onClick={handleRollback}
                    className="inline-flex items-center gap-2 rounded-lg border border-danger-300 px-4 py-2 text-sm font-medium text-danger-700 hover:bg-danger-50"
                  >
                    <RotateCcw className="h-4 w-4" /> Rollback
                  </button>
                </div>
              </div>
            )}

            {currentJob.status === "rolled_back" && (
              <div className="rounded-lg border border-secondary-200 bg-secondary-50 p-3">
                <p className="text-sm text-secondary-700">Import rolled back.</p>
                <button onClick={handleDone} className="mt-2 rounded-lg bg-primary-600 px-4 py-2 text-sm text-white">
                  Done
                </button>
              </div>
            )}
          </div>
        )}

        {step === "result" && importResult && (
          <div className="space-y-4">
            <div className="rounded-lg border border-secondary-200 bg-white p-4">
              {Object.entries(importResult).map(([key, val]) => (
                <div key={key} className="flex justify-between py-1 text-sm">
                  <span className="text-secondary-500">{key}</span>
                  <span className="font-medium text-secondary-900">{String(val)}</span>
                </div>
              ))}
            </div>
            <button
              onClick={handleDone}
              className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
            >
              Done
            </button>
          </div>
        )}
      </div>
    </Overlay>
  );
}

function Overlay({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 pt-10" onClick={onClose}>
      <div className="relative w-full max-w-lg rounded-lg bg-white shadow-xl mx-4" onClick={(e) => e.stopPropagation()}>
        {children}
      </div>
    </div>
  );
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    uploaded: "Uploaded",
    validating: "Validating...",
    importing: "Importing...",
    completed: "Completed",
    failed: "Failed",
    rolled_back: "Rolled Back",
  };
  return labels[status] || status;
}
