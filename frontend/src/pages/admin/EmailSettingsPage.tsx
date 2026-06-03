import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { useConfirm } from "@/components/ui/ConfirmDialog";

interface EmailConfig {
  smtp_host: string;
  smtp_port: number;
  smtp_username: string;
  smtp_password: string;
  smtp_use_tls: boolean;
  smtp_use_ssl: boolean;
  from_email: string;
  from_name: string;
}

export default function EmailSettingsPage() {
  const queryClient = useQueryClient();
  const { confirm } = useConfirm();
  const [form, setForm] = useState<EmailConfig>({
    smtp_host: "",
    smtp_port: 587,
    smtp_username: "",
    smtp_password: "",
    smtp_use_tls: true,
    smtp_use_ssl: false,
    from_email: "",
    from_name: "",
  });
  const [testEmail, setTestEmail] = useState("");
  const [testResult, setTestResult] = useState<{ ok: boolean; msg: string } | null>(null);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState("");

  const { data: config, error: configError, isLoading: configLoading } = useQuery({
    queryKey: ["email-settings"],
    queryFn: async (): Promise<EmailConfig> => {
      const { data } = await api.get("/core/admin/settings/email/");
      return data;
    },
    retry: 2,
  });

  useEffect(() => {
    if (config) setForm(config);
  }, [config]);

  const saveMutation = useMutation({
    mutationFn: async (data: Partial<EmailConfig>) => {
      const res = await api.put("/core/admin/settings/email/", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["email-settings"] });
      setSaved(true);
      setSaveError("");
      setTimeout(() => setSaved(false), 3000);
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      setSaveError(err.response?.data?.detail || "Failed to save settings");
    },
  });

  const testMutation = useMutation({
    mutationFn: async (recipient: string) => {
      const res = await api.post("/core/admin/settings/email/test/", { recipient });
      return res.data;
    },
    onSuccess: (data) => setTestResult({ ok: true, msg: data.detail }),
    onError: (err: { response?: { data?: { detail?: string } } }) =>
      setTestResult({ ok: false, msg: err.response?.data?.detail || "Test failed" }),
  });

  const handleSave = async () => {
    const confirmed = await confirm({
      title: "Save SMTP Settings",
      message: "Update email configuration?",
      variant: "info",
      confirmText: "Save",
    });
    if (confirmed) saveMutation.mutate(form);
  };

  const handleTest = () => {
    setTestResult(null);
    testMutation.mutate(testEmail || form.from_email);
  };

  const handleChange = (field: keyof EmailConfig, value: string | number | boolean) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <div className="mx-auto max-w-2xl p-4 md:p-6">
      <h1 className="mb-6 text-xl font-bold text-secondary-900 md:text-2xl">Email Settings</h1>

      {configLoading && (
        <div className="mb-4 rounded-lg bg-secondary-50 p-3 text-sm text-secondary-600">Loading settings...</div>
      )}
      {configError && (
        <div className="mb-4 rounded-lg bg-danger-50 p-3 text-sm text-danger-700">
          Failed to load settings: {(configError as any)?.response?.data?.detail || "Check server logs"}
        </div>
      )}
      {saved && (
        <div className="mb-4 rounded-lg bg-success-50 p-3 text-sm text-success-700">Settings saved</div>
      )}
      {saveError && (
        <div className="mb-4 rounded-lg bg-danger-50 p-3 text-sm text-danger-700">{saveError}</div>
      )}

      <div className="space-y-4 rounded-lg border border-secondary-200 bg-white p-6">
        <h2 className="text-lg font-semibold text-secondary-900">SMTP Configuration</h2>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-secondary-700">SMTP Host</label>
            <input
              type="text"
              value={form.smtp_host}
              onChange={(e) => handleChange("smtp_host", e.target.value)}
              placeholder="smtp.gmail.com"
              className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-secondary-700">SMTP Port</label>
            <input
              type="number"
              value={form.smtp_port}
              onChange={(e) => handleChange("smtp_port", parseInt(e.target.value) || 587)}
              className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-secondary-700">Username</label>
            <input
              type="text"
              value={form.smtp_username}
              onChange={(e) => handleChange("smtp_username", e.target.value)}
              className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-secondary-700">Password</label>
            <input
              type="password"
              value={form.smtp_password}
              onChange={(e) => handleChange("smtp_password", e.target.value)}
              placeholder="Leave blank to keep current"
              className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
            />
          </div>
        </div>

        <div className="flex flex-wrap gap-4">
          <label className="flex items-center gap-2 text-sm text-secondary-700">
            <input
              type="checkbox"
              checked={form.smtp_use_tls}
              onChange={(e) => handleChange("smtp_use_tls", e.target.checked)}
              className="rounded border-secondary-300 text-primary-600"
            />
            Use TLS
          </label>
          <label className="flex items-center gap-2 text-sm text-secondary-700">
            <input
              type="checkbox"
              checked={form.smtp_use_ssl}
              onChange={(e) => handleChange("smtp_use_ssl", e.target.checked)}
              className="rounded border-secondary-300 text-primary-600"
            />
            Use SSL
          </label>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-secondary-700">From Email</label>
            <input
              type="email"
              value={form.from_email}
              onChange={(e) => handleChange("from_email", e.target.value)}
              placeholder="noreply@example.com"
              className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-secondary-700">From Name</label>
            <input
              type="text"
              value={form.from_name}
              onChange={(e) => handleChange("from_name", e.target.value)}
              placeholder="pyERP"
              className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
            />
          </div>
        </div>

        <div className="flex justify-end">
          <button
            onClick={handleSave}
            className="rounded-lg bg-primary-600 px-6 py-2 text-sm font-medium text-white hover:bg-primary-700"
          >
            Save Settings
          </button>
        </div>
      </div>

      <div className="mt-6 rounded-lg border border-secondary-200 bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold text-secondary-900">Test Email</h2>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1">
            <label className="block text-sm font-medium text-secondary-700">Recipient</label>
            <input
              type="email"
              value={testEmail}
              onChange={(e) => setTestEmail(e.target.value)}
              placeholder={form.from_email || "recipient@example.com"}
              className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
            />
          </div>
          <button
            onClick={handleTest}
            disabled={testMutation.isPending}
            className="rounded-lg bg-secondary-600 px-4 py-2 text-sm font-medium text-white hover:bg-secondary-700 disabled:opacity-50"
          >
            {testMutation.isPending ? "Sending..." : "Send Test"}
          </button>
        </div>
        {testResult && (
          <div className={`mt-3 rounded-lg p-3 text-sm ${
            testResult.ok ? "bg-success-50 text-success-700" : "bg-danger-50 text-danger-700"
          }`}>
            {testResult.msg}
          </div>
        )}
      </div>
    </div>
  );
}
