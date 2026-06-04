import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useConfirm } from "@/components/ui/ConfirmDialog";
import api from "@/lib/api";
import {
  ArrowLeft, ArrowRight, Check, CheckCircle, Download, Upload, RotateCcw,
} from "lucide-react";

const STEPS = [
  { key: "gl", label: "GL Balance", icon: "💰" },
  { key: "ap", label: "AP Invoices", icon: "📄" },
  { key: "ar", label: "AR Invoices", icon: "📄" },
  { key: "inventory", label: "Inventory", icon: "📦" },
  { key: "asset", label: "Fixed Assets", icon: "🏗️" },
];

const STEP_LABELS: Record<string, string> = {
  gl: "Chart of Accounts",
  ap: "Accounts Payable",
  ar: "Accounts Receivable",
  inventory: "Inventory",
  asset: "Fixed Assets",
};

export default function MigrationWizardPage() {
  const { confirm } = useConfirm();
  const queryClient = useQueryClient();
  const [step, setStep] = useState(0);
  const [migrationId, setMigrationId] = useState<string | null>(null);
  const [goLiveDate, setGoLiveDate] = useState("");
  const [stepFiles, setStepFiles] = useState<Record<string, File | null>>({});
  const [stepResults, setStepResults] = useState<Record<string, Record<string, unknown>>>({});

  const { data: migrations = [] } = useQuery({
    queryKey: ["opening-migrations"],
    queryFn: async () => {
      const { data } = await api.get("/core/opening-balance/migrations/");
      return (data?.results ?? data ?? []) as Record<string, unknown>[];
    },
  });

  const { data: summary, refetch: refetchSummary } = useQuery({
    queryKey: ["opening-summary", migrationId],
    queryFn: async (): Promise<Record<string, unknown>> => {
      const { data } = await api.get(`/core/opening-balance/migrations/${migrationId}/summary/`);
      return data;
    },
    enabled: !!migrationId,
  });

  async function handleCreateMigration() {
    if (!goLiveDate) return;
    const ok = await confirm({
      title: "Start Migration",
      message: `Create opening balance migration as of ${goLiveDate}?`,
      variant: "info",
      confirmText: "Start",
    });
    if (!ok) return;
    try {
      const { data } = await api.post("/core/opening-balance/migrations/", {
        go_live_date: goLiveDate,
      });
      setMigrationId((data as Record<string, unknown>).id as string);
      queryClient.invalidateQueries({ queryKey: ["opening-migrations"] });
    } catch (err) {
      console.warn("Failed to create migration, falling back to existing:", err);
    }
  }

  const currentStep = STEPS[step];
  const isLastStep = step === STEPS.length - 1;

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>, stepKey: string) {
    if (e.target.files && e.target.files[0]) {
      setStepFiles((prev) => ({ ...prev, [stepKey]: e.target.files![0] }));
    }
  }

  async function handleUploadAndImport(stepKey: string) {
    const file = stepFiles[stepKey];
    if (!migrationId || !file) return;
    const ok = await confirm({
      title: `Import ${STEP_LABELS[stepKey]}`,
      message: `Upload and import ${file.name}?`,
      variant: "info",
      confirmText: "Import",
    });
    if (!ok) return;

    const formData = new FormData();
    formData.append("file", file);
    try {
      const { data } = await api.post(
        `/core/opening-balance/migrations/${migrationId}/import/${stepKey}/`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } },
      );
      setStepResults((prev) => ({ ...prev, [stepKey]: data as Record<string, unknown> }));
      refetchSummary();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Import failed";
      await confirm({ title: "Error", message: msg, variant: "danger", confirmText: "OK" });
    }
  }

  async function handleComplete() {
    if (!migrationId) return;
    const ok = await confirm({
      title: "Complete Migration",
      message: "Finalize opening balance migration? This cannot be undone.",
      variant: "warning",
      confirmText: "Complete",
    });
    if (!ok) return;
    await api.post(`/core/opening-balance/migrations/${migrationId}/complete/`);
    refetchSummary();
  }

  async function handleRollback() {
    if (!migrationId) return;
    const ok = await confirm({
      title: "Rollback Migration",
      message: "Delete all opening balance data?",
      variant: "danger",
      confirmText: "Rollback",
    });
    if (!ok) return;
    await api.post(`/core/opening-balance/migrations/${migrationId}/rollback/`);
    setMigrationId(null);
    setStepResults({});
    setStepFiles({});
    setStep(0);
    queryClient.invalidateQueries({ queryKey: ["opening-migrations"] });
  }

  if (!migrationId && migrations.length === 0) {
    return (
      <div className="p-4 md:p-6 max-w-lg">
        <h1 className="mb-4 text-xl font-bold text-secondary-900">Opening Balance Migration</h1>
        <p className="mb-4 text-sm text-secondary-500">
          Import opening balances from your old system.
        </p>
        <div className="mb-4">
          <label className="mb-1 block text-sm font-medium text-secondary-700">Go-Live Date</label>
          <input
            type="date"
            value={goLiveDate}
            onChange={(e) => setGoLiveDate(e.target.value)}
            className="w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm"
          />
        </div>
        <button
          onClick={handleCreateMigration}
          disabled={!goLiveDate}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
        >
          Start Migration
        </button>
      </div>
    );
  }

  if (!migrationId && migrations.length > 0) {
    const latest = migrations[0] as Record<string, unknown>;
    return (
      <div className="p-4 md:p-6 max-w-lg">
        <h1 className="mb-4 text-xl font-bold text-secondary-900">Opening Balance Migration</h1>
        <p className="mb-4 text-sm text-secondary-500">
          Continue existing migration from {latest.go_live_date as string} (Status: {latest.status as string})
        </p>
        <button
          onClick={() => setMigrationId(latest.id as string)}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white"
        >
          Continue
        </button>
        <button
          onClick={() => {
            setMigrationId(latest.id as string);
            setStepResults({});
          }}
          className="ml-2 rounded-lg border border-secondary-300 px-4 py-2 text-sm text-secondary-700"
        >
          Start Fresh
        </button>
      </div>
    );
  }

  const isCompleted = summary?.status === "completed";
  const isRolledBack = summary?.status === "rolled_back";

  if (isCompleted || isRolledBack) {
    return (
      <div className="p-4 md:p-6 max-w-2xl">
        <h1 className="mb-4 text-xl font-bold text-secondary-900">
          Migration {isCompleted ? "Completed" : "Rolled Back"}
        </h1>
        {summary && (
          <div className="space-y-2 text-sm">
            {Object.entries(summary).map(([key, val]) => {
              if (typeof val === "object") {
                return (
                  <div key={key} className="rounded-lg border border-secondary-200 bg-white p-3">
                    <span className="font-medium text-secondary-900">{key}: </span>
                    <span className="text-secondary-600">{JSON.stringify(val)}</span>
                  </div>
                );
              }
              return (
                <div key={key} className="flex justify-between rounded-lg border border-secondary-200 bg-white p-3">
                  <span className="text-secondary-500">{key}</span>
                  <span className="font-medium text-secondary-900">{String(val)}</span>
                </div>
              );
            })}
          </div>
        )}
        <button onClick={handleRollback} className="mt-4 rounded-lg bg-primary-600 px-4 py-2 text-sm text-white">
          Start New Migration
        </button>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6">
      <h1 className="mb-4 text-xl font-bold text-secondary-900">Opening Balance Migration</h1>

      {/* Step Progress */}
      <div className="mb-6 flex flex-wrap gap-2">
        {STEPS.map((s, i) => (
          <button
            key={s.key}
            onClick={() => setStep(i)}
            className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              stepResults[s.key]
                ? "bg-success-100 text-success-700"
                : i === step
                  ? "bg-primary-100 text-primary-700"
                  : "bg-secondary-100 text-secondary-500"
            }`}
          >
            {stepResults[s.key] ? <Check className="h-3 w-3" /> : null}
            {s.label}
          </button>
        ))}
      </div>

      {/* Current Step Content */}
      <div className="mb-6 rounded-lg border border-secondary-200 bg-white p-4">
        <h2 className="mb-3 text-lg font-semibold text-secondary-900">
          {currentStep.label}
        </h2>

        {stepResults[currentStep.key] ? (
          <div>
            <div className="mb-3 rounded-lg border border-success-200 bg-success-50 p-3">
              <p className="text-sm text-success-700">
                Imported {stepResults[currentStep.key].success as number} records (
                {stepResults[currentStep.key].errors as number} errors)
              </p>
            </div>
            {!isLastStep && (
              <button
                onClick={() => setStep(step + 1)}
                className="inline-flex items-center gap-1 rounded-lg bg-primary-600 px-4 py-2 text-sm text-white"
              >
                Next: {STEPS[step + 1].label} <ArrowRight className="h-4 w-4" />
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-secondary-500">
              Download the CSV template, fill in your data, then upload.
            </p>
            <a
              href={`/api/v1/core/opening-balance/templates/${currentStep.key}/csv/`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-sm text-primary-600 hover:text-primary-700"
            >
              <Download className="h-3 w-3" /> Download {currentStep.label} Template
            </a>
            <div>
              <input
                type="file"
                accept=".csv"
                onChange={(e) => handleFileSelect(e, currentStep.key)}
                className="w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm"
              />
            </div>
            <button
              onClick={() => handleUploadAndImport(currentStep.key)}
              disabled={!stepFiles[currentStep.key]}
              className="inline-flex items-center gap-1 rounded-lg bg-primary-600 px-4 py-2 text-sm text-white hover:bg-primary-700 disabled:opacity-50"
            >
              <Upload className="h-4 w-4" /> Upload & Import
            </button>
          </div>
        )}
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          {step > 0 && (
            <button
              onClick={() => setStep(step - 1)}
              className="inline-flex items-center gap-1 rounded-lg border border-secondary-300 px-4 py-2 text-sm text-secondary-700"
            >
              <ArrowLeft className="h-4 w-4" /> Previous
            </button>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleRollback}
            className="inline-flex items-center gap-1 rounded-lg border border-danger-300 px-4 py-2 text-sm text-danger-700 hover:bg-danger-50"
          >
            <RotateCcw className="h-4 w-4" /> Rollback All
          </button>
          <button
            onClick={handleComplete}
            className="inline-flex items-center gap-1 rounded-lg bg-success-600 px-4 py-2 text-sm text-white hover:bg-success-700"
          >
            <CheckCircle className="h-4 w-4" /> Complete Migration
          </button>
        </div>
      </div>

      {/* Summary */}
      {summary && (
        <div className="mt-6 rounded-lg border border-secondary-200 bg-secondary-50 p-4">
          <h3 className="mb-2 text-sm font-semibold text-secondary-700">Summary</h3>
          <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-5">
            {(["gl", "ap", "ar", "inventory", "assets"] as const).map((k) => {
              const s = summary[k] as Record<string, unknown> | undefined;
              if (!s) return null;
              return (
                <div key={k} className="rounded bg-white p-2">
                  <div className="font-medium text-secondary-700">{STEP_LABELS[k] || k}</div>
                  <div className="text-success-600">{s.success as number} imported</div>
                  {(s.errors as number) > 0 && (
                    <div className="text-danger-600">{s.errors as number} errors</div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
