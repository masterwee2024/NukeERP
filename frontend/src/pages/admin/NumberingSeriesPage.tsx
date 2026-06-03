import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useConfirm } from "@/components/ui/ConfirmDialog";
import { useCompanies } from "@/hooks/useCompanyContext";
import AccordionSection from "@/components/shared/AccordionSection";
import DynamicListDetailPage from "@/components/shared/DynamicListDetailPage";
import api from "@/lib/api";
import { Building2, Pencil, Trash2, Loader2 } from "lucide-react";

interface Policy {
  id: string;
  document_type: string;
  prefix: string;
  date_format: string;
  padding: number;
  description: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  version: number;
  company_assignments: Assignment[];
}

interface PolicyListItem {
  id: string;
  document_type: string;
  prefix: string;
  date_format: string;
  padding: number;
  description: string;
  is_active: boolean;
}

interface Assignment {
  id: string;
  company_id: string;
  company_name: string;
  next_number: number;
  reset_period: string;
  last_reset_at: string | null;
  is_active: boolean;
  updated_at: string;
  version: number;
}

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

  const [selected, setSelected] = useState<Policy | null>(null);
  const [view, setView] = useState<"list" | "detail" | "edit" | "create">("list");
  const [error, setError] = useState("");
  const [activeSection, setActiveSection] = useState("basic");
  const [editAssignment, setEditAssignment] = useState<Assignment | null>(null);
  const [editAssignmentForm, setEditAssignmentForm] = useState({ next_number: 1, reset_period: "yearly", updated_at: "" });

  const [formDocType, setFormDocType] = useState("");
  const [formPrefix, setFormPrefix] = useState("");
  const [formDateFormat, setFormDateFormat] = useState("YYYYMM");
  const [formPadding, setFormPadding] = useState(6);
  const [formDesc, setFormDesc] = useState("");

  const { data: policies = [], isLoading } = useQuery({
    queryKey: ["numbering-policies"],
    queryFn: async (): Promise<PolicyListItem[]> => {
      const { data } = await api.get("/core/admin/numbering-policies/");
      return data;
    },
    staleTime: 30 * 1000,
  });

  const { data: policyDetail, isLoading: detailLoading } = useQuery({
    queryKey: ["numbering-policy", selected?.id],
    queryFn: async (): Promise<Policy> => {
      const { data } = await api.get(`/core/admin/numbering-policies/${selected!.id}/`);
      return data;
    },
    enabled: !!selected && view === "detail",
    staleTime: 15 * 1000,
  });

  const createMutation = useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const { data } = await api.post("/core/admin/numbering-policies/", payload);
      return data;
    },
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["numbering-policies"] }); setView("list"); },
    onError: (err: unknown) => setError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed"),
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: Record<string, unknown> }) => {
      const { data } = await api.put(`/core/admin/numbering-policies/${id}/`, payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["numbering-policies"] });
      queryClient.invalidateQueries({ queryKey: ["numbering-policy"] });
      setView("detail");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => { await api.delete(`/core/admin/numbering-policies/${id}/`); },
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["numbering-policies"] }); setSelected(null); setView("list"); },
  });

  const assignMutation = useMutation({
    mutationFn: async ({ pid, cid }: { pid: string; cid: string }) => {
      await api.post(`/core/admin/numbering-policies/${pid}/assign/`, { company_id: cid });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["numbering-policy"] }),
  });

  const updateAssignMutation = useMutation({
    mutationFn: async ({ pid, aid, payload }: { pid: string; aid: string; payload: Record<string, unknown> }) => {
      const { data } = await api.put(`/core/admin/numbering-policies/${pid}/assign/${aid}/`, payload);
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

  const toggleSection = (section: string) => {
    setActiveSection((prev) => (prev === section ? "" : section));
  };

  const initCreate = () => {
    setFormDocType(""); setFormPrefix(""); setFormDateFormat("YYYYMM"); setFormPadding(6); setFormDesc("");
    setError(""); setView("create");
  };

  const initEdit = (pol: Policy) => {
    setFormDocType(pol.document_type); setFormPrefix(pol.prefix); setFormDateFormat(pol.date_format);
    setFormPadding(pol.padding); setFormDesc(pol.description);
    setError(""); setView("edit");
  };

  const handleSavePolicy = async () => {
    const isEdit = view === "edit";
    if (!formDocType) { setError("Document type required"); return; }
    const confirmed = await confirm({
      title: isEdit ? "Update Policy" : "Create Policy",
      message: `${isEdit ? "Update" : "Create"} policy "${formDocType}"?`,
      variant: "warning",
      confirmText: isEdit ? "Update" : "Create",
    });
    if (!confirmed) return;
    if (isEdit && selected) {
      updateMutation.mutate({ id: selected.id, payload: { document_type: formDocType, prefix: formPrefix, date_format: formDateFormat, padding: formPadding, description: formDesc, updated_at: selected.updated_at } });
    } else {
      createMutation.mutate({ document_type: formDocType, prefix: formPrefix, date_format: formDateFormat, padding: formPadding, description: formDesc });
    }
  };

  const handleDelete = async (pol: PolicyListItem) => {
    const confirmed = await confirm({ title: "Delete Policy", message: `Delete "${pol.document_type}"?`, variant: "danger", confirmText: "Delete" });
    if (!confirmed) return;
    deleteMutation.mutate(pol.id);
  };

  const handleAssign = async (companyId: string) => {
    if (!selected) return;
    const name = companies.find((c) => c.id === companyId)?.name || companyId;
    const confirmed = await confirm({ title: "Assign Company", message: `Assign to "${name}"?`, variant: "info", confirmText: "Assign" });
    if (!confirmed) return;
    assignMutation.mutate({ pid: selected.id, cid: companyId });
  };

  const handleUnassign = async (a: Assignment) => {
    if (!selected) return;
    const confirmed = await confirm({ title: "Unassign", message: `Remove "${a.company_name}"?`, variant: "danger", confirmText: "Unassign" });
    if (!confirmed) return;
    unassignMutation.mutate({ pid: selected.id, aid: a.id });
    setEditAssignment(null);
  };

  const handleEditAssignmentStart = (a: Assignment) => {
    setEditAssignment(a);
    setEditAssignmentForm({ next_number: a.next_number, reset_period: a.reset_period, updated_at: a.updated_at });
  };

  const handleSaveAssignment = async () => {
    if (!selected || !editAssignment) return;
    const confirmed = await confirm({ title: "Update Assignment", message: `Update "${editAssignment.company_name}"?`, variant: "warning", confirmText: "Save" });
    if (!confirmed) return;
    updateAssignMutation.mutate({ pid: selected.id, aid: editAssignment.id, payload: { next_number: editAssignmentForm.next_number, reset_period: editAssignmentForm.reset_period, updated_at: editAssignmentForm.updated_at } });
    setEditAssignment(null);
  };

  function renderForm() {
    const isPending = createMutation.isPending || updateMutation.isPending;
    return (
      <div>
        {error && <div className="mb-4 rounded-lg bg-danger-50 p-3 text-sm text-danger-700">{error}</div>}
        <AccordionSection title="Basic Information" isOpen={activeSection === "basic"} onToggle={() => toggleSection("basic")}>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-secondary-700">Document Type <span className="text-danger-500">*</span></label>
              <input type="text" value={formDocType} onChange={(e) => setFormDocType(e.target.value)}
                placeholder="e.g., invoice, purchase_order" className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none" />
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-secondary-700">Prefix</label>
                <input type="text" value={formPrefix} onChange={(e) => setFormPrefix(e.target.value)} placeholder="INV-"
                  className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none" />
              </div>
              <div>
                <label className="block text-sm font-medium text-secondary-700">Date Format</label>
                <input type="text" value={formDateFormat} onChange={(e) => setFormDateFormat(e.target.value)} placeholder="YYYYMM"
                  className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none" />
              </div>
              <div>
                <label className="block text-sm font-medium text-secondary-700">Padding</label>
                <input type="number" value={formPadding} onChange={(e) => setFormPadding(parseInt(e.target.value) || 6)}
                  className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none" />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary-700">Description</label>
              <input type="text" value={formDesc} onChange={(e) => setFormDesc(e.target.value)}
                className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none" />
            </div>
          </div>
        </AccordionSection>
        <div className="mt-6 flex justify-end gap-3">
          <button onClick={() => setView("detail")}
            className="rounded-lg border border-secondary-300 px-4 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-50">Cancel</button>
          <button onClick={handleSavePolicy} disabled={isPending}
            className="rounded-lg bg-primary-600 px-6 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50">
            {isPending ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <DynamicListDetailPage<PolicyListItem>
      title="Numbering Policies"
      records={policies}
      isLoading={isLoading}
      toCard={(p) => ({
        id: p.id,
        label: p.document_type,
        sublabel: p.description || "",
        badge: { label: `"${p.prefix}"`, color: "bg-secondary-100 text-secondary-600" },
        meta: [
          { label: "Format", value: p.date_format || "—" },
          { label: "Pad", value: String(p.padding) },
        ],
      })}
      selectedRecord={selected as unknown as PolicyListItem}
      onSelect={(p) => {
        const found = policies.find((x) => x.id === p.id);
        if (found) { setSelected(found as unknown as Policy); setView("detail"); }
      }}
      viewState={view}
      onViewStateChange={(v) => { setView(v); if (v === "list") { setSelected(null); setError(""); } }}
      onCreate={initCreate}
      renderDetail={(pol) => {
        const detail = policyDetail;
        const detailPol = detail ?? pol;

        return (
          <div>
            {detailLoading && <div className="flex h-24 items-center justify-center"><Loader2 className="h-5 w-5 animate-spin text-primary-500" /></div>}
            {error && <div className="mb-4 rounded-lg bg-danger-50 p-3 text-sm text-danger-700">{error}</div>}
            <AccordionSection title="Basic Information" isOpen={activeSection === "basic"} onToggle={() => toggleSection("basic")}>
              <div className="space-y-3">
                <div><label className="block text-xs font-medium uppercase text-secondary-400">Document Type</label><p className="mt-1 text-sm text-secondary-900">{detailPol.document_type}</p></div>
                <div><label className="block text-xs font-medium uppercase text-secondary-400">Prefix</label><p className="mt-1 text-sm text-secondary-900">"{detailPol.prefix}"</p></div>
                <div><label className="block text-xs font-medium uppercase text-secondary-400">Date Format</label><p className="mt-1 text-sm text-secondary-900">{detailPol.date_format || "—"}</p></div>
                <div><label className="block text-xs font-medium uppercase text-secondary-400">Padding</label><p className="mt-1 text-sm text-secondary-900">{detailPol.padding}</p></div>
                <div><label className="block text-xs font-medium uppercase text-secondary-400">Description</label><p className="mt-1 text-sm text-secondary-900">{detailPol.description || "—"}</p></div>
              </div>
            </AccordionSection>
          </div>
        );
      }}
      onEdit={(pol) => {
        const detail = policyDetail;
        if (detail) initEdit(detail);
        else { setFormDocType(pol.document_type); setFormPrefix(pol.prefix); setFormDateFormat(pol.date_format); setFormPadding(pol.padding); setFormDesc(pol.description); setView("edit"); }
      }}
      onDelete={(pol) => handleDelete(pol)}
      renderForm={() => renderForm()}
      actionSlots={{
        betweenSections: () => {
          if (!policyDetail) return null;
          const assignments = policyDetail.company_assignments ?? [];
          const assignedIds = new Set(assignments.map((a) => a.company_id));
          const unassigned = companies.filter((c) => !assignedIds.has(c.id));

          if (editAssignment) {
            return (
              <div className="mt-4 space-y-4 rounded-lg border border-secondary-200 bg-white p-4">
                <h3 className="text-sm font-semibold text-secondary-900">Edit: {editAssignment.company_name}</h3>
                <div>
                  <label className="block text-sm font-medium text-secondary-700">Next Number</label>
                  <input type="number" value={editAssignmentForm.next_number}
                    onChange={(e) => setEditAssignmentForm((p) => ({ ...p, next_number: parseInt(e.target.value) || 1 }))}
                    className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-secondary-700">Reset Period</label>
                  <select value={editAssignmentForm.reset_period}
                    onChange={(e) => setEditAssignmentForm((p) => ({ ...p, reset_period: e.target.value }))}
                    className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none">
                    {RESET_PERIODS.map((rp) => (<option key={rp.value} value={rp.value}>{rp.label}</option>))}
                  </select>
                </div>
                <div className="flex justify-end gap-3">
                  <button onClick={() => setEditAssignment(null)}
                    className="rounded-lg border border-secondary-300 px-4 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-50">Cancel</button>
                  <button onClick={handleSaveAssignment}
                    className="rounded-lg bg-primary-600 px-6 py-2 text-sm font-medium text-white hover:bg-primary-700">Save</button>
                </div>
              </div>
            );
          }

          return (
            <div className="mt-4 space-y-3">
              <h3 className="text-sm font-semibold text-secondary-900">Assigned Companies ({assignments.length})</h3>
              {assignments.length === 0 ? (
                <p className="text-sm text-secondary-500">No companies assigned yet.</p>
              ) : (
                assignments.map((a) => (
                  <div key={a.id} className="rounded-lg border border-secondary-200 bg-white p-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Building2 className="h-4 w-4 text-secondary-400" />
                        <span className="text-sm font-medium text-secondary-900">{a.company_name}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <button onClick={() => handleEditAssignmentStart(a)}
                          className="rounded p-1 text-secondary-400 hover:bg-secondary-100 hover:text-primary-600" title="Edit"><Pencil className="h-3.5 w-3.5" /></button>
                        <button onClick={() => handleUnassign(a)}
                          className="rounded p-1 text-secondary-400 hover:bg-danger-50 hover:text-danger-600" title="Unassign"><Trash2 className="h-3.5 w-3.5" /></button>
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
                <select className="w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
                  value="" onChange={(e) => { if (e.target.value) handleAssign(e.target.value); }}>
                  <option value="" disabled>+ Assign company...</option>
                  {unassigned.map((c) => (<option key={c.id} value={c.id}>{c.name}</option>))}
                </select>
              )}
            </div>
          );
        },
      }}
    />
  );
}
