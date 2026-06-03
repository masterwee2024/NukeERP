import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useConfirm } from "@/components/ui/ConfirmDialog";
import {
  useNumberingPolicies,
  type NumberingPolicy,
  type PolicyListItem,
  type CompanyAssignment,
} from "@/hooks/useNumberingSeries";
import { useCompanies } from "@/hooks/useCompanyContext";
import { useIsMobile } from "@/hooks/useIsMobile";
import AccordionSection from "@/components/shared/AccordionSection";
import FormPageLayout from "@/components/shared/FormPageLayout";
import api from "@/lib/api";
import {
  Pencil,
  Trash2,
  Plus,
  ArrowLeft,
  Loader2,
  Building2,
} from "lucide-react";

const RESET_PERIODS = [
  { value: "yearly", label: "Yearly" },
  { value: "monthly", label: "Monthly" },
  { value: "never", label: "Never" },
];

interface PolicyForm {
  document_type: string;
  prefix: string;
  date_format: string;
  padding: number;
  description: string;
  id: string;
  updated_at: string;
}

const INITIAL_POLICY_FORM: PolicyForm = {
  document_type: "",
  prefix: "",
  date_format: "YYYYMM",
  padding: 6,
  description: "",
  id: "",
  updated_at: "",
};

export default function NumberingSeriesPage() {
  const { confirm } = useConfirm();
  const isMobile = useIsMobile();
  const {
    policies,
    isLoading,
    create,
    update,
    remove,
    assign,
    updateAssignment,
    unassign,
    isCreating,
    isUpdating,
  } = useNumberingPolicies();
  const { data: companiesData } = useCompanies();
  const companies = companiesData ?? [];

  const [selectedPolicy, setSelectedPolicy] = useState<PolicyListItem | null>(null);
  const [policyDetail, setPolicyDetail] = useState<NumberingPolicy | null>(null);
  const [activeView, setActiveView] = useState<"list" | "detail" | "edit" | "create">("list");
  const [activeSubView, setActiveSubView] = useState<"main" | "edit-assignment">("main");
  const [form, setForm] = useState(INITIAL_POLICY_FORM);
  const [editAssignment, setEditAssignment] = useState<CompanyAssignment | null>(null);
  const [editAssignmentForm, setEditAssignmentForm] = useState({ next_number: 1, reset_period: "yearly", updated_at: "" });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [activeSection, setActiveSection] = useState("basic");

  const toggleSection = (section: string) => {
    setActiveSection((prev) => (prev === section ? "" : section));
  };

  // Fetch policy detail when selected
  const { data: fetchedDetail, isLoading: detailLoading } = useQuery({
    queryKey: ["numbering-policy", selectedPolicy?.id],
    queryFn: async (): Promise<NumberingPolicy> => {
      const { data } = await api.get(
        `/core/admin/numbering-policies/${selectedPolicy!.id}/`,
      );
      return data;
    },
    enabled: !!selectedPolicy,
    staleTime: 15 * 1000,
  });

  useEffect(() => {
    if (fetchedDetail) {
      setPolicyDetail(fetchedDetail);
    }
  }, [fetchedDetail]);

  const populatePolicyForm = (p: NumberingPolicy) => ({
    document_type: p.document_type,
    prefix: p.prefix,
    date_format: p.date_format,
    padding: p.padding,
    description: p.description,
    id: p.id,
    updated_at: p.updated_at,
  });

  const handleSelectPolicy = (p: PolicyListItem) => {
    setSelectedPolicy(p);
    setPolicyDetail(null);
    setForm(populatePolicyForm({ ...p, company_assignments: [], created_at: "", updated_at: "", version: 0 }));
    setActiveView("detail");
    setActiveSubView("main");
    setError("");
    setSuccess("");
  };

  const handleCreate = () => {
    setSelectedPolicy(null);
    setPolicyDetail(null);
    setForm(INITIAL_POLICY_FORM);
    setActiveView("create");
    setError("");
    setSuccess("");
  };

  const handleEdit = () => {
    if (!policyDetail) return;
    setForm(populatePolicyForm(policyDetail));
    setActiveView("edit");
    setError("");
    setSuccess("");
  };

  const handleSavePolicy = async () => {
    if (!form.document_type) {
      setError("Document type is required");
      return;
    }
    const isEdit = activeView === "edit";
    const label = form.document_type;
    const confirmed = await confirm({
      title: isEdit ? "Update Numbering Policy" : "Create Numbering Policy",
      message: isEdit
        ? `Update policy "${label}"?`
        : `Create new policy "${label}"?`,
      variant: "warning",
      confirmText: isEdit ? "Update" : "Create",
    });
    if (!confirmed) return;
    try {
      if (isEdit && form.id) {
        await update(form.id, {
          document_type: form.document_type,
          prefix: form.prefix,
          date_format: form.date_format,
          padding: form.padding,
          description: form.description,
          updated_at: form.updated_at,
        });
        setSuccess("Policy updated");
      } else {
        await create({
          document_type: form.document_type,
          prefix: form.prefix,
          date_format: form.date_format,
          padding: form.padding,
          description: form.description,
        });
        setSuccess("Policy created");
      }
      setActiveView("list");
      setSelectedPolicy(null);
      setError("");
      setTimeout(() => setSuccess(""), 3000);
    } catch (err: unknown) {
      const apiErr = err as { response?: { data?: { detail?: string } } };
      setError(apiErr?.response?.data?.detail || "Failed to save");
    }
  };

  const handleDeletePolicy = async (p: PolicyListItem) => {
    const confirmed = await confirm({
      title: "Delete Numbering Policy",
      message: `Delete policy "${p.document_type}"? This will remove assignments for all companies.`,
      variant: "danger",
      confirmText: "Delete",
    });
    if (!confirmed) return;
    try {
      await remove(p.id);
      setSuccess("Policy deleted");
      setSelectedPolicy(null);
      setActiveView("list");
      setTimeout(() => setSuccess(""), 3000);
    } catch (err: unknown) {
      const apiErr = err as { response?: { data?: { detail?: string } } };
      setError(apiErr?.response?.data?.detail || "Failed to delete");
    }
  };

  const handleCancel = () => {
    if (activeView === "edit" && policyDetail) {
      setForm(populatePolicyForm(policyDetail));
      setActiveView("detail");
    } else {
      setActiveView("list");
    }
    setActiveSubView("main");
    setError("");
  };

  const handleAssignCompany = async (companyId: string) => {
    if (!policyDetail) return;
    const company = companies.find((c) => c.id === companyId);
    const confirmed = await confirm({
      title: "Assign Company",
      message: `Assign policy "${policyDetail.document_type}" to "${company?.name || companyId}"?`,
      variant: "info",
      confirmText: "Assign",
    });
    if (!confirmed) return;
    try {
      await assign(policyDetail.id, companyId);
      setSuccess("Company assigned");
      setTimeout(() => setSuccess(""), 3000);
    } catch (err: unknown) {
      const apiErr = err as { response?: { data?: { detail?: string } } };
      setError(apiErr?.response?.data?.detail || "Failed to assign");
    }
  };

  const handleUnassign = async (assignment: CompanyAssignment) => {
    if (!policyDetail) return;
    const confirmed = await confirm({
      title: "Unassign Company",
      message: `Remove "${assignment.company_name}" from this policy?`,
      variant: "danger",
      confirmText: "Unassign",
    });
    if (!confirmed) return;
    try {
      await unassign(policyDetail.id, assignment.id);
      setSuccess("Company unassigned");
      setActiveSubView("main");
      setEditAssignment(null);
      setTimeout(() => setSuccess(""), 3000);
    } catch (err: unknown) {
      const apiErr = err as { response?: { data?: { detail?: string } } };
      setError(apiErr?.response?.data?.detail || "Failed to unassign");
    }
  };

  const handleEditAssignmentStart = (assignment: CompanyAssignment) => {
    setEditAssignment(assignment);
    setEditAssignmentForm({
      next_number: assignment.next_number,
      reset_period: assignment.reset_period,
      updated_at: assignment.updated_at,
    });
    setActiveSubView("edit-assignment");
    setError("");
  };

  const handleSaveAssignment = async () => {
    if (!policyDetail || !editAssignment) return;
    const confirmed = await confirm({
      title: "Update Assignment",
      message: `Update numbering for "${editAssignment.company_name}"?`,
      variant: "warning",
      confirmText: "Save",
    });
    if (!confirmed) return;
    try {
      await updateAssignment(policyDetail.id, editAssignment.id, {
        next_number: editAssignmentForm.next_number,
        reset_period: editAssignmentForm.reset_period,
        updated_at: editAssignmentForm.updated_at,
      });
      setSuccess("Assignment updated");
      setActiveSubView("main");
      setEditAssignment(null);
      setTimeout(() => setSuccess(""), 3000);
    } catch (err: unknown) {
      const apiErr = err as { response?: { data?: { detail?: string } } };
      setError(apiErr?.response?.data?.detail || "Failed to update");
    }
  };

  // --- Render helpers ---

  function renderPolicyList() {
    return (
      <div>
        {success && (
          <div className="mb-4 rounded-lg bg-success-50 p-3 text-sm text-success-700">
            {success}
          </div>
        )}
        <div className="space-y-2">
          {policies.length === 0 ? (
            <div className="py-8 text-center text-sm text-secondary-500">
              No numbering policies configured.
            </div>
          ) : (
            policies.map((p) => (
              <div
                key={p.id}
                className={`cursor-pointer rounded-lg border bg-white p-3 ${
                  selectedPolicy?.id === p.id
                    ? "border-primary-400 ring-1 ring-primary-200"
                    : "border-secondary-200"
                }`}
                onClick={() => handleSelectPolicy(p)}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-secondary-900">
                    {p.document_type}
                  </span>
                  <span className="text-xs text-secondary-500">
                    "{p.prefix}"
                  </span>
                </div>
                <div className="mt-1 flex items-center gap-2 text-xs text-secondary-500">
                  <span>{p.date_format || "—"}</span>
                  <span className="text-secondary-300">|</span>
                  <span>Pad: {p.padding}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    );
  }

  function renderPolicyForm() {
    return (
      <div className="space-y-4">
        {error && (
          <div className="rounded-lg bg-danger-50 p-3 text-sm text-danger-700">
            {error}
          </div>
        )}
        <AccordionSection
          title="Basic Information"
          isOpen={activeSection === "basic"}
          onToggle={() => toggleSection("basic")}
        >
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-secondary-700">
                Document Type <span className="text-danger-500">*</span>
              </label>
              <input
                type="text"
                value={form.document_type}
                onChange={(e) =>
                  setForm((p) => ({ ...p, document_type: e.target.value }))
                }
                placeholder="e.g., invoice, purchase_order"
                className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary-700">Prefix</label>
              <input
                type="text"
                value={form.prefix}
                onChange={(e) =>
                  setForm((p) => ({ ...p, prefix: e.target.value }))
                }
                placeholder="INV-"
                className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              />
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-secondary-700">
                  Date Format
                </label>
                <input
                  type="text"
                  value={form.date_format}
                  onChange={(e) =>
                    setForm((p) => ({ ...p, date_format: e.target.value }))
                  }
                  placeholder="YYYYMM"
                  className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-secondary-700">
                  Padding
                </label>
                <input
                  type="number"
                  value={form.padding}
                  onChange={(e) =>
                    setForm((p) => ({
                      ...p,
                      padding: parseInt(e.target.value) || 6,
                    }))
                  }
                  className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary-700">Description</label>
              <input
                type="text"
                value={form.description}
                onChange={(e) =>
                  setForm((p) => ({ ...p, description: e.target.value }))
                }
                className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              />
            </div>
          </div>
        </AccordionSection>
        <div className="flex justify-end gap-3">
          <button
            onClick={handleCancel}
            className="rounded-lg border border-secondary-300 px-4 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSavePolicy}
            disabled={isCreating || isUpdating}
            className="rounded-lg bg-primary-600 px-6 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            {isCreating || isUpdating ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
    );
  }

  function renderAssignments() {
    if (!policyDetail) return null;
    const assignments = policyDetail.company_assignments || [];
    const assignedCompanyIds = new Set(assignments.map((a) => a.company_id));
    const unassignedCompanies = companies.filter(
      (c) => !assignedCompanyIds.has(c.id),
    );

    if (activeSubView === "edit-assignment" && editAssignment) {
      return (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-secondary-900">
            Edit: {editAssignment.company_name}
          </h3>
          <div>
            <label className="block text-sm font-medium text-secondary-700">
              Next Number
            </label>
            <input
              type="number"
              value={editAssignmentForm.next_number}
              onChange={(e) =>
                setEditAssignmentForm((p) => ({
                  ...p,
                  next_number: parseInt(e.target.value) || 1,
                }))
              }
              className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-secondary-700">
              Reset Period
            </label>
            <select
              value={editAssignmentForm.reset_period}
              onChange={(e) =>
                setEditAssignmentForm((p) => ({
                  ...p,
                  reset_period: e.target.value,
                }))
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
              onClick={() => {
                setActiveSubView("main");
                setEditAssignment(null);
              }}
              className="rounded-lg border border-secondary-300 px-4 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSaveAssignment}
              className="rounded-lg bg-primary-600 px-6 py-2 text-sm font-medium text-white hover:bg-primary-700"
            >
              Save
            </button>
          </div>
        </div>
      );
    }

    return (
      <div className="space-y-3">
        {assignments.length === 0 ? (
          <p className="py-4 text-center text-sm text-secondary-500">
            No companies assigned yet.
          </p>
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
                    title="Edit assignment"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={() => handleUnassign(a)}
                    className="rounded p-1 text-secondary-400 hover:bg-danger-50 hover:text-danger-600"
                    title="Unassign company"
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

        {unassignedCompanies.length > 0 && (
          <div className="pt-2">
            <select
              className="w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              value=""
              onChange={(e) => {
                if (e.target.value) handleAssignCompany(e.target.value);
              }}
            >
              <option value="" disabled>
                + Assign company...
              </option>
              {unassignedCompanies.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>
    );
  }

  function renderPolicyDetail() {
    if (!policyDetail) return null;
    return (
      <div className="space-y-4">
        {error && (
          <div className="rounded-lg bg-danger-50 p-3 text-sm text-danger-700">
            {error}
          </div>
        )}
        <div className="flex gap-2">
          <button
            onClick={handleEdit}
            className="inline-flex items-center gap-1 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
          >
            <Pencil className="h-4 w-4" />
            Edit Policy
          </button>
          <button
            onClick={() => handleDeletePolicy(policyDetail)}
            className="inline-flex items-center gap-1 rounded-lg bg-danger-600 px-4 py-2 text-sm font-medium text-white hover:bg-danger-700"
          >
            <Trash2 className="h-4 w-4" />
            Delete
          </button>
        </div>

        <AccordionSection
          title="Basic Information"
          isOpen={activeSection === "basic"}
          onToggle={() => toggleSection("basic")}
        >
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium uppercase text-secondary-400">
                Document Type
              </label>
              <p className="mt-1 text-sm text-secondary-900">
                {policyDetail.document_type}
              </p>
            </div>
            <div>
              <label className="block text-xs font-medium uppercase text-secondary-400">
                Prefix
              </label>
              <p className="mt-1 text-sm text-secondary-900">
                "{policyDetail.prefix}"
              </p>
            </div>
            <div>
              <label className="block text-xs font-medium uppercase text-secondary-400">
                Date Format
              </label>
              <p className="mt-1 text-sm text-secondary-900">
                {policyDetail.date_format || "—"}
              </p>
            </div>
            <div>
              <label className="block text-xs font-medium uppercase text-secondary-400">
                Padding
              </label>
              <p className="mt-1 text-sm text-secondary-900">
                {policyDetail.padding}
              </p>
            </div>
            <div>
              <label className="block text-xs font-medium uppercase text-secondary-400">
                Description
              </label>
              <p className="mt-1 text-sm text-secondary-900">
                {policyDetail.description || "—"}
              </p>
            </div>
          </div>
        </AccordionSection>

        <AccordionSection
          title={`Assigned Companies (${(policyDetail.company_assignments || []).length})`}
          isOpen={activeSection === "assignments"}
          onToggle={() => toggleSection("assignments")}
        >
          {renderAssignments()}
        </AccordionSection>
      </div>
    );
  }

  function viewContent() {
    if (activeView === "create") {
      return (
        <div>
          <h2 className="mb-4 text-lg font-semibold text-secondary-900">
            Create Numbering Policy
          </h2>
          {renderPolicyForm()}
        </div>
      );
    }
    if (activeView === "edit") {
      return (
        <div>
          <h2 className="mb-4 text-lg font-semibold text-secondary-900">
            Edit Numbering Policy
          </h2>
          {renderPolicyForm()}
        </div>
      );
    }
    if (activeView === "detail" && policyDetail) {
      return detailLoading ? (
        <div className="flex h-48 items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-primary-500" />
        </div>
      ) : (
        renderPolicyDetail()
      );
    }
    return (
      <div className="flex h-48 items-center justify-center text-sm text-secondary-400">
        Select a policy to view details
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
            <h1 className="text-xl font-bold text-secondary-900">
              Numbering Policies
            </h1>
            <button
              onClick={handleCreate}
              className="inline-flex items-center justify-center rounded-lg bg-primary-600 p-2 text-white hover:bg-primary-700"
            >
              <Plus className="h-5 w-5" />
            </button>
          </div>
          {renderPolicyList()}
        </div>
      );
    }
    return (
      <div className="p-4">
        <div className="mb-4 flex items-center gap-2">
          <button
            onClick={() => {
              setActiveView("list");
              setSelectedPolicy(null);
              setPolicyDetail(null);
              setError("");
            }}
            className="inline-flex items-center gap-1 text-sm font-medium text-secondary-600 hover:text-secondary-900"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </button>
          <h1 className="text-lg font-bold text-secondary-900">
            {activeView === "create"
              ? "New Policy"
              : policyDetail?.document_type || ""}
          </h1>
        </div>
        {viewContent()}
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 h-[calc(100vh-4rem)]">
      <FormPageLayout
        leftPanel={{
          id: "list",
          label: "Numbering Policies",
          content: (
            <div>
              <div className="mb-4 flex items-center justify-between">
                <h1 className="text-xl font-bold text-secondary-900">
                  Numbering Policies
                </h1>
                <button
                  onClick={handleCreate}
                  className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
                >
                  + New Policy
                </button>
              </div>
              {renderPolicyList()}
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
