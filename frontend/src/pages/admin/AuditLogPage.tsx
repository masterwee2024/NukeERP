import AccordionSection from "@/components/shared/AccordionSection";
import DynamicListDetailPage from "@/components/shared/DynamicListDetailPage";

export default function AuditLogPage() {
  return (
    <DynamicListDetailPage
      configKey="admin.audit-logs"
      actionSlots={{
        betweenSections: (record) => {
          const changes = (record.changes as Record<string, { old: unknown; new: unknown }>) ?? {};
          const changeKeys = Object.keys(changes);
          return (
            <div className="mt-4">
              <AccordionSection title={`Changes (${changeKeys.length})`} isOpen={true} onToggle={() => {}}>
                <div className="space-y-3">
                  {changeKeys.length === 0 && <p className="text-sm text-secondary-500">No changes recorded.</p>}
                  {changeKeys.map((field) => {
                    const change = changes[field];
                    return (
                      <div key={field} className="rounded-lg border border-secondary-200 bg-secondary-50 p-3">
                        <label className="block text-xs font-medium uppercase text-secondary-500">{field}</label>
                        <div className="mt-1 grid grid-cols-2 gap-3">
                          <div>
                            <span className="text-xs text-danger-500">Old:</span>
                            <p className="mt-0.5 truncate font-mono text-sm text-secondary-700">{formatValue(change.old)}</p>
                          </div>
                          <div>
                            <span className="text-xs text-success-600">New:</span>
                            <p className="mt-0.5 truncate font-mono text-sm text-secondary-900">{formatValue(change.new)}</p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </AccordionSection>
            </div>
          );
        },
      }}
    />
  );
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return String(value);
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
