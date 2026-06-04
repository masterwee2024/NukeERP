import { useState, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { useAction } from "@/components/ui/ConfirmDialog";

interface RetentionPolicy {
  retention_years: number;
  auto_archive: boolean;
}

export default function AuditRetentionSettingsPage() {
  const queryClient = useQueryClient();
  const { execute } = useAction();

  const [retentionYears, setRetentionYears] = useState<number>(7);
  const [autoArchive, setAutoArchive] = useState<boolean>(true);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState("");

  const {
    data: policy,
    isLoading,
    error,
  } = useQuery<RetentionPolicy>({
    queryKey: ["audit-retention"],
    queryFn: async () => {
      const { data } = await api.get("/core/admin/audit-retention/");
      return data;
    },
    retry: 2,
  });

  useEffect(() => {
    if (policy) {
      setRetentionYears(policy.retention_years);
      setAutoArchive(policy.auto_archive);
    }
  }, [policy]);

  const handleSave = async () => {
    await execute({
      confirm: {
        title: "Save Retention Policy",
        message: `Set retention to ${retentionYears} year(s) with ${autoArchive ? "auto-archive" : "no auto-archive"}?`,
        variant: "info",
        confirmText: "Save",
      },
      action: async () => {
        const res = await api.put("/core/admin/audit-retention/", {
          retention_years: retentionYears,
          auto_archive: autoArchive,
        });
        return res.data;
      },
      success: {
        title: "Settings Saved",
        message: "Audit log retention policy has been updated.",
        variant: "info",
      },
      errorTitle: "Save Failed",
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["audit-retention"] });
        setSaved(true);
        setSaveError("");
        setTimeout(() => setSaved(false), 3000);
      },
    });
  };

  return (
    <div className="mx-auto max-w-2xl p-4 md:p-6">
      <h1 className="mb-6 text-xl font-bold text-secondary-900 md:text-2xl">
        Audit Retention Settings
      </h1>

      {isLoading && (
        <div className="mb-4 rounded-lg bg-secondary-50 p-3 text-sm text-secondary-600">
          Loading settings...
        </div>
      )}

      {error && !isLoading && (
        <div className="mb-4 rounded-lg bg-danger-50 p-3 text-sm text-danger-700">
          Failed to load settings:{" "}
          {(error as { response?: { data?: { detail?: string } } })?.response?.data
            ?.detail || "Check server logs"}
        </div>
      )}

      {saved && (
        <div className="mb-4 rounded-lg bg-success-50 p-3 text-sm text-success-700">
          Settings saved
        </div>
      )}
      {saveError && (
        <div className="mb-4 rounded-lg bg-danger-50 p-3 text-sm text-danger-700">
          {saveError}
        </div>
      )}

      <div className="space-y-6 rounded-lg border border-secondary-200 bg-white p-6">
        <h2 className="text-lg font-semibold text-secondary-900">
          Retention Policy
        </h2>

        {/* Retention Years */}
        <div>
          <label
            htmlFor="retention_years"
            className="block text-sm font-medium text-secondary-700"
          >
            Retention Period (years)
          </label>
          <p className="mb-2 text-xs text-secondary-400">
            Audit logs older than this will be archived or deleted.
          </p>
          <input
            id="retention_years"
            type="number"
            min={1}
            max={20}
            value={retentionYears}
            onChange={(e) => {
              const val = parseInt(e.target.value, 10);
              if (!isNaN(val)) {
                setRetentionYears(Math.max(1, Math.min(20, val)));
              }
            }}
            className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
          />
          <p className="mt-1 text-xs text-secondary-400">Between 1 and 20 years.</p>
        </div>

        {/* Auto Archive */}
        <div>
          <label className="flex items-start gap-3">
            <input
              type="checkbox"
              checked={autoArchive}
              onChange={(e) => setAutoArchive(e.target.checked)}
              className="mt-0.5 rounded border-secondary-300 text-primary-600"
            />
            <div>
              <span className="text-sm font-medium text-secondary-700">
                Auto-archive old logs
              </span>
              <p className="text-xs text-secondary-400">
                When enabled, logs exceeding the retention period are automatically
                archived to a separate storage. When disabled, old logs are deleted
                permanently.
              </p>
            </div>
          </label>
        </div>

        {/* Save Button */}
        <div className="flex justify-end border-t border-secondary-200 pt-4">
          <button
            onClick={handleSave}
            className="rounded-lg bg-primary-600 px-6 py-2 text-sm font-medium text-white hover:bg-primary-700"
          >
            Save Settings
          </button>
        </div>
      </div>
    </div>
  );
}
