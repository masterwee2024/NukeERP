import { useState } from "react";
import { useAuditLogs, type AuditLog } from "@/hooks/useAuditLogs";
import AccordionSection from "@/components/shared/AccordionSection";
import DynamicListDetailPage from "@/components/shared/DynamicListDetailPage";

const ACTION_BADGES: Record<string, string> = {
  create: "bg-success-100 text-success-700",
  update: "bg-primary-100 text-primary-700",
  delete: "bg-danger-100 text-danger-700",
};

export default function AuditLogPage() {
  const { logs, isLoading } = useAuditLogs({ pageSize: 100 });
  const [selectedRecord, setSelectedRecord] = useState<AuditLog | null>(null);
  const [activeSection, setActiveSection] = useState("summary");

  const toggleSection = (section: string) => {
    setActiveSection((prev) => (prev === section ? "" : section));
  };

  return (
    <DynamicListDetailPage<AuditLog>
      title="Audit Log"
      records={logs}
      isLoading={isLoading}
      toCard={(log) => ({
        id: log.id,
        label: log.model_name,
        badge: {
          label: log.action,
          color:
            ACTION_BADGES[log.action] || "bg-secondary-100 text-secondary-600",
        },
        meta: [
          { label: "User", value: log.user_name },
          { label: "Record", value: `#${log.record_id.slice(0, 8)}` },
          { label: "Time", value: new Date(log.timestamp).toLocaleString() },
        ],
      })}
      selectedRecord={selectedRecord}
      onSelect={(r) => setSelectedRecord(r)}
      renderDetail={(log) => {
        const changes = log.changes || {};
        const changeKeys = Object.keys(changes);
        return (
          <div className="space-y-4">
            <AccordionSection
              title="Summary"
              isOpen={activeSection === "summary"}
              onToggle={() => toggleSection("summary")}
            >
              <div className="space-y-3">
                {[
                  { label: "Model", value: log.model_name },
                  {
                    label: "Record ID",
                    value: log.record_id || "—",
                    mono: true,
                  },
                  { label: "Action", value: log.action, capitalize: true },
                  { label: "User", value: log.user_name },
                  { label: "IP Address", value: log.ip_address || "—", mono: true },
                  { label: "Company", value: log.company_name || "—" },
                  {
                    label: "Timestamp",
                    value: new Date(log.timestamp).toLocaleString(),
                  },
                ].map((f) => (
                  <div key={f.label}>
                    <label className="block text-xs font-medium uppercase text-secondary-400">
                      {f.label}
                    </label>
                    <p
                      className={`mt-1 text-sm ${
                        f.mono ? "font-mono" : ""
                      } ${f.capitalize ? "capitalize" : ""} text-secondary-900`}
                    >
                      {f.value}
                    </p>
                  </div>
                ))}
              </div>
            </AccordionSection>

            <AccordionSection
              title={`Changes (${changeKeys.length})`}
              isOpen={activeSection === "changes"}
              onToggle={() => toggleSection("changes")}
            >
              <div className="space-y-3">
                {changeKeys.length === 0 && (
                  <p className="text-sm text-secondary-500">
                    No changes recorded.
                  </p>
                )}
                {changeKeys.map((field) => {
                  const change = changes[field];
                  return (
                    <div
                      key={field}
                      className="rounded-lg border border-secondary-200 bg-secondary-50 p-3"
                    >
                      <label className="block text-xs font-medium uppercase text-secondary-500">
                        {field}
                      </label>
                      <div className="mt-1 grid grid-cols-2 gap-3">
                        <div>
                          <span className="text-xs text-danger-500">Old:</span>
                          <p className="mt-0.5 truncate font-mono text-sm text-secondary-700">
                            {formatChangeValue(change.old)}
                          </p>
                        </div>
                        <div>
                          <span className="text-xs text-success-600">New:</span>
                          <p className="mt-0.5 truncate font-mono text-sm text-secondary-900">
                            {formatChangeValue(change.new)}
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </AccordionSection>
          </div>
        );
      }}
    />
  );
}

function formatChangeValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return String(value);
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
