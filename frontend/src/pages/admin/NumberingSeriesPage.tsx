import { useState } from "react";
import { useConfirm } from "@/components/ui/ConfirmDialog";
import { useNumberingSeries, type NumberingSeries } from "@/hooks/useNumberingSeries";
import { useCompanies, type Company } from "@/hooks/useCompanyContext";
import { useIsMobile } from "@/hooks/useIsMobile";
import AccordionSection from "@/components/shared/AccordionSection";
import FormPageLayout from "@/components/shared/FormPageLayout";
import { Pencil, Trash2, Plus, ArrowLeft, Loader2 } from "lucide-react";

const RESET_PERIODS = [
  { value: "yearly", label: "Yearly" },
  { value: "monthly", label: "Monthly" },
  { value: "never", label: "Never" },
];

const INITIAL_FORM = {
  document_type: "",
  prefix: "",
  date_format: "YYYYMM",
  next_number: 1,
  reset_period: "yearly",
  padding: 6,
  company_id: "",
  description: "",
  id: "",
  updated_at: "",
};

export default function NumberingSeriesPage() {
  const { confirm } = useConfirm();
  const isMobile = useIsMobile();
  const { seriesList, isLoading, create, update, remove, isCreating, isUpdating } = useNumberingSeries();
  const { data: companiesData } = useCompanies();
  const companies = companiesData ?? [];

  const [selectedRecord, setSelectedRecord] = useState<NumberingSeries | null>(null);
  const [activeView, setActiveView] = useState<"list" | "detail" | "edit" | "create">("list");
  const [form, setForm] = useState(INITIAL_FORM);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [activeSection, setActiveSection] = useState("basic");

  const toggleSection = (section: string) => {
    setActiveSection((prev) => (prev === section ? "" : section));
  };

  const populateForm = (series: NumberingSeries) => ({
    document_type: series.document_type,
    prefix: series.prefix,
    date_format: series.date_format,
    next_number: series.next_number,
    reset_period: series.reset_period,
    padding: series.padding,
    company_id: series.company,
    description: series.description,
    id: series.id,
    updated_at: series.updated_at,
  });

  const handleRowClick = (series: NumberingSeries) => {
    setSelectedRecord(series);
    setForm(populateForm(series));
    setActiveView("detail");
    setError("");
    setSuccess("");
  };

  const handleCreate = () => {
    setSelectedRecord(null);
    setForm({ ...INITIAL_FORM, company_id: companies[0]?.id || "" });
    setActiveView("create");
    setError("");
    setSuccess("");
  };

  const handleEdit = () => {
    setActiveView("edit");
    setError("");
    setSuccess("");
  };

  const handleSave = async () => {
    if (!form.document_type || !form.company_id) {
      setError("Document type and company are required");
      return;
    }
    const label = `${form.prefix}${form.document_type}`;
    const isEdit = activeView === "edit";
    const confirmed = await confirm({
      title: isEdit ? "Update Numbering Series" : "Create Numbering Series",
      message: isEdit
        ? `Update numbering series "${label}"?`
        : `Create new numbering series "${label}"?`,
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
          next_number: form.next_number,
          reset_period: form.reset_period,
          padding: form.padding,
          description: form.description,
          updated_at: form.updated_at,
        });
        setSuccess("Numbering series updated");
      } else {
        await create({
          document_type: form.document_type,
          prefix: form.prefix,
          date_format: form.date_format,
          next_number: form.next_number,
          reset_period: form.reset_period,
          padding: form.padding,
          company_id: form.company_id,
          description: form.description,
        });
        setSuccess("Numbering series created");
      }
      setActiveView("list");
      setSelectedRecord(null);
      setError("");
      setTimeout(() => setSuccess(""), 3000);
    } catch (err: unknown) {
      const apiErr = err as { response?: { data?: { detail?: string } } };
      setError(apiErr?.response?.data?.detail || "Failed to save");
    }
  };

  const handleDelete = async (series: NumberingSeries) => {
    const confirmed = await confirm({
      title: "Delete Numbering Series",
      message: `Delete numbering series "${series.prefix}${series.document_type}"?`,
      variant: "danger",
      confirmText: "Delete",
    });
    if (!confirmed) return;
    try {
      await remove(series.id);
      setSuccess("Numbering series deleted");
      setSelectedRecord(null);
      setActiveView("list");
      setTimeout(() => setSuccess(""), 3000);
    } catch (err: unknown) {
      const apiErr = err as { response?: { data?: { detail?: string } } };
      setError(apiErr?.response?.data?.detail || "Failed to delete");
    }
  };

  const handleCancel = () => {
    if (activeView === "edit" && selectedRecord) {
      setForm(populateForm(selectedRecord));
      setActiveView("detail");
    } else {
      setActiveView("list");
    }
    setError("");
  };

  if (isLoading) {
    return (
      <div className="flex h-48 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
      </div>
    );
  }

  function renderList() {
    return (
      <div>
        {success && (
          <div className="mb-4 rounded-lg bg-success-50 p-3 text-sm text-success-700">{success}</div>
        )}
        <div className="overflow-x-auto rounded-lg border border-secondary-200 bg-white">
          <table className="min-w-full divide-y divide-secondary-200">
            <thead className="bg-secondary-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-secondary-500">Document Type</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-secondary-500">Prefix</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-secondary-500">Format</th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase text-secondary-500">Next #</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-secondary-100">
              {seriesList.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-sm text-secondary-500">
                    No numbering series configured.
                  </td>
                </tr>
              )}
              {seriesList.map((series) => (
                <tr
                  key={series.id}
                  className="cursor-pointer"
                  onClick={() => handleRowClick(series)}
                >
                  <td className="px-4 py-3 text-sm font-medium text-secondary-900">{series.document_type}</td>
                  <td className="px-4 py-3 text-sm text-secondary-700">"{series.prefix}"</td>
                  <td className="px-4 py-3 text-sm text-secondary-700">{series.date_format || "—"}</td>
                  <td className="px-4 py-3 text-right text-sm text-secondary-700">{series.next_number}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  function renderForm() {
    return (
      <div className="space-y-4">
        {error && (
          <div className="rounded-lg bg-danger-50 p-3 text-sm text-danger-700">{error}</div>
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
                onChange={(e) => setForm((p) => ({ ...p, document_type: e.target.value }))}
                placeholder="e.g., invoice, purchase_order"
                className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary-700">
                Company <span className="text-danger-500">*</span>
              </label>
              <select
                value={form.company_id}
                onChange={(e) => setForm((p) => ({ ...p, company_id: e.target.value }))}
                className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              >
                <option value="">Select company</option>
                {companies.map((c: Company) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary-700">Description</label>
              <input
                type="text"
                value={form.description}
                onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
                className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              />
            </div>
          </div>
        </AccordionSection>

        <AccordionSection
          title="Format Settings"
          isOpen={activeSection === "format"}
          onToggle={() => toggleSection("format")}
        >
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-secondary-700">Prefix</label>
              <input
                type="text"
                value={form.prefix}
                onChange={(e) => setForm((p) => ({ ...p, prefix: e.target.value }))}
                placeholder="INV-"
                className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary-700">Date Format</label>
              <input
                type="text"
                value={form.date_format}
                onChange={(e) => setForm((p) => ({ ...p, date_format: e.target.value }))}
                placeholder="YYYYMM"
                className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary-700">Next Number</label>
              <input
                type="number"
                value={form.next_number}
                onChange={(e) => setForm((p) => ({ ...p, next_number: parseInt(e.target.value) || 1 }))}
                className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary-700">Padding</label>
              <input
                type="number"
                value={form.padding}
                onChange={(e) => setForm((p) => ({ ...p, padding: parseInt(e.target.value) || 6 }))}
                className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary-700">Reset Period</label>
              <select
                value={form.reset_period}
                onChange={(e) => setForm((p) => ({ ...p, reset_period: e.target.value }))}
                className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              >
                {RESET_PERIODS.map((rp) => (
                  <option key={rp.value} value={rp.value}>{rp.label}</option>
                ))}
              </select>
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
            onClick={handleSave}
            disabled={isCreating || isUpdating}
            className="rounded-lg bg-primary-600 px-6 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            {isCreating || isUpdating ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
    );
  }

  function renderDetail() {
    if (!selectedRecord) return null;
    return (
      <div className="space-y-4">
        {error && (
          <div className="rounded-lg bg-danger-50 p-3 text-sm text-danger-700">{error}</div>
        )}
        <div className="flex gap-2">
          <button
            onClick={handleEdit}
            className="inline-flex items-center gap-1 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
          >
            {isMobile && <Pencil className="h-4 w-4" />}
            Edit
          </button>
          <button
            onClick={() => handleDelete(selectedRecord)}
            className="inline-flex items-center gap-1 rounded-lg bg-danger-600 px-4 py-2 text-sm font-medium text-white hover:bg-danger-700"
          >
            {isMobile && <Trash2 className="h-4 w-4" />}
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
              <label className="block text-xs font-medium uppercase text-secondary-400">Document Type</label>
              <p className="mt-1 text-sm text-secondary-900">{selectedRecord.document_type}</p>
            </div>
            <div>
              <label className="block text-xs font-medium uppercase text-secondary-400">Company</label>
              <p className="mt-1 text-sm text-secondary-900">{selectedRecord.company_name}</p>
            </div>
            <div>
              <label className="block text-xs font-medium uppercase text-secondary-400">Description</label>
              <p className="mt-1 text-sm text-secondary-900">{selectedRecord.description || "—"}</p>
            </div>
          </div>
        </AccordionSection>

        <AccordionSection
          title="Format Settings"
          isOpen={activeSection === "format"}
          onToggle={() => toggleSection("format")}
        >
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium uppercase text-secondary-400">Prefix</label>
              <p className="mt-1 text-sm text-secondary-900">"{selectedRecord.prefix}"</p>
            </div>
            <div>
              <label className="block text-xs font-medium uppercase text-secondary-400">Date Format</label>
              <p className="mt-1 text-sm text-secondary-900">{selectedRecord.date_format || "—"}</p>
            </div>
            <div>
              <label className="block text-xs font-medium uppercase text-secondary-400">Next Number</label>
              <p className="mt-1 text-sm text-secondary-900">{selectedRecord.next_number}</p>
            </div>
            <div>
              <label className="block text-xs font-medium uppercase text-secondary-400">Padding</label>
              <p className="mt-1 text-sm text-secondary-900">{selectedRecord.padding}</p>
            </div>
            <div>
              <label className="block text-xs font-medium uppercase text-secondary-400">Reset Period</label>
              <p className="mt-1 text-sm text-secondary-900 capitalize">{selectedRecord.reset_period}</p>
            </div>
          </div>
        </AccordionSection>
      </div>
    );
  }

  function viewContent() {
    if (activeView === "create") {
      return (
        <div>
          <h2 className="mb-4 text-lg font-semibold text-secondary-900">Create Numbering Series</h2>
          {renderForm()}
        </div>
      );
    }
    if (activeView === "edit") {
      return (
        <div>
          <h2 className="mb-4 text-lg font-semibold text-secondary-900">Edit Numbering Series</h2>
          {renderForm()}
        </div>
      );
    }
    if (activeView === "detail" && selectedRecord) {
      return renderDetail();
    }
    return (
      <div className="flex h-48 items-center justify-center text-sm text-secondary-400">
        Select a record to view
      </div>
    );
  }

  if (isMobile) {
    if (activeView === "list") {
      return (
        <div className="p-4">
          <div className="mb-4 flex items-center justify-between">
            <h1 className="text-xl font-bold text-secondary-900">Numbering Series</h1>
            <button
              onClick={handleCreate}
              className="inline-flex items-center justify-center rounded-lg bg-primary-600 p-2 text-white hover:bg-primary-700"
            >
              <Plus className="h-5 w-5" />
            </button>
          </div>
          {renderList()}
        </div>
      );
    }

    return (
      <div className="p-4">
        <div className="mb-4 flex items-center gap-2">
          <button
            onClick={() => { setActiveView("list"); setSelectedRecord(null); setError(""); }}
            className="inline-flex items-center gap-1 text-sm font-medium text-secondary-600 hover:text-secondary-900"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </button>
          <h1 className="text-lg font-bold text-secondary-900">
            {activeView === "create" ? "New Series" : selectedRecord?.document_type || ""}
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
          label: "Numbering Series",
          content: (
            <div>
              <div className="mb-4 flex items-center justify-between">
                <h1 className="text-xl font-bold text-secondary-900">Numbering Series</h1>
                <button
                  onClick={handleCreate}
                  className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
                >
                  + New Series
                </button>
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
