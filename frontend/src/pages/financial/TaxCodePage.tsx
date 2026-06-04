import { useState, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAction } from "@/components/ui/ConfirmDialog";
import { useIsMobile } from "@/hooks/useIsMobile";
import FormPageLayout from "@/components/shared/FormPageLayout";
import AccordionSection from "@/components/shared/AccordionSection";
import api from "@/lib/api";
import {
  Plus,
  Pencil,
  Trash2,
  ArrowLeft,
  Loader2,
  X,
  BadgeCheck,
  BadgeX,
  Calendar,
  Percent,
} from "lucide-react";

// ── Types ──

interface TaxCode {
  id: string;
  code: string;
  name: string;
  rate_percent: number;
  tax_type: string;
  is_active: boolean;
  description: string;
}

interface TaxRate {
  id: string;
  tax_code_id: string;
  rate_percent: number;
  effective_from: string;
  effective_to: string | null;
  is_current: boolean;
}

interface PaginatedResponse<T> {
  count: number;
  results: T[];
}

// ── Tax Type Options ──

const TAX_TYPE_OPTIONS = [
  { value: "sales", label: "Sales Tax" },
  { value: "service", label: "Service Tax" },
  { value: "exempt", label: "Exempt" },
  { value: "zero_rated", label: "Zero-Rated" },
  { value: "out_of_scope", label: "Out of Scope" },
  { value: "purchase", label: "Purchase / Input Tax" },
];

const TAX_TYPE_BADGE: Record<string, string> = {
  sales: "bg-blue-50 text-blue-700 border-blue-200",
  service: "bg-purple-50 text-purple-700 border-purple-200",
  exempt: "bg-green-50 text-green-700 border-green-200",
  zero_rated: "bg-amber-50 text-amber-700 border-amber-200",
  out_of_scope: "bg-secondary-50 text-secondary-600 border-secondary-200",
  purchase: "bg-rose-50 text-rose-700 border-rose-200",
};

function getTaxTypeLabel(value: string): string {
  return TAX_TYPE_OPTIONS.find((o) => o.value === value)?.label || value;
}

function formatDate(dateStr: string): string {
  if (!dateStr) return "—";
  try {
    return new Intl.DateTimeFormat("en-MY", {
      year: "numeric",
      month: "short",
      day: "numeric",
    }).format(new Date(dateStr + "T00:00:00"));
  } catch {
    return dateStr;
  }
}

// ── Sub-components ──

function StatusBadge({ active }: { active: boolean }) {
  return active ? (
    <span className="inline-flex items-center gap-1 rounded-full border border-success-200 bg-success-50 px-2 py-0.5 text-xs font-medium text-success-700">
      <BadgeCheck className="h-3 w-3" />
      Active
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 rounded-full border border-secondary-200 bg-secondary-50 px-2 py-0.5 text-xs font-medium text-secondary-500">
      <BadgeX className="h-3 w-3" />
      Inactive
    </span>
  );
}

function TaxTypeBadge({ taxType }: { taxType: string }) {
  return (
    <span
      className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium capitalize ${
        TAX_TYPE_BADGE[taxType] || "bg-secondary-50 text-secondary-600 border-secondary-200"
      }`}
    >
      {getTaxTypeLabel(taxType)}
    </span>
  );
}

// ── Tax Code Form Modal ──

function TaxCodeFormModal({
  editingRecord,
  onClose,
  onDone,
}: {
  editingRecord: TaxCode | null;
  onClose: () => void;
  onDone: () => void;
}) {
  const { execute } = useAction();
  const isEditing = !!editingRecord;

  const [code, setCode] = useState(editingRecord?.code || "");
  const [name, setName] = useState(editingRecord?.name || "");
  const [ratePercent, setRatePercent] = useState(editingRecord?.rate_percent ?? 0);
  const [taxType, setTaxType] = useState(editingRecord?.tax_type || "sales");
  const [isActive, setIsActive] = useState(editingRecord?.is_active ?? true);
  const [description, setDescription] = useState(editingRecord?.description || "");

  const isValid = code.trim() && name.trim() && taxType;

  const handleSave = async () => {
    if (!isValid) return;

    const payload: Record<string, unknown> = {
      code: code.trim(),
      name: name.trim(),
      rate_percent: ratePercent,
      tax_type: taxType,
      is_active: isActive,
      description: description.trim(),
    };

    await execute({
      confirm: {
        title: isEditing ? "Update Tax Code" : "Create Tax Code",
        message: isEditing
          ? `Update tax code "${editingRecord!.code}"?`
          : `Create tax code "${code.trim()}"?`,
        variant: "info",
        confirmText: isEditing ? "Update" : "Create",
      },
      action: async () => {
        if (isEditing && editingRecord) {
          const { data } = await api.put(`/financial/tax-codes/${editingRecord.id}/`, payload);
          return data;
        }
        const { data } = await api.post("/financial/tax-codes/", payload);
        return data;
      },
      success: {
        title: isEditing ? "Tax Code Updated" : "Tax Code Created",
        message: isEditing
          ? `Tax code "${editingRecord!.code}" has been updated.`
          : `Tax code "${code.trim()}" has been created.`,
        variant: "info",
      },
      onSuccess: () => {
        onDone();
        onClose();
      },
    });
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 pt-4 pb-10"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-lg rounded-lg bg-white shadow-xl mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-4 md:p-6">
          {/* Header */}
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-secondary-900">
              {isEditing ? `Edit Tax Code ${editingRecord!.code}` : "New Tax Code"}
            </h2>
            <button
              onClick={onClose}
              className="rounded p-1 text-secondary-400 hover:text-secondary-600"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Form fields */}
          <div className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-secondary-700">
                  Code <span className="text-danger-500">*</span>
                </label>
                <input
                  type="text"
                  value={code}
                  onChange={(e) => setCode(e.target.value.toUpperCase())}
                  placeholder="e.g. SST-06"
                  className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-secondary-700">
                  Rate (%) <span className="text-danger-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={ratePercent}
                  onChange={(e) => setRatePercent(parseFloat(e.target.value) || 0)}
                  className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-secondary-700">
                Name <span className="text-danger-500">*</span>
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Service Tax 6%"
                className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-secondary-700">
                Tax Type <span className="text-danger-500">*</span>
              </label>
              <select
                value={taxType}
                onChange={(e) => setTaxType(e.target.value)}
                className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              >
                {TAX_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                  className="h-4 w-4 rounded border-secondary-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm font-medium text-secondary-700">Active</span>
              </label>
            </div>

            <div>
              <label className="block text-sm font-medium text-secondary-700">Description</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional description..."
                rows={3}
                className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              />
            </div>
          </div>

          {/* Footer */}
          <div className="mt-6 flex items-center justify-end gap-3 border-t border-secondary-200 pt-4">
            <button
              onClick={onClose}
              className="rounded-lg border border-secondary-300 px-4 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={!isValid}
              className="rounded-lg bg-primary-600 px-6 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            >
              {isEditing ? "Update" : "Create"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Tax Rate Form Modal ──

function TaxRateFormModal({
  taxCodeId,
  onClose,
  onDone,
}: {
  taxCodeId: string;
  onClose: () => void;
  onDone: () => void;
}) {
  const { execute } = useAction();

  const [ratePercent, setRatePercent] = useState(0);
  const [effectiveFrom, setEffectiveFrom] = useState(() =>
    new Date().toISOString().split("T")[0]
  );
  const [effectiveTo, setEffectiveTo] = useState("");

  const isValid = ratePercent > 0 && effectiveFrom;

  const handleSave = async () => {
    if (!isValid) return;

    const payload: Record<string, unknown> = {
      tax_code_id: taxCodeId,
      rate_percent: ratePercent,
      effective_from: effectiveFrom,
      effective_to: effectiveTo || null,
    };

    await execute({
      confirm: {
        title: "Add Tax Rate",
        message: `Add rate of ${ratePercent}% effective ${formatDate(effectiveFrom)}?`,
        variant: "info",
        confirmText: "Add Rate",
      },
      action: async () => {
        const { data } = await api.post("/financial/tax-rates/", payload);
        return data;
      },
      success: {
        title: "Tax Rate Added",
        message: `Rate of ${ratePercent}% has been added.`,
        variant: "info",
      },
      onSuccess: () => {
        onDone();
        onClose();
      },
    });
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 pt-4 pb-10"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-md rounded-lg bg-white shadow-xl mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-4 md:p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-secondary-900">Add Tax Rate</h2>
            <button
              onClick={onClose}
              className="rounded p-1 text-secondary-400 hover:text-secondary-600"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-secondary-700">
                Rate (%) <span className="text-danger-500">*</span>
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={ratePercent}
                onChange={(e) => setRatePercent(parseFloat(e.target.value) || 0)}
                className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary-700">
                Effective From <span className="text-danger-500">*</span>
              </label>
              <input
                type="date"
                value={effectiveFrom}
                onChange={(e) => setEffectiveFrom(e.target.value)}
                className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary-700">Effective To</label>
              <input
                type="date"
                value={effectiveTo}
                onChange={(e) => setEffectiveTo(e.target.value)}
                className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              />
              <p className="mt-1 text-xs text-secondary-400">Leave blank if currently effective.</p>
            </div>
          </div>

          <div className="mt-6 flex items-center justify-end gap-3 border-t border-secondary-200 pt-4">
            <button
              onClick={onClose}
              className="rounded-lg border border-secondary-300 px-4 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={!isValid}
              className="rounded-lg bg-primary-600 px-6 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            >
              Add Rate
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Main Page Component ──

export default function TaxCodePage() {
  const queryClient = useQueryClient();
  const { execute } = useAction();
  const isMobile = useIsMobile();

  // ── State ──
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showMobileDetail, setShowMobileDetail] = useState(false);
  const [showFormModal, setShowFormModal] = useState(false);
  const [editingRecord, setEditingRecord] = useState<TaxCode | null>(null);
  const [showRateForm, setShowRateForm] = useState(false);

  // ── Fetch tax codes ──
  const {
    data: listResponse,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["tax-codes"],
    queryFn: async (): Promise<PaginatedResponse<TaxCode>> => {
      const { data } = await api.get("/financial/tax-codes/");
      return data;
    },
    staleTime: 10_000,
  });

  const records = listResponse?.results || [];

  // ── Fetch selected tax code detail (for detail view) ──
  const { data: selectedCode, isLoading: detailLoading } = useQuery({
    queryKey: ["tax-code", selectedId],
    queryFn: async (): Promise<TaxCode> => {
      // Use list data directly since there's no single endpoint
      const found = records.find((r) => r.id === selectedId);
      if (found) return found;
      const { data } = await api.get("/financial/tax-codes/");
      const all: TaxCode[] = data.results || data || [];
      return all.find((r) => r.id === selectedId) as TaxCode;
    },
    enabled: !!selectedId,
    staleTime: 10_000,
  });

  // ── Fetch tax rates for selected code ──
  const { data: taxRatesData, isLoading: ratesLoading } = useQuery({
    queryKey: ["tax-rates", selectedId],
    queryFn: async (): Promise<TaxRate[]> => {
      const { data } = await api.get("/financial/tax-rates/", {
        params: { tax_code_id: selectedId },
      });
      return data.results || data || [];
    },
    enabled: !!selectedId,
    staleTime: 10_000,
  });

  const taxRates = taxRatesData || [];

  // ── Helpers ──

  const refresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["tax-codes"] });
    if (selectedId) {
      queryClient.invalidateQueries({ queryKey: ["tax-rates", selectedId] });
    }
  }, [queryClient, selectedId]);

  // ── Handlers ──

  const handleSelect = useCallback(
    (code: TaxCode) => {
      setSelectedId(code.id);
      if (isMobile) setShowMobileDetail(true);
    },
    [isMobile]
  );

  const handleBackToList = useCallback(() => {
    setSelectedId(null);
    setShowMobileDetail(false);
  }, []);

  const handleCreateOpen = useCallback(() => {
    setEditingRecord(null);
    setShowFormModal(true);
  }, []);

  const handleEditOpen = useCallback(() => {
    if (selectedCode) {
      setEditingRecord(selectedCode);
      setShowFormModal(true);
    }
  }, [selectedCode]);

  const handleFormDone = useCallback(() => {
    refresh();
    if (selectedId) {
      queryClient.invalidateQueries({ queryKey: ["tax-code", selectedId] });
    }
  }, [refresh, queryClient, selectedId]);

  const handleDelete = useCallback(
    async (code: TaxCode) => {
      await execute({
        confirm: {
          title: "Delete Tax Code",
          message: `Delete tax code "${code.code}"? This action cannot be undone.`,
          variant: "danger",
          confirmText: "Delete",
        },
        action: async () => {
          await api.delete(`/financial/tax-codes/${code.id}/`);
        },
        success: {
          title: "Tax Code Deleted",
          message: `"${code.code}" has been deleted.`,
          variant: "info",
        },
        onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: ["tax-codes"] });
          if (selectedId === code.id) {
            setSelectedId(null);
            setShowMobileDetail(false);
          }
        },
      });
    },
    [execute, queryClient, selectedId]
  );

  const handleRateAdded = useCallback(() => {
    if (selectedId) {
      queryClient.invalidateQueries({ queryKey: ["tax-rates", selectedId] });
    }
  }, [queryClient, selectedId]);

  // ── Render: List Table (Desktop) ──

  const renderListTable = () => {
    if (isLoading) {
      return (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-primary-500" />
        </div>
      );
    }

    if (error) {
      return (
        <div className="rounded-lg bg-danger-50 p-4 text-sm text-danger-700">
          Failed to load tax codes. Please try again.
        </div>
      );
    }

    if (records.length === 0) {
      return (
        <div className="rounded-lg bg-secondary-50 p-8 text-center">
          <Percent className="mx-auto h-8 w-8 text-secondary-300" />
          <p className="mt-2 text-sm text-secondary-500">
            No tax codes yet. Create one to get started.
          </p>
        </div>
      );
    }

    return (
      <div className="overflow-x-auto rounded-lg border border-secondary-200">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="bg-secondary-50 text-left text-xs font-medium uppercase text-secondary-500">
              <th className="px-4 py-3">Code</th>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3 text-right">Rate</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-secondary-100">
            {records.map((code) => (
              <tr
                key={code.id}
                onClick={() => handleSelect(code)}
                className={`cursor-pointer transition-colors ${
                  selectedId === code.id
                    ? "bg-primary-50"
                    : "hover:bg-secondary-50"
                }`}
              >
                <td className="px-4 py-3 font-mono text-sm font-medium text-secondary-900">
                  {code.code}
                </td>
                <td className="px-4 py-3 text-secondary-600">{code.name}</td>
                <td className="px-4 py-3 text-right font-mono text-secondary-900">
                  {code.rate_percent}%
                </td>
                <td className="px-4 py-3">
                  <TaxTypeBadge taxType={code.tax_type} />
                </td>
                <td className="px-4 py-3">
                  <StatusBadge active={code.is_active} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  // ── Render: List Cards (Mobile) ──

  const renderMobileCards = () => {
    if (isLoading) {
      return (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-primary-500" />
        </div>
      );
    }

    if (error) {
      return (
        <div className="rounded-lg bg-danger-50 p-4 text-sm text-danger-700">
          Failed to load tax codes.
        </div>
      );
    }

    if (records.length === 0) {
      return (
        <div className="rounded-lg bg-secondary-50 p-8 text-center">
          <Percent className="mx-auto h-8 w-8 text-secondary-300" />
          <p className="mt-2 text-sm text-secondary-500">No tax codes yet.</p>
        </div>
      );
    }

    return (
      <div className="space-y-2">
        {records.map((code) => (
          <div
            key={code.id}
            onClick={() => handleSelect(code)}
            className="cursor-pointer rounded-lg border border-secondary-200 bg-white p-3"
          >
            <div className="flex items-center justify-between">
              <span className="font-mono text-sm font-medium text-secondary-900">
                {code.code}
              </span>
              <StatusBadge active={code.is_active} />
            </div>
            <div className="mt-1 text-sm text-secondary-600">{code.name}</div>
            <div className="mt-1 flex items-center gap-2 text-xs text-secondary-400">
              <span>{code.rate_percent}%</span>
              <span className="text-secondary-300">|</span>
              <TaxTypeBadge taxType={code.tax_type} />
            </div>
          </div>
        ))}
      </div>
    );
  };

  // ── Render: Detail View ──

  const renderDetail = () => {
    if (!selectedCode) {
      return (
        <div className="flex h-48 items-center justify-center">
          <div className="text-center">
            <Percent className="mx-auto h-10 w-10 text-secondary-200" />
            <p className="mt-2 text-sm text-secondary-500">
              Select a tax code to view details
            </p>
          </div>
        </div>
      );
    }

    if (detailLoading) {
      return (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-primary-500" />
        </div>
      );
    }

    const code = selectedCode;

    return (
      <div className="space-y-4">
        {/* Action buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleEditOpen}
            className="inline-flex items-center gap-1.5 rounded-lg border border-secondary-300 px-3 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-50"
          >
            <Pencil className="h-4 w-4" />
            <span className="hidden sm:inline">Edit</span>
          </button>
          <button
            onClick={() => handleDelete(code)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-danger-300 px-3 py-2 text-sm font-medium text-danger-600 hover:bg-danger-50"
          >
            <Trash2 className="h-4 w-4" />
            <span className="hidden sm:inline">Delete</span>
          </button>
        </div>

        {/* Tax Code Details */}
        <AccordionSection
          title="Tax Code Details"
          isOpen={true}
          onToggle={() => {}}
        >
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <span className="text-xs font-medium uppercase tracking-wider text-secondary-500">
                Code
              </span>
              <p className="mt-1 font-mono text-sm font-medium text-secondary-900">{code.code}</p>
            </div>
            <div>
              <span className="text-xs font-medium uppercase tracking-wider text-secondary-500">
                Name
              </span>
              <p className="mt-1 text-sm text-secondary-900">{code.name}</p>
            </div>
            <div>
              <span className="text-xs font-medium uppercase tracking-wider text-secondary-500">
                Rate
              </span>
              <p className="mt-1 text-sm font-mono text-secondary-900">{code.rate_percent}%</p>
            </div>
            <div>
              <span className="text-xs font-medium uppercase tracking-wider text-secondary-500">
                Tax Type
              </span>
              <div className="mt-1">
                <TaxTypeBadge taxType={code.tax_type} />
              </div>
            </div>
            <div>
              <span className="text-xs font-medium uppercase tracking-wider text-secondary-500">
                Status
              </span>
              <div className="mt-1">
                <StatusBadge active={code.is_active} />
              </div>
            </div>
          </div>
          {code.description && (
            <div className="mt-3">
              <span className="text-xs font-medium uppercase tracking-wider text-secondary-500">
                Description
              </span>
              <p className="mt-1 text-sm text-secondary-900">{code.description}</p>
            </div>
          )}
        </AccordionSection>

        {/* Rate History */}
        <AccordionSection
          title={`Rate History (${taxRates.length})`}
          isOpen={true}
          onToggle={() => {}}
        >
          {ratesLoading ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-5 w-5 animate-spin text-primary-500" />
            </div>
          ) : taxRates.length === 0 ? (
            <div className="py-4 text-center text-sm text-secondary-400">
              No rate history yet.
            </div>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-secondary-200">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="bg-secondary-50 text-left text-xs font-medium uppercase text-secondary-500">
                    <th className="px-3 py-2">Rate</th>
                    <th className="px-3 py-2">Effective From</th>
                    <th className="px-3 py-2">Effective To</th>
                    <th className="px-3 py-2">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-secondary-100">
                  {taxRates.map((rate) => (
                    <tr key={rate.id}>
                      <td className="px-3 py-2 font-mono font-medium text-secondary-900">
                        {rate.rate_percent}%
                      </td>
                      <td className="px-3 py-2 text-secondary-600">
                        <span className="inline-flex items-center gap-1">
                          <Calendar className="h-3 w-3 text-secondary-400" />
                          {formatDate(rate.effective_from)}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-secondary-600">
                        {rate.effective_to ? (
                          <span className="inline-flex items-center gap-1">
                            <Calendar className="h-3 w-3 text-secondary-400" />
                            {formatDate(rate.effective_to)}
                          </span>
                        ) : (
                          <span className="text-secondary-400">—</span>
                        )}
                      </td>
                      <td className="px-3 py-2">
                        {rate.is_current ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-success-50 px-2 py-0.5 text-xs font-medium text-success-700">
                            <BadgeCheck className="h-3 w-3" />
                            Current
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 rounded-full bg-secondary-50 px-2 py-0.5 text-xs font-medium text-secondary-500">
                            Historic
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="mt-3">
            <button
              onClick={() => setShowRateForm(true)}
              className="inline-flex items-center gap-1 text-sm font-medium text-primary-600 hover:text-primary-700"
            >
              <Plus className="h-3.5 w-3.5" /> Add Rate
            </button>
          </div>
        </AccordionSection>

        {/* Tax Rate Form Modal */}
        {showRateForm && selectedCode && (
          <TaxRateFormModal
            taxCodeId={selectedCode.id}
            onClose={() => setShowRateForm(false)}
            onDone={handleRateAdded}
          />
        )}
      </div>
    );
  };

  const renderList = () => (
    <div className="space-y-4">
      {renderListTable()}
    </div>
  );

  // ── Render: Main Layout ──

  // Mobile: list view
  if (isMobile && !showMobileDetail) {
    return (
      <div className="p-4">
        <div className="mb-4 flex items-center justify-between">
          <h1 className="text-lg font-bold text-secondary-900">Tax Codes</h1>
          <button
            onClick={handleCreateOpen}
            className="inline-flex items-center justify-center rounded-lg bg-primary-600 p-2 text-white hover:bg-primary-700"
          >
            <Plus className="h-5 w-5" />
          </button>
        </div>
        {renderMobileCards()}

        {/* Form Modal */}
        {showFormModal && (
          <TaxCodeFormModal
            editingRecord={editingRecord}
            onClose={() => {
              setShowFormModal(false);
              setEditingRecord(null);
            }}
            onDone={handleFormDone}
          />
        )}
      </div>
    );
  }

  // Mobile: detail view
  if (isMobile && showMobileDetail) {
    return (
      <div className="p-4">
        <button
          onClick={handleBackToList}
          className="mb-3 flex items-center gap-1 text-sm text-secondary-500 hover:text-secondary-900"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Tax Codes
        </button>
        {renderDetail()}

        {/* Form Modal */}
        {showFormModal && (
          <TaxCodeFormModal
            editingRecord={editingRecord}
            onClose={() => {
              setShowFormModal(false);
              setEditingRecord(null);
            }}
            onDone={handleFormDone}
          />
        )}
      </div>
    );
  }

  // Desktop: split pane
  return (
    <div className="p-4 md:p-6 h-[calc(100vh-4rem)]">
      <FormPageLayout
        leftPanel={{
          id: "list",
          label: "Tax Codes",
          content: (
            <div>
              <div className="mb-4 flex items-center justify-between">
                <h1 className="text-xl font-bold text-secondary-900">Tax Codes</h1>
                <button
                  onClick={handleCreateOpen}
                  className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
                >
                  + New Tax Code
                </button>
              </div>
              {renderList()}
            </div>
          ),
        }}
        rightPanel={{
          id: "detail",
          label: "Details",
          content: renderDetail(),
        }}
      />

      {/* Form Modal (shared for both mobile and desktop) */}
      {showFormModal && (
        <TaxCodeFormModal
          editingRecord={editingRecord}
          onClose={() => {
            setShowFormModal(false);
            setEditingRecord(null);
          }}
          onDone={handleFormDone}
        />
      )}
    </div>
  );
}
