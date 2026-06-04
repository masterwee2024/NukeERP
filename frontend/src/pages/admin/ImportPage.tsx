import { useState, useRef, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useConfirm } from "@/components/ui/ConfirmDialog";
import api from "@/lib/api";
import {
  Upload,
  Download,
  CheckCircle,
  AlertCircle,
  RotateCcw,
  ArrowLeft,
  Loader2,
  FileText,
  Search,
} from "lucide-react";

interface ImportTemplate {
  id: string;
  name: string;
  entity_type: string;
  description: string;
  column_definitions: { name: string; label: string }[];
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
  started_at: string | null;
  completed_at: string | null;
  error_log: string;
  rows: ImportRow[];
}

interface ImportRow {
  id: string;
  row_number: number;
  raw_data: unknown;
  mapped_data: unknown;
  status: string;
  errors: { field: string; message: string }[];
  warnings: { message: string }[];
}

interface HistoryItem {
  id: string;
  entity_type: string;
  action: string;
  record_count: number;
  performed_by_name: string;
  notes: string;
  created_at: string;
}

type Step = "templates" | "upload" | "mapping" | "validate" | "result";

export default function ImportPage() {
  const { confirm } = useConfirm();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [step, setStep] = useState<Step>("templates");
  const [selectedTemplate, setSelectedTemplate] = useState<ImportTemplate | null>(null);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [importResult, setImportResult] = useState<Record<string, unknown> | null>(null);
  const [search, setSearch] = useState("");
  const [reloadStatus, setReloadStatus] = useState<"idle" | "reloading" | "done" | "uptodate" | "failed">("idle");

  const { data: templates = [], isLoading: templatesLoading } = useQuery({
    queryKey: ["import-templates"],
    queryFn: async () => {
      const { data } = await api.get("/core/import/templates/");
      return (data?.results ?? data ?? []) as ImportTemplate[];
    },
  });

  const { data: history = [] } = useQuery({
    queryKey: ["import-history"],
    queryFn: async () => {
      const { data } = await api.get("/core/import/history/");
      return (data?.results ?? data ?? []) as HistoryItem[];
    },
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
      if (job && (job.status === "validating" || job.status === "importing")) {
        return 2000;
      }
      return false;
    },
  });

  const totalHistory = history.length;
  const recentHistory = history.slice(0, 20);

  const filteredTemplates = useMemo(() => {
    if (!search) return templates;
    const q = search.toLowerCase();
    return templates.filter(
      (t) =>
        t.name.toLowerCase().includes(q) ||
        t.entity_type.toLowerCase().includes(q)
    );
  }, [templates, search]);

  function selectTemplate(t: ImportTemplate) {
    setSelectedTemplate(t);
    setStep("upload");
    setSelectedFile(null);
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  }

  async function handleUpload() {
    if (!selectedTemplate || !selectedFile) return;
    const ok = await confirm({
      title: "Upload CSV",
      message: `Upload "${selectedFile.name}" for ${selectedTemplate.name}?`,
      variant: "info",
      confirmText: "Upload",
    });
    if (!ok) return;

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("entity_type", selectedTemplate.entity_type);

    try {
      const { data } = await api.post("/core/import/upload/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setCurrentJobId((data as { job_id: string }).job_id);
      setStep("validate");
      queryClient.invalidateQueries({ queryKey: ["import-history"] });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Upload failed";
      await confirm({
        title: "Upload Failed",
        message: msg,
        variant: "danger",
        confirmText: "OK",
      });
    }
  }

  async function handleValidate() {
    if (!currentJobId) return;
    try {
      await api.post(`/core/import/jobs/${currentJobId}/validate/`);
      queryClient.invalidateQueries({ queryKey: ["import-job", currentJobId] });
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
      queryClient.invalidateQueries({ queryKey: ["import-history"] });
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
      const { data } = await api.post(`/core/import/jobs/${currentJobId}/rollback/`);
      setImportResult(data as Record<string, unknown>);
      queryClient.invalidateQueries({ queryKey: ["import-history"] });
      queryClient.invalidateQueries({ queryKey: ["import-job", currentJobId] });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Rollback failed";
      await confirm({ title: "Error", message: msg, variant: "danger", confirmText: "OK" });
    }
  }

  function reset() {
    setStep("templates");
    setSelectedTemplate(null);
    setCurrentJobId(null);
    setSelectedFile(null);
    setImportResult(null);
  }

  if (step === "upload" && selectedTemplate) {
    return (
      <div className="p-4 md:p-6 max-w-2xl">
        <button
          onClick={() => setStep("templates")}
          className="mb-4 inline-flex items-center gap-1 text-sm text-secondary-600 hover:text-secondary-900"
        >
          <ArrowLeft className="h-4 w-4" /> Back to Templates
        </button>
        <h1 className="mb-1 text-xl font-bold text-secondary-900">{selectedTemplate.name}</h1>
        <p className="mb-4 text-sm text-secondary-500">{selectedTemplate.description}</p>

        <div className="mb-4 rounded-lg border border-secondary-200 bg-secondary-50 p-3">
          <h3 className="mb-2 text-xs font-semibold uppercase text-secondary-500">Columns</h3>
          <div className="flex flex-wrap gap-2">
            {selectedTemplate.column_definitions.map((col) => (
              <span
                key={col.name}
                className="rounded bg-white px-2 py-1 text-xs text-secondary-700"
              >
                {col.label}
              </span>
            ))}
          </div>
        </div>

        <div className="mb-4">
          <label className="mb-1 block text-sm font-medium text-secondary-700">CSV File</label>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={handleFileChange}
            className="w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm"
          />
        </div>

        <button
          onClick={handleUpload}
          disabled={!selectedFile}
          className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
        >
          <Upload className="h-4 w-4" />
          Upload & Validate
        </button>
      </div>
    );
  }

  if (step === "validate" && currentJob) {
    return (
      <div className="p-4 md:p-6 max-w-3xl">
        <button
          onClick={reset}
          className="mb-4 inline-flex items-center gap-1 text-sm text-secondary-600 hover:text-secondary-900"
        >
          <ArrowLeft className="h-4 w-4" /> Start New Import
        </button>

        <div className="mb-6 rounded-lg border border-secondary-200 bg-white p-4">
          <h2 className="mb-3 text-lg font-semibold text-secondary-900">
            {currentJob.template_name}
          </h2>
          <div className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
            <div>
              <div className="text-secondary-500">Status</div>
              <div className="font-medium text-secondary-900">{statusLabel(currentJob.status)}</div>
            </div>
            <div>
              <div className="text-secondary-500">File</div>
              <div className="truncate font-medium text-secondary-900">{currentJob.file_name}</div>
            </div>
            <div>
              <div className="text-secondary-500">Total Rows</div>
              <div className="font-medium text-secondary-900">{currentJob.total_rows}</div>
            </div>
            <div>
              <div className="text-secondary-500">Errors</div>
              <div className={`font-medium ${currentJob.error_count > 0 ? "text-danger-600" : "text-success-600"}`}>
                {currentJob.error_count}
              </div>
            </div>
          </div>
        </div>

        {currentJob.status === "uploaded" && (
          <button
            onClick={handleValidate}
            className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
          >
            <CheckCircle className="h-4 w-4" />
            Validate Rows
          </button>
        )}

        {(currentJob.status === "validating" || currentJob.status === "importing") && (
          <div className="flex items-center gap-2 text-sm text-secondary-600">
            <Loader2 className="h-4 w-4 animate-spin" />
            Processing...
          </div>
        )}

        {currentJob.status === "uploaded" && currentJob.error_count > 0 && (
          <div className="mt-4 rounded-lg border border-danger-200 bg-danger-50 p-3">
            <h3 className="mb-2 flex items-center gap-1 text-sm font-semibold text-danger-700">
              <AlertCircle className="h-4 w-4" /> Validation Errors
            </h3>
            <div className="max-h-48 overflow-y-auto space-y-1">
              {currentJob.rows
                ?.filter((r) => r.status === "error")
                .slice(0, 20)
                .map((r) => (
                  <div key={r.id} className="text-xs text-danger-600">
                    Row {r.row_number}: {r.errors?.map((e) => e.message).join("; ")}
                  </div>
                ))}
            </div>
          </div>
        )}

        {currentJob.status === "uploaded" && currentJob.error_count === 0 && currentJob.total_rows > 0 && (
          <div className="mt-4">
            <button
              onClick={handleImport}
              className="inline-flex items-center gap-2 rounded-lg bg-success-600 px-4 py-2 text-sm font-medium text-white hover:bg-success-700"
            >
              <Upload className="h-4 w-4" />
              Import {currentJob.total_rows} Rows
            </button>
          </div>
        )}

        {currentJob.status === "completed" && (
          <div className="mt-4 space-y-3">
            <div className="rounded-lg border border-success-200 bg-success-50 p-3">
              <p className="text-sm font-medium text-success-700">
                {currentJob.success_count} rows imported successfully.
              </p>
            </div>
            <button
              onClick={handleRollback}
              className="inline-flex items-center gap-2 rounded-lg border border-danger-300 px-4 py-2 text-sm font-medium text-danger-700 hover:bg-danger-50"
            >
              <RotateCcw className="h-4 w-4" />
              Rollback Import
            </button>
          </div>
        )}

        {currentJob.status === "rolled_back" && (
          <div className="mt-4 rounded-lg border border-secondary-200 bg-secondary-50 p-3">
            <p className="text-sm text-secondary-700">Import has been rolled back.</p>
          </div>
        )}
      </div>
    );
  }

  if (step === "result" && importResult) {
    return (
      <div className="p-4 md:p-6 max-w-2xl">
        <button
          onClick={reset}
          className="mb-4 inline-flex items-center gap-1 text-sm text-secondary-600 hover:text-secondary-900"
        >
          <ArrowLeft className="h-4 w-4" /> New Import
        </button>
        <h1 className="mb-4 text-xl font-bold text-secondary-900">Import Result</h1>
        <div className="rounded-lg border border-secondary-200 bg-white p-4">
          <div className="space-y-2 text-sm">
            {Object.entries(importResult).map(([key, val]) => (
              <div key={key} className="flex justify-between">
                <span className="text-secondary-500">{key}</span>
                <span className="font-medium text-secondary-900">{String(val)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6">
      <h1 className="mb-1 text-xl font-bold text-secondary-900">Data Import</h1>
      <p className="mb-6 text-sm text-secondary-500">
        Import master data from CSV files. Select a template to begin.
      </p>

      <div className="relative mb-6 max-w-md">
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-secondary-400" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search templates..."
              className="w-full rounded-lg border border-secondary-300 py-2 pl-9 pr-3 text-sm focus:border-primary-500 focus:outline-none"
            />
          </div>
          <button
            onClick={async () => {
              setReloadStatus("reloading");
              try {
                const before = templates.length;
                await api.post("/core/import/seed-templates/");
                await queryClient.invalidateQueries({ queryKey: ["import-templates"] });
                await new Promise((r) => setTimeout(r, 200));
                const after = (queryClient.getQueryData(["import-templates"]) as unknown[])?.length ?? 0;
                if (after > before) {
                  setReloadStatus("done");
                } else {
                  setReloadStatus("uptodate");
                }
              } catch {
                setReloadStatus("failed");
              }
              setTimeout(() => setReloadStatus("idle"), 2000);
            }}
            className={`shrink-0 rounded-lg border px-3 py-2 text-xs font-medium transition-colors ${
              reloadStatus === "reloading"
                ? "border-primary-300 bg-primary-50 text-primary-600"
                : reloadStatus === "done"
                  ? "border-success-300 bg-success-50 text-success-700"
                  : reloadStatus === "uptodate"
                    ? "border-secondary-300 bg-secondary-50 text-secondary-600"
                    : reloadStatus === "failed"
                      ? "border-danger-300 bg-danger-50 text-danger-700"
                      : "border-secondary-300 text-secondary-600 hover:bg-secondary-50"
            }`}
            title="Reload default import templates"
            disabled={reloadStatus === "reloading"}
          >
            {reloadStatus === "idle" && "Reload Templates"}
            {reloadStatus === "reloading" && "Reloading..."}
            {reloadStatus === "done" && "New templates loaded!"}
            {reloadStatus === "uptodate" && "Templates up to date"}
            {reloadStatus === "failed" && "Failed — page will reload"}
          </button>
        </div>
      </div>

      {templatesLoading ? (
        <div className="flex h-32 items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-primary-500" />
        </div>
      ) : (
        <div className="mb-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filteredTemplates.map((t) => (
            <button
              key={t.id}
              onClick={() => selectTemplate(t)}
              className="rounded-lg border border-secondary-200 bg-white p-4 text-left hover:border-primary-400 hover:shadow-sm transition-all"
            >
              <div className="mb-2 flex items-center gap-2">
                <FileText className="h-5 w-5 text-primary-500" />
                <span className="text-sm font-semibold text-secondary-900">{t.name}</span>
              </div>
              <p className="mb-2 text-xs text-secondary-500">{t.description}</p>
              <div className="flex flex-wrap gap-1">
                {t.column_definitions.slice(0, 4).map((col) => (
                  <span
                    key={col.name}
                    className="rounded bg-secondary-100 px-1.5 py-0.5 text-xs text-secondary-600"
                  >
                    {col.label}
                  </span>
                ))}
                {t.column_definitions.length > 4 && (
                  <span className="rounded bg-secondary-100 px-1.5 py-0.5 text-xs text-secondary-400">
                    +{t.column_definitions.length - 4}
                  </span>
                )}
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  window.open(
                    `/api/v1/core/import/templates/${t.entity_type}/csv/`,
                    "_blank"
                  );
                }}
                className="mt-3 inline-flex items-center gap-1 text-xs text-primary-600 hover:text-primary-700"
              >
                <Download className="h-3 w-3" /> Download CSV Template
              </button>
            </button>
          ))}
          {filteredTemplates.length === 0 && (
            <div className="col-span-full py-8 text-center text-sm text-secondary-400">
              No templates found.{' '}
              <button
                onClick={async () => {
                  try {
                    await api.post("/core/import/seed-templates/");
                    queryClient.invalidateQueries({ queryKey: ["import-templates"] });
                  } catch {
                    // silently fail
                  }
                }}
                className="text-primary-600 hover:text-primary-700 underline"
              >
                Click here
              </button>{' '}
              to load default templates.
            </div>
          )}
        </div>
      )}

      {/* Import History */}
      {recentHistory.length > 0 && (
        <div>
          <h2 className="mb-3 text-base font-semibold text-secondary-900">
            Recent Imports ({totalHistory})
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-secondary-200 text-left text-xs uppercase text-secondary-500">
                  <th className="pb-2 pr-4 font-medium">Type</th>
                  <th className="pb-2 pr-4 font-medium">Action</th>
                  <th className="pb-2 pr-4 font-medium">Records</th>
                  <th className="pb-2 pr-4 font-medium">By</th>
                  <th className="pb-2 font-medium">Date</th>
                </tr>
              </thead>
              <tbody>
                {recentHistory.map((h) => (
                  <tr key={h.id} className="border-b border-secondary-100">
                    <td className="py-2 pr-4 text-secondary-900">{h.entity_type}</td>
                    <td className="py-2 pr-4">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          h.action === "import"
                            ? "bg-success-100 text-success-700"
                            : "bg-danger-100 text-danger-700"
                        }`}
                      >
                        {h.action}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-secondary-900">{h.record_count}</td>
                    <td className="py-2 pr-4 text-secondary-600">{h.performed_by_name}</td>
                    <td className="py-2 text-secondary-500">{h.created_at?.slice(0, 10)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
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
