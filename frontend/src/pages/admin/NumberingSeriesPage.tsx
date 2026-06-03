import { useState } from "react";
import { useConfirm } from "@/components/ui/ConfirmDialog";
import { useNumberingSeries, type NumberingSeries, type NumberingSeriesCreate } from "@/hooks/useNumberingSeries";
import { useCompanies, type Company } from "@/hooks/useCompanyContext";

const RESET_PERIODS = [
  { value: "yearly", label: "Yearly" },
  { value: "monthly", label: "Monthly" },
  { value: "never", label: "Never" },
];

const INITIAL_FORM: NumberingSeriesCreate & { id?: string; updated_at?: string } = {
  document_type: "",
  prefix: "",
  date_format: "YYYYMM",
  next_number: 1,
  reset_period: "yearly",
  padding: 6,
  company_id: "",
  description: "",
};

export default function NumberingSeriesPage() {
  const { confirm } = useConfirm();
  const { seriesList, isLoading, create, update, remove, isCreating, isUpdating } = useNumberingSeries();
  const { data: companiesData } = useCompanies();
  const companies = companiesData ?? [];

  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [form, setForm] = useState(INITIAL_FORM);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const openCreate = () => {
    setEditing(null);
    setForm({ ...INITIAL_FORM, company_id: companies[0]?.id || "" });
    setShowForm(true);
    setError("");
  };

  const openEdit = (series: NumberingSeries) => {
    setEditing(series.id);
    setForm({
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
    setShowForm(true);
    setError("");
  };

  const handleSave = async () => {
    if (!form.document_type || !form.company_id) {
      setError("Document type and company are required");
      return;
    }
    const label = `${form.prefix}${form.document_type}`;
    const confirmed = await confirm({
      title: editing ? "Update Numbering Series" : "Create Numbering Series",
      message: editing
        ? `Update numbering series "${label}"?`
        : `Create new numbering series "${label}"?`,
      variant: "warning",
      confirmText: editing ? "Update" : "Create",
    });
    if (!confirmed) return;
    try {
      if (editing) {
        await update(editing, {
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
        await create(form);
        setSuccess("Numbering series created");
      }
      setShowForm(false);
      setEditing(null);
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
    if (confirmed) {
      try {
        await remove(series.id);
        setSuccess("Numbering series deleted");
        setTimeout(() => setSuccess(""), 3000);
      } catch (err: unknown) {
        const apiErr = err as { response?: { data?: { detail?: string } } };
        setError(apiErr?.response?.data?.detail || "Failed to delete");
      }
    }
  };

  const handleClose = () => {
    setShowForm(false);
    setEditing(null);
    setError("");
  };

  if (isLoading) {
    return (
      <div className="flex h-48 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent" />
      </div>
    );
  }

  if (showForm) {
    return (
      <div className="mx-auto max-w-2xl p-4 md:p-6">
        <h1 className="mb-6 text-xl font-bold text-secondary-900 md:text-2xl">
          {editing ? "Edit Numbering Series" : "Create Numbering Series"}
        </h1>

        {error && (
          <div className="mb-4 rounded-lg bg-danger-50 p-3 text-sm text-danger-700">{error}</div>
        )}

        <div className="space-y-4 rounded-lg border border-secondary-200 bg-white p-6">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-secondary-700">Document Type *</label>
              <input
                type="text"
                value={form.document_type}
                onChange={(e) => setForm((p) => ({ ...p, document_type: e.target.value }))}
                placeholder="e.g., invoice, purchase_order"
                className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary-700">Company *</label>
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
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
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
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
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

          <div className="flex justify-end gap-3">
            <button
              onClick={handleClose}
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
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-bold text-secondary-900 md:text-2xl">Numbering Series</h1>
        <button
          onClick={openCreate}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
        >
          + New Series
        </button>
      </div>

      {success && (
        <div className="mb-4 rounded-lg bg-success-50 p-3 text-sm text-success-700">{success}</div>
      )}
      {error && (
        <div className="mb-4 rounded-lg bg-danger-50 p-3 text-sm text-danger-700">{error}</div>
      )}

      <div className="overflow-x-auto rounded-lg border border-secondary-200 bg-white">
        <table className="min-w-full divide-y divide-secondary-200">
          <thead className="bg-secondary-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-secondary-500">Document Type</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-secondary-500">Prefix</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-secondary-500">Format</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-secondary-500">Next #</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-secondary-500">Reset</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-secondary-500">Company</th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase text-secondary-500">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-secondary-100">
            {seriesList.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-sm text-secondary-500">
                  No numbering series configured. Click "New Series" to create one.
                </td>
              </tr>
            )}
            {seriesList.map((series) => (
              <tr key={series.id} className="hover:bg-secondary-50">
                <td className="px-4 py-3 text-sm font-medium text-secondary-900">{series.document_type}</td>
                <td className="px-4 py-3 text-sm text-secondary-700">"{series.prefix}"</td>
                <td className="px-4 py-3 text-sm text-secondary-700">{series.date_format || "—"}</td>
                <td className="px-4 py-3 text-sm text-secondary-700">{series.next_number}</td>
                <td className="px-4 py-3 text-sm text-secondary-700">{series.reset_period}</td>
                <td className="px-4 py-3 text-sm text-secondary-700">{series.company_name}</td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => openEdit(series)}
                    className="mr-2 text-sm text-primary-600 hover:text-primary-800"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(series)}
                    className="text-sm text-danger-600 hover:text-danger-800"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
