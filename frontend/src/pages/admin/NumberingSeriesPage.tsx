import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useConfirm } from "@/components/ui/ConfirmDialog";
import { useCompanies } from "@/hooks/useCompanyContext";
import DynamicListDetailPage from "@/components/shared/DynamicListDetailPage";
import api from "@/lib/api";
import { Building2, Pencil, Trash2 } from "lucide-react";

const RESET_PERIODS = [
  { value: "yearly", label: "Yearly" },
  { value: "monthly", label: "Monthly" },
  { value: "never", label: "Never" },
];

export default function NumberingSeriesPage() {
  const queryClient = useQueryClient();
  const { confirm } = useConfirm();
  const { data: companiesData } = useCompanies();
  const companies = companiesData ?? [];

  const [editAssignment, setEditAssignment] = useState<{
    id: string;
    company_name: string;
    next_number: number;
    reset_period: string;
    updated_at: string;
  } | null>(null);

  const assignMutation = useMutation({
    mutationFn: async ({ pid, cid }: { pid: string; cid: string }) => {
      await api.post(`/core/admin/numbering-policies/${pid}/assign/`, {
        company_id: cid,
      });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["numbering-policy"] }),
  });

  const updateAssignMutation = useMutation({
    mutationFn: async ({
      pid,
      aid,
      payload,
    }: {
      pid: string;
      aid: string;
      payload: Record<string, unknown>;
    }) => {
      const { data } = await api.put(
        `/core/admin/numbering-policies/${pid}/assign/${aid}/`,
        payload
      );
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["numbering-policy"] }),
  });

  const unassignMutation = useMutation({
    mutationFn: async ({ pid, aid }: { pid: string; aid: string }) => {
      await api.delete(`/core/admin/numbering-policies/${pid}/assign/${aid}/`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["numbering-policy"] }),
  });

  const handleAssign = async (policyId: string, companyId: string) => {
    const name = companies.find((c) => c.id === companyId)?.name || companyId;
    const ok = await confirm({
      title: "Assign Company",
      message: `Assign to "${name}"?`,
      variant: "info",
      confirmText: "Assign",
    });
    if (ok) assignMutation.mutate({ pid: policyId, cid: companyId });
  };

  const handleUnassign = async (
    policyId: string,
    assignmentId: string,
    companyName: string
  ) => {
    const ok = await confirm({
      title: "Unassign",
      message: `Remove "${companyName}"?`,
      variant: "danger",
      confirmText: "Unassign",
    });
    if (ok) {
      unassignMutation.mutate({ pid: policyId, aid: assignmentId });
      setEditAssignment(null);
    }
  };

  const handleEditAssignmentStart = (a: {
    id: string;
    company_name: string;
    next_number: number;
    reset_period: string;
    updated_at: string;
  }) => {
    setEditAssignment(a);
  };

  const handleSaveAssignment = async (policyId: string) => {
    if (!editAssignment) return;
    const ok = await confirm({
      title: "Update Assignment",
      message: `Update "${editAssignment.company_name}"?`,
      variant: "warning",
      confirmText: "Save",
    });
    if (!ok) return;
    updateAssignMutation.mutate({
      pid: policyId,
      aid: editAssignment.id,
      payload: {
        next_number: editAssignment.next_number,
        reset_period: editAssignment.reset_period,
        updated_at: editAssignment.updated_at,
      },
    });
    setEditAssignment(null);
  };

  return (
    <DynamicListDetailPage
      configKey="admin.numbering-policies"
      actionSlots={{
        betweenSections: (record) => {
          const assignments =
            ((record as Record<string, unknown>).company_assignments as Array<{
              id: string;
              company_id: string;
              company_name: string;
              next_number: number;
              reset_period: string;
              updated_at: string;
            }>) ?? [];
          const assignedIds = new Set(assignments.map((a) => a.company_id));
          const unassigned = companies.filter((c) => !assignedIds.has(c.id));
          const policyId = String(record.id);

          if (editAssignment) {
            return (
              <div className="mt-4 space-y-4 rounded-lg border border-secondary-200 bg-white p-4">
                <h3 className="text-sm font-semibold text-secondary-900">
                  Edit: {editAssignment.company_name}
                </h3>
                <div>
                  <label className="block text-sm font-medium text-secondary-700">
                    Next Number
                  </label>
                  <input
                    type="number"
                    value={editAssignment.next_number}
                    onChange={(e) =>
                      setEditAssignment((p) =>
                        p ? { ...p, next_number: parseInt(e.target.value) || 1 } : null
                      )
                    }
                    className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-secondary-700">
                    Reset Period
                  </label>
                  <select
                    value={editAssignment.reset_period}
                    onChange={(e) =>
                      setEditAssignment((p) =>
                        p ? { ...p, reset_period: e.target.value } : null
                      )
                    }
                    className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
                  >
                    {RESET_PERIODS.map((rp) => (
                      <option key={rp.value} value={rp.value}>
                        {rp.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex justify-end gap-3">
                  <button
                    onClick={() => setEditAssignment(null)}
                    className="rounded-lg border border-secondary-300 px-4 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => handleSaveAssignment(policyId)}
                    className="rounded-lg bg-primary-600 px-6 py-2 text-sm font-medium text-white hover:bg-primary-700"
                  >
                    Save
                  </button>
                </div>
              </div>
            );
          }

          return (
            <div className="mt-4 space-y-3">
              <h3 className="text-sm font-semibold text-secondary-900">
                Assigned Companies ({assignments.length})
              </h3>
              {assignments.length === 0 ? (
                <p className="text-sm text-secondary-500">No companies assigned yet.</p>
              ) : (
                assignments.map((a) => (
                  <div
                    key={a.id}
                    className="rounded-lg border border-secondary-200 bg-white p-3"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Building2 className="h-4 w-4 text-secondary-400" />
                        <span className="text-sm font-medium text-secondary-900">
                          {a.company_name}
                        </span>
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleEditAssignmentStart(a)}
                          className="rounded p-1 text-secondary-400 hover:bg-secondary-100 hover:text-primary-600"
                          title="Edit"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={() => handleUnassign(policyId, a.id, a.company_name)}
                          className="rounded p-1 text-secondary-400 hover:bg-danger-50 hover:text-danger-600"
                          title="Unassign"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-xs text-secondary-500">
                      <span>Next: {a.next_number}</span>
                      <span className="text-secondary-300">|</span>
                      <span className="capitalize">{a.reset_period}</span>
                    </div>
                  </div>
                ))
              )}
              {unassigned.length > 0 && (
                <select
                  className="w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
                  value=""
                  onChange={(e) => {
                    if (e.target.value) handleAssign(policyId, e.target.value);
                  }}
                >
                  <option value="" disabled>
                    + Assign company...
                  </option>
                  {unassigned.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              )}
            </div>
          );
        },
      }}
    />
  );
}
