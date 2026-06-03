import { useState } from "react";
import { useIsMobile } from "@/hooks/useIsMobile";
import { useAuditLogs, type AuditLog } from "@/hooks/useAuditLogs";
import AccordionSection from "@/components/shared/AccordionSection";
import FormPageLayout from "@/components/shared/FormPageLayout";
import { ArrowLeft, Loader2, Activity, PlusCircle, Trash2, Pencil } from "lucide-react";

const ACTION_ICONS: Record<string, React.ReactNode> = {
  create: <PlusCircle className="h-4 w-4 text-success-500" />,
  update: <Pencil className="h-4 w-4 text-primary-500" />,
  delete: <Trash2 className="h-4 w-4 text-danger-500" />,
};

const ACTION_BADGES: Record<string, string> = {
  create: "bg-success-100 text-success-700",
  update: "bg-primary-100 text-primary-700",
  delete: "bg-danger-100 text-danger-700",
};

export default function AuditLogPage() {
  const isMobile = useIsMobile();
  const { logs, totalCount, isLoading } = useAuditLogs({ pageSize: 100 });

  const [selectedRecord, setSelectedRecord] = useState<AuditLog | null>(null);
  const [activeView, setActiveView] = useState<"list" | "detail">("list");
  const [activeSection, setActiveSection] = useState("summary");

  const toggleSection = (section: string) => {
    setActiveSection((prev) => (prev === section ? "" : section));
  };

  const handleRowClick = (log: AuditLog) => {
    setSelectedRecord(log);
    setActiveView("detail");
  };

  function renderList() {
    return (
      <div className="space-y-2">
        {logs.length === 0 ? (
          <div className="py-8 text-center text-sm text-secondary-500">
            No audit log entries.
          </div>
        ) : (
          logs.map((log) => (
            <div
              key={log.id}
              className="cursor-pointer rounded-lg border border-secondary-200 bg-white p-3"
              onClick={() => handleRowClick(log)}
            >
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5 text-sm font-medium text-secondary-900">
                  {ACTION_ICONS[log.action] || <Activity className="h-4 w-4" />}
                  {log.model_name}
                </span>
                <span
                  className={`rounded-full px-1.5 py-0.5 text-xs capitalize ${ACTION_BADGES[log.action] || "bg-secondary-100 text-secondary-600"}`}
                >
                  {log.action}
                </span>
              </div>
              <div className="mt-1 flex items-center gap-2 text-xs text-secondary-500">
                <span>{log.user_name}</span>
                <span className="text-secondary-300">|</span>
                <span>#{log.record_id.slice(0, 8)}</span>
                <span className="text-secondary-300">|</span>
                <span>{new Date(log.timestamp).toLocaleString()}</span>
              </div>
            </div>
          ))
        )}
      </div>
    );
  }

  function renderDetail() {
    if (!selectedRecord) return null;
    const changes = selectedRecord.changes || {};
    const changeKeys = Object.keys(changes);

    return (
      <div className="space-y-4">
        <AccordionSection
          title="Summary"
          isOpen={activeSection === "summary"}
          onToggle={() => toggleSection("summary")}
        >
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium uppercase text-secondary-400">Model</label>
              <p className="mt-1 text-sm text-secondary-900">{selectedRecord.model_name}</p>
            </div>
            <div>
              <label className="block text-xs font-medium uppercase text-secondary-400">Record ID</label>
              <p className="mt-1 text-sm font-mono text-secondary-900">{selectedRecord.record_id || "—"}</p>
            </div>
            <div>
              <label className="block text-xs font-medium uppercase text-secondary-400">Action</label>
              <p className="mt-1 text-sm capitalize text-secondary-900">{selectedRecord.action}</p>
            </div>
            <div>
              <label className="block text-xs font-medium uppercase text-secondary-400">User</label>
              <p className="mt-1 text-sm text-secondary-900">{selectedRecord.user_name}</p>
            </div>
            <div>
              <label className="block text-xs font-medium uppercase text-secondary-400">IP Address</label>
              <p className="mt-1 font-mono text-sm text-secondary-900">
                {selectedRecord.ip_address || "—"}
              </p>
            </div>
            <div>
              <label className="block text-xs font-medium uppercase text-secondary-400">Company</label>
              <p className="mt-1 text-sm text-secondary-900">
                {selectedRecord.company_name || "—"}
              </p>
            </div>
            <div>
              <label className="block text-xs font-medium uppercase text-secondary-400">Timestamp</label>
              <p className="mt-1 text-sm text-secondary-900">
                {new Date(selectedRecord.timestamp).toLocaleString()}
              </p>
            </div>
          </div>
        </AccordionSection>

        <AccordionSection
          title={`Changes (${changeKeys.length})`}
          isOpen={activeSection === "changes"}
          onToggle={() => toggleSection("changes")}
        >
          <div className="space-y-3">
            {changeKeys.length === 0 && (
              <p className="text-sm text-secondary-500">No changes recorded.</p>
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
  }

  function viewContent() {
    if (activeView === "detail" && selectedRecord) {
      return renderDetail();
    }
    return (
      <div className="flex h-48 items-center justify-center text-sm text-secondary-400">
        Select an entry to view details
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex h-48 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
      </div>
    );
  }

  if (isMobile) {
    if (activeView === "list") {
      return (
        <div className="p-4">
          <div className="mb-4 flex items-center justify-between">
            <h1 className="text-xl font-bold text-secondary-900">Audit Log</h1>
          </div>
          {renderList()}
        </div>
      );
    }
    return (
      <div className="p-4">
        <div className="mb-4 flex items-center gap-2">
          <button
            onClick={() => {
              setActiveView("list");
              setSelectedRecord(null);
            }}
            className="inline-flex items-center gap-1 text-sm font-medium text-secondary-600 hover:text-secondary-900"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </button>
          <h1 className="text-lg font-bold text-secondary-900">Audit Detail</h1>
        </div>
        {renderDetail()}
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 h-[calc(100vh-4rem)]">
      <FormPageLayout
        leftPanel={{
          id: "list",
          label: "Audit Log",
          content: (
            <div>
              <div className="mb-4 flex items-center justify-between">
                <h1 className="text-xl font-bold text-secondary-900">Audit Log</h1>
                <span className="text-xs text-secondary-500">{totalCount} entries</span>
              </div>
              {renderList()}
            </div>
          ),
        }}
        rightPanel={{
          id: "detail",
          label: "Detail",
          content: viewContent(),
        }}
      />
    </div>
  );
}

function formatChangeValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return String(value);
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
