import { useState, useEffect, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAction } from "@/components/ui/ConfirmDialog";
import { useIsMobile } from "@/hooks/useIsMobile";
import { useDebounce } from "@/hooks/useDebounce";
import FormPageLayout from "@/components/shared/FormPageLayout";
import AccordionSection from "@/components/shared/AccordionSection";
import api from "@/lib/api";
import {
  Plus,
  Pencil,
  Trash2,
  ArrowLeft,
  Search,
  Loader2,
  X,
  CheckCircle,
  RotateCcw,

  FileText,
  AlertTriangle,
} from "lucide-react";

// ── Types ──

interface Account {
  id: string;
  code: string;
  name: string;
  account_type: string;
}

interface JournalLine {
  id?: string;
  account_id: string;
  account_code?: string;
  account_name?: string;
  debit: number;
  credit: number;
  description: string;
}

interface JournalEntry {
  id: string;
  entry_number: string;
  date: string;
  description: string;
  reference: string;
  status: "draft" | "posted" | "reversed";
  total_debit: number;
  total_credit: number;
  created_by?: { id: string; name: string };
  lines: JournalLine[];
  updated_at?: string;
  reversal_entry_id?: string;
  reversed_entry_id?: string;
}

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

interface FormLineItem {
  _key: string;
  account_id: string;
  debit: number;
  credit: number;
  description: string;
}

// ── Status Badge Colors ──

const STATUS_BADGE: Record<string, string> = {
  draft: "bg-amber-50 text-amber-700 border-amber-200",
  posted: "bg-green-50 text-green-700 border-green-200",
  reversed: "bg-red-50 text-red-700 border-red-200",
};

const STATUS_LABEL: Record<string, string> = {
  draft: "Draft",
  posted: "Posted",
  reversed: "Reversed",
};

// ── Helpers ──

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-MY", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
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

let keyCounter = 0;
function makeLineKey(): string {
  keyCounter += 1;
  return `line_${keyCounter}_${Date.now()}`;
}

// ── Status Badge ──

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium capitalize ${
        STATUS_BADGE[status] || "bg-secondary-50 text-secondary-600 border-secondary-200"
      }`}
    >
      {STATUS_LABEL[status] || status}
    </span>
  );
}

// ── Line Items Table (read-only, used in detail view) ──

function LineItemsReadonlyTable({ lines }: { lines: JournalLine[] }) {
  const totalDebit = lines.reduce((s, l) => s + (l.debit || 0), 0);
  const totalCredit = lines.reduce((s, l) => s + (l.credit || 0), 0);
  const isBalanced = Math.abs(totalDebit - totalCredit) < 0.01;

  return (
    <div className="overflow-x-auto rounded-lg border border-secondary-200">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="bg-secondary-50 text-left text-xs font-medium uppercase text-secondary-500">
            <th className="px-4 py-2.5">Account</th>
            <th className="px-4 py-2.5 text-right">Debit (RM)</th>
            <th className="px-4 py-2.5 text-right">Credit (RM)</th>
            <th className="px-4 py-2.5">Description</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-secondary-100">
          {lines.length === 0 ? (
            <tr>
              <td colSpan={4} className="px-4 py-8 text-center text-secondary-400">
                No line items
              </td>
            </tr>
          ) : (
            lines.map((line, idx) => (
              <tr key={line.id || idx} className="hover:bg-secondary-50">
                <td className="px-4 py-2">
                  {line.account_code && line.account_name ? (
                    <span>
                      <span className="font-mono text-xs text-secondary-500">{line.account_code}</span>{" "}
                      <span className="text-secondary-900">{line.account_name}</span>
                    </span>
                  ) : (
                    <span className="text-secondary-400">—</span>
                  )}
                </td>
                <td className="px-4 py-2 text-right font-mono text-secondary-900">
                  {line.debit > 0 ? formatCurrency(line.debit) : "—"}
                </td>
                <td className="px-4 py-2 text-right font-mono text-secondary-900">
                  {line.credit > 0 ? formatCurrency(line.credit) : "—"}
                </td>
                <td className="px-4 py-2 text-secondary-600">{line.description || "—"}</td>
              </tr>
            ))
          )}
        </tbody>
        <tfoot>
          <tr className={`border-t-2 font-medium ${isBalanced ? "border-secondary-300" : "border-danger-400"}`}>
            <td className="px-4 py-2.5 text-xs font-semibold uppercase text-secondary-600">
              {isBalanced ? "Balanced" : "NOT Balanced"}
            </td>
            <td className="px-4 py-2.5 text-right font-mono text-secondary-900">
              {formatCurrency(totalDebit)}
            </td>
            <td className="px-4 py-2.5 text-right font-mono text-secondary-900">
              {formatCurrency(totalCredit)}
            </td>
            <td className="px-4 py-2.5" />
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

// ── Line Items Editor (used in create/edit form modal) ──

function LineItemsEditor({
  lines,
  accounts,
  onChange,
}: {
  lines: FormLineItem[];
  accounts: Account[];
  onChange: (lines: FormLineItem[]) => void;
}) {
  const totalDebit = lines.reduce((s, l) => s + (l.debit || 0), 0);
  const totalCredit = lines.reduce((s, l) => s + (l.credit || 0), 0);
  const isBalanced = Math.abs(totalDebit - totalCredit) < 0.01;

  const updateLine = (key: string, field: keyof FormLineItem, value: string | number) => {
    onChange(
      lines.map((l) => (l._key === key ? { ...l, [field]: value } : l))
    );
  };

  const removeLine = (key: string) => {
    if (lines.length <= 1) return;
    onChange(lines.filter((l) => l._key !== key));
  };

  const addLine = () => {
    onChange([...lines, { _key: makeLineKey(), account_id: "", debit: 0, credit: 0, description: "" }]);
  };

  return (
    <div>
      <div className="overflow-x-auto rounded-lg border border-secondary-200">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="bg-secondary-50 text-left text-xs font-medium uppercase text-secondary-500">
              <th className="px-3 py-2">Account</th>
              <th className="px-3 py-2 text-right">Debit (RM)</th>
              <th className="px-3 py-2 text-right">Credit (RM)</th>
              <th className="px-3 py-2">Description</th>
              <th className="w-10 px-3 py-2" />
            </tr>
          </thead>
          <tbody className="divide-y divide-secondary-100">
            {lines.map((line) => (
              <tr key={line._key} className="hover:bg-secondary-50">
                <td className="px-3 py-1.5">
                  <select
                    value={line.account_id}
                    onChange={(e) => updateLine(line._key, "account_id", e.target.value)}
                    className="w-full rounded-lg border border-secondary-300 px-2 py-1.5 text-sm focus:border-primary-500 focus:outline-none"
                  >
                    <option value="">— Select —</option>
                    {accounts.map((acc) => (
                      <option key={acc.id} value={acc.id}>
                        {acc.code} — {acc.name}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="px-3 py-1.5">
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={line.debit || ""}
                    onChange={(e) =>
                      updateLine(line._key, "debit", parseFloat(e.target.value) || 0)
                    }
                    className="w-full rounded-lg border border-secondary-300 px-2 py-1.5 text-right text-sm focus:border-primary-500 focus:outline-none"
                    placeholder="0.00"
                  />
                </td>
                <td className="px-3 py-1.5">
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={line.credit || ""}
                    onChange={(e) =>
                      updateLine(line._key, "credit", parseFloat(e.target.value) || 0)
                    }
                    className="w-full rounded-lg border border-secondary-300 px-2 py-1.5 text-right text-sm focus:border-primary-500 focus:outline-none"
                    placeholder="0.00"
                  />
                </td>
                <td className="px-3 py-1.5">
                  <input
                    type="text"
                    value={line.description}
                    onChange={(e) => updateLine(line._key, "description", e.target.value)}
                    className="w-full rounded-lg border border-secondary-300 px-2 py-1.5 text-sm focus:border-primary-500 focus:outline-none"
                    placeholder="Line description..."
                  />
                </td>
                <td className="px-3 py-1.5">
                  <button
                    type="button"
                    onClick={() => removeLine(line._key)}
                    disabled={lines.length <= 1}
                    className="rounded p-1 text-secondary-400 hover:bg-danger-50 hover:text-danger-600 disabled:opacity-30 disabled:cursor-not-allowed"
                    title="Remove line"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr
              className={`border-t-2 font-medium ${
                isBalanced ? "border-secondary-300" : "border-danger-400"
              }`}
            >
              <td className="px-3 py-2 text-xs font-semibold uppercase text-secondary-600">
                {isBalanced ? "✓ Balanced" : "✗ NOT Balanced"}
              </td>
              <td className="px-3 py-2 text-right font-mono text-secondary-900">
                {formatCurrency(totalDebit)}
              </td>
              <td className="px-3 py-2 text-right font-mono text-secondary-900">
                {formatCurrency(totalCredit)}
              </td>
              <td colSpan={2} className="px-3 py-2" />
            </tr>
          </tfoot>
        </table>
      </div>
      <button
        type="button"
        onClick={addLine}
        className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-primary-600 hover:text-primary-700"
      >
        <Plus className="h-3.5 w-3.5" /> Add Line
      </button>
    </div>
  );
}

// ── Journal Entry Form Modal (Create/Edit) ──

function JournalEntryFormModal({
  editingEntry,
  onClose,
  onDone,
}: {
  editingEntry: JournalEntry | null;
  onClose: () => void;
  onDone: () => void;
}) {
  const { execute } = useAction();
  const isEditing = !!editingEntry;

  // Fetch accounts for dropdown
  const { data: accountsData } = useQuery({
    queryKey: ["financial-accounts-list"],
    queryFn: async (): Promise<Account[]> => {
      const { data } = await api.get("/financial/accounts/", {
        params: { page_size: 1000 },
      });
      return data.results || data || [];
    },
    staleTime: 60_000,
  });
  const accounts = accountsData || [];

  // Form state
  const [date, setDate] = useState(() => {
    if (editingEntry?.date) return editingEntry.date;
    return new Date().toISOString().split("T")[0];
  });
  const [description, setDescription] = useState(editingEntry?.description || "");
  const [reference, setReference] = useState(editingEntry?.reference || "");
  const [lines, setLines] = useState<FormLineItem[]>(() => {
    if (editingEntry?.lines && editingEntry.lines.length > 0) {
      return editingEntry.lines.map((l) => ({
        _key: makeLineKey(),
        account_id: l.account_id,
        debit: l.debit,
        credit: l.credit,
        description: l.description,
      }));
    }
    return [{ _key: makeLineKey(), account_id: "", debit: 0, credit: 0, description: "" }];
  });
  const [saving, setSaving] = useState(false);

  const totalDebit = lines.reduce((s, l) => s + (l.debit || 0), 0);
  const totalCredit = lines.reduce((s, l) => s + (l.credit || 0), 0);
  const isBalanced = Math.abs(totalDebit - totalCredit) < 0.01;
  const isValid =
    date &&
    description.trim() &&
    lines.some((l) => l.account_id && ((l.debit || 0) > 0 || (l.credit || 0) > 0)) &&
    isBalanced;

  const handleSave = async () => {
    if (!isValid) return;
    setSaving(true);

    const payload: Record<string, unknown> = {
      date,
      description: description.trim(),
      reference: reference.trim(),
      lines: lines.map((l) => ({
        account_id: l.account_id,
        debit: l.debit || 0,
        credit: l.credit || 0,
        description: l.description.trim(),
      })),
    };

    if (isEditing && editingEntry?.updated_at) {
      payload.updated_at = editingEntry.updated_at;
    }

    const result = await execute({
      confirm: {
        title: isEditing ? "Update Journal Entry" : "Create Journal Entry",
        message: isEditing
          ? `Update journal entry "${editingEntry!.entry_number}"?`
          : `Create journal entry dated ${formatDate(date)}?`,
        variant: "info",
        confirmText: isEditing ? "Update" : "Create",
      },
      action: async () => {
        if (isEditing && editingEntry) {
          const { data } = await api.put(
            `/financial/journal-entries/${editingEntry.id}/`,
            payload
          );
          return data;
        }
        const { data } = await api.post("/financial/journal-entries/", payload);
        return data;
      },
      success: {
        title: isEditing ? "Journal Entry Updated" : "Journal Entry Created",
        message: isEditing
          ? `Entry "${editingEntry!.entry_number}" has been updated.`
          : "New journal entry has been created as draft.",
        variant: "info",
      },
      onSuccess: () => {
        setSaving(false);
        onDone();
        onClose();
      },
    });
    if (!result) {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 pt-4 pb-10"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-3xl rounded-lg bg-white shadow-xl mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-4 md:p-6">
          {/* Header */}
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-secondary-900">
              {isEditing ? `Edit Journal Entry ${editingEntry!.entry_number}` : "New Journal Entry"}
            </h2>
            <button
              onClick={onClose}
              className="rounded p-1 text-secondary-400 hover:text-secondary-600"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="space-y-4">
            {/* Date + Description + Reference */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div>
                <label className="block text-sm font-medium text-secondary-700">
                  Date <span className="text-danger-500">*</span>
                </label>
                <input
                  type="date"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-secondary-700">Reference</label>
                <input
                  type="text"
                  value={reference}
                  onChange={(e) => setReference(e.target.value)}
                  placeholder="e.g. INV-001"
                  className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-secondary-700">
                Description <span className="text-danger-500">*</span>
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe the journal entry..."
                rows={2}
                className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
                required
              />
            </div>

            {/* Line Items */}
            <div>
              <label className="mb-1.5 block text-sm font-medium text-secondary-700">
                Line Items <span className="text-danger-500">*</span>
              </label>
              <LineItemsEditor
                lines={lines}
                accounts={accounts}
                onChange={setLines}
              />
            </div>
          </div>

          {/* Footer */}
          <div className="mt-6 flex items-center justify-between border-t border-secondary-200 pt-4">
            {!isBalanced && lines.some((l) => l.account_id) && (
              <p className="flex items-center gap-1 text-sm text-danger-600">
                <AlertTriangle className="h-4 w-4" />
                Debits and credits must be equal
              </p>
            )}
            {isBalanced && isBalanced !== null && (
              <p className="text-sm text-success-600">Entry is balanced</p>
            )}
            {!isBalanced && (
              <span /> // spacer
            )}
            <div className="flex items-center gap-3">
              <button
                onClick={onClose}
                className="rounded-lg border border-secondary-300 px-4 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={!isValid || saving}
                className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-6 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
              >
                {saving ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Saving...
                  </>
                ) : isEditing ? (
                  "Update Entry"
                ) : (
                  "Create Draft"
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Main Page Component ──

export default function JournalEntryPage() {
  const queryClient = useQueryClient();
  const { execute } = useAction();
  const isMobile = useIsMobile();

  // ── State ──
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showMobileDetail, setShowMobileDetail] = useState(false);
  const [showFormModal, setShowFormModal] = useState(false);
  const [editingEntry, setEditingEntry] = useState<JournalEntry | null>(null);
  const pageSize = 20;

  const debouncedSearch = useDebounce(search, 300);

  // ── Fetch journal entries (paginated) ──
  const {
    data: listResponse,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["journal-entries", debouncedSearch, statusFilter, page],
    queryFn: async (): Promise<PaginatedResponse<JournalEntry>> => {
      const params: Record<string, string | number> = {
        page,
        page_size: pageSize,
      };
      if (debouncedSearch) params.search = debouncedSearch;
      if (statusFilter) params.status = statusFilter;
      const { data } = await api.get("/financial/journal-entries/", { params });
      return data;
    },
    staleTime: 10_000,
  });

  const records = listResponse?.results || [];
  const totalCount = listResponse?.count || 0;
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

  // ── Fetch selected entry detail (for right panel / mobile detail) ──
  const { data: selectedEntry, isLoading: detailLoading } = useQuery({
    queryKey: ["journal-entry", selectedId],
    queryFn: async (): Promise<JournalEntry> => {
      const { data } = await api.get(`/financial/journal-entries/${selectedId}/`);
      return data;
    },
    enabled: !!selectedId,
    staleTime: 10_000,
  });

  // Reset page when search/filter changes
  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, statusFilter]);

  // Clear selection when records change
  useEffect(() => {
    if (selectedId && records.length > 0) {
      const stillExists = records.some((r) => r.id === selectedId);
      if (!stillExists) {
        setSelectedId(null);
        setShowMobileDetail(false);
      }
    }
  }, [records, selectedId]);

  // ── Helpers ──

  const refresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["journal-entries"] });
    if (selectedId) {
      queryClient.invalidateQueries({ queryKey: ["journal-entry", selectedId] });
    }
  }, [queryClient, selectedId]);

  // ── Handlers ──

  const handleSelect = useCallback(
    (entry: JournalEntry) => {
      setSelectedId(entry.id);
      if (isMobile) setShowMobileDetail(true);
    },
    [isMobile]
  );

  const handleBackToList = useCallback(() => {
    setSelectedId(null);
    setShowMobileDetail(false);
  }, []);

  const handleCreateOpen = useCallback(() => {
    setEditingEntry(null);
    setShowFormModal(true);
  }, []);

  const handleEditOpen = useCallback(() => {
    if (selectedEntry) {
      setEditingEntry(selectedEntry);
      setShowFormModal(true);
    }
  }, [selectedEntry]);

  const handleFormDone = useCallback(() => {
    refetch();
    if (selectedId) {
      queryClient.invalidateQueries({ queryKey: ["journal-entry", selectedId] });
    }
  }, [refetch, queryClient, selectedId]);

  const handleDelete = useCallback(
    async (entry: JournalEntry) => {
      await execute({
        confirm: {
          title: "Delete Journal Entry",
          message: `Delete "${entry.entry_number}"? This action cannot be undone.`,
          variant: "danger",
          confirmText: "Delete",
        },
        action: async () => {
          await api.delete(`/financial/journal-entries/${entry.id}/`);
        },
        success: {
          title: "Journal Entry Deleted",
          message: `"${entry.entry_number}" has been deleted.`,
          variant: "info",
        },
        onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: ["journal-entries"] });
          if (selectedId === entry.id) {
            setSelectedId(null);
            setShowMobileDetail(false);
          }
        },
      });
    },
    [execute, queryClient, selectedId]
  );

  const handlePost = useCallback(
    async (entry: JournalEntry) => {
      await execute({
        confirm: {
          title: "Post Journal Entry",
          message: `Post "${entry.entry_number}" to the General Ledger? This action cannot be reversed.`,
          variant: "warning",
          confirmText: "Post",
        },
        action: async () => {
          const { data } = await api.post(
            `/financial/journal-entries/${entry.id}/post/`
          );
          return data;
        },
        success: {
          title: "Journal Entry Posted",
          message: `"${entry.entry_number}" has been posted to the General Ledger.`,
          variant: "info",
        },
        onSuccess: () => {
          refresh();
        },
      });
    },
    [execute, refresh]
  );

  const handleReverse = useCallback(
    async (entry: JournalEntry) => {
      await execute({
        confirm: {
          title: "Reverse Journal Entry",
          message: `Reverse "${entry.entry_number}"? A reversing entry will be created with opposite debits/credits.`,
          variant: "warning",
          confirmText: "Reverse",
        },
        action: async () => {
          const { data } = await api.post(
            `/financial/journal-entries/${entry.id}/reverse/`
          );
          return data;
        },
        success: {
          title: "Journal Entry Reversed",
          message: `"${entry.entry_number}" has been reversed. A reversing entry was created.`,
          variant: "info",
        },
        onSuccess: () => {
          refresh();
        },
      });
    },
    [execute, refresh]
  );

  // ── Render: List View ──

  const renderSearchAndFilter = () => (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-secondary-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by entry number or description..."
          className="w-full rounded-lg border border-secondary-300 pl-9 pr-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
        />
        {search && (
          <button
            onClick={() => setSearch("")}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-secondary-400 hover:text-secondary-600"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
      <select
        value={statusFilter}
        onChange={(e) => setStatusFilter(e.target.value)}
        className="w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none sm:w-40"
      >
        <option value="">All Statuses</option>
        <option value="draft">Draft</option>
        <option value="posted">Posted</option>
        <option value="reversed">Reversed</option>
      </select>
    </div>
  );

  const renderPagination = () => {
    if (totalCount <= pageSize) return null;
    return (
      <div className="flex items-center justify-between pt-3 text-sm">
        <span className="text-secondary-500">
          {totalCount} total entries
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="rounded-lg border border-secondary-300 px-3 py-1.5 text-sm font-medium text-secondary-700 hover:bg-secondary-50 disabled:opacity-50"
          >
            Previous
          </button>
          <span className="text-secondary-600">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="rounded-lg border border-secondary-300 px-3 py-1.5 text-sm font-medium text-secondary-700 hover:bg-secondary-50 disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </div>
    );
  };

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
          Failed to load journal entries. Please try again.
        </div>
      );
    }

    if (records.length === 0) {
      return (
        <div className="rounded-lg bg-secondary-50 p-8 text-center">
          <FileText className="mx-auto h-8 w-8 text-secondary-300" />
          <p className="mt-2 text-sm text-secondary-500">
            {debouncedSearch || statusFilter
              ? "No journal entries match your filters."
              : "No journal entries yet. Create one to get started."}
          </p>
        </div>
      );
    }

    return (
      <>
        <div className="overflow-x-auto rounded-lg border border-secondary-200">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="bg-secondary-50 text-left text-xs font-medium uppercase text-secondary-500">
                <th className="px-4 py-3">Entry #</th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Description</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Total Debit</th>
                <th className="px-4 py-3 text-right">Total Credit</th>
                <th className="px-4 py-3">Created By</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-secondary-100">
              {records.map((entry) => (
                <tr
                  key={entry.id}
                  onClick={() => handleSelect(entry)}
                  className={`cursor-pointer transition-colors ${
                    selectedId === entry.id
                      ? "bg-primary-50"
                      : "hover:bg-secondary-50"
                  }`}
                >
                  <td className="px-4 py-3 font-medium text-secondary-900">
                    {entry.entry_number}
                  </td>
                  <td className="px-4 py-3 text-secondary-600">
                    {formatDate(entry.date)}
                  </td>
                  <td className="max-w-[200px] truncate px-4 py-3 text-secondary-600">
                    {entry.description || "—"}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={entry.status} />
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-secondary-900">
                    {formatCurrency(entry.total_debit)}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-secondary-900">
                    {formatCurrency(entry.total_credit)}
                  </td>
                  <td className="px-4 py-3 text-secondary-600">
                    {entry.created_by?.name || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {renderPagination()}
      </>
    );
  };

  const renderList = () => (
    <div className="space-y-4">
      {renderSearchAndFilter()}
      {renderListTable()}
    </div>
  );

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
          Failed to load journal entries.
        </div>
      );
    }

    if (records.length === 0) {
      return (
        <div className="rounded-lg bg-secondary-50 p-8 text-center">
          <FileText className="mx-auto h-8 w-8 text-secondary-300" />
          <p className="mt-2 text-sm text-secondary-500">
            {debouncedSearch || statusFilter
              ? "No journal entries match your filters."
              : "No journal entries yet."}
          </p>
        </div>
      );
    }

    return (
      <div className="space-y-2">
        {records.map((entry) => (
          <div
            key={entry.id}
            onClick={() => handleSelect(entry)}
            className="cursor-pointer rounded-lg border border-secondary-200 bg-white p-3"
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-secondary-900">
                {entry.entry_number}
              </span>
              <StatusBadge status={entry.status} />
            </div>
            <div className="mt-1 text-xs text-secondary-500 line-clamp-1">
              {entry.description || "—"}
            </div>
            <div className="mt-1 flex items-center gap-2 text-xs text-secondary-400">
              <span>{formatDate(entry.date)}</span>
              <span className="text-secondary-300">|</span>
              <span>Dr {formatCurrency(entry.total_debit)}</span>
              <span className="text-secondary-300">|</span>
              <span>Cr {formatCurrency(entry.total_credit)}</span>
            </div>
          </div>
        ))}
        {/* Pagination for mobile */}
        {totalCount > pageSize && (
          <div className="flex items-center justify-between pt-2 text-sm">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="rounded-lg border border-secondary-300 px-3 py-1.5 text-xs font-medium text-secondary-700 hover:bg-secondary-50 disabled:opacity-50"
            >
              Previous
            </button>
            <span className="text-xs text-secondary-500">
              {page} of {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="rounded-lg border border-secondary-300 px-3 py-1.5 text-xs font-medium text-secondary-700 hover:bg-secondary-50 disabled:opacity-50"
            >
              Next
            </button>
          </div>
        )}
      </div>
    );
  };

  // ── Render: Detail View ──

  const renderDetail = () => {
    if (!selectedEntry) {
      return (
        <div className="flex h-48 items-center justify-center">
          <div className="text-center">
            <FileText className="mx-auto h-10 w-10 text-secondary-200" />
            <p className="mt-2 text-sm text-secondary-500">
              Select a journal entry to view details
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

    const entry = selectedEntry;
    const isDraft = entry.status === "draft";
    const isPosted = entry.status === "posted";

    return (
      <div className="space-y-4">
        {/* Action buttons */}
        <div className="flex items-center gap-2">
          {isDraft && (
            <>
              <button
                onClick={handleEditOpen}
                className="inline-flex items-center gap-1.5 rounded-lg border border-secondary-300 px-3 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-50"
              >
                <Pencil className="h-4 w-4" />
                <span className="hidden sm:inline">Edit</span>
              </button>
              <button
                onClick={() => handleDelete(entry)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-danger-300 px-3 py-2 text-sm font-medium text-danger-600 hover:bg-danger-50"
              >
                <Trash2 className="h-4 w-4" />
                <span className="hidden sm:inline">Delete</span>
              </button>
              <button
                onClick={() => handlePost(entry)}
                className="inline-flex items-center gap-1.5 rounded-lg bg-success-600 px-4 py-2 text-sm font-medium text-white hover:bg-success-500"
              >
                <CheckCircle className="h-4 w-4" />
                <span className="hidden sm:inline">Post to GL</span>
              </button>
            </>
          )}
          {isPosted && (
            <button
              onClick={() => handleReverse(entry)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-warning-500 px-3 py-2 text-sm font-medium text-warning-600 hover:bg-amber-50"
            >
              <RotateCcw className="h-4 w-4" />
              <span className="hidden sm:inline">Reverse</span>
            </button>
          )}
        </div>

        {/* Entry metadata */}
        <AccordionSection
          title="Entry Details"
          isOpen={true}
          onToggle={() => {}}
        >
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <span className="text-xs font-medium uppercase tracking-wider text-secondary-500">
                Entry Number
              </span>
              <p className="mt-1 text-sm font-medium text-secondary-900">{entry.entry_number}</p>
            </div>
            <div>
              <span className="text-xs font-medium uppercase tracking-wider text-secondary-500">
                Date
              </span>
              <p className="mt-1 text-sm text-secondary-900">{formatDate(entry.date)}</p>
            </div>
            <div>
              <span className="text-xs font-medium uppercase tracking-wider text-secondary-500">
                Status
              </span>
              <div className="mt-1">
                <StatusBadge status={entry.status} />
              </div>
            </div>
            <div>
              <span className="text-xs font-medium uppercase tracking-wider text-secondary-500">
                Reference
              </span>
              <p className="mt-1 text-sm text-secondary-900">{entry.reference || "—"}</p>
            </div>
            <div>
              <span className="text-xs font-medium uppercase tracking-wider text-secondary-500">
                Created By
              </span>
              <p className="mt-1 text-sm text-secondary-900">
                {entry.created_by?.name || "—"}
              </p>
            </div>
            <div>
              <span className="text-xs font-medium uppercase tracking-wider text-secondary-500">
                Total Debit
              </span>
              <p className="mt-1 text-sm font-mono text-secondary-900">
                {formatCurrency(entry.total_debit)}
              </p>
            </div>
            <div>
              <span className="text-xs font-medium uppercase tracking-wider text-secondary-500">
                Total Credit
              </span>
              <p className="mt-1 text-sm font-mono text-secondary-900">
                {formatCurrency(entry.total_credit)}
              </p>
            </div>
            {entry.reversal_entry_id && (
              <div>
                <span className="text-xs font-medium uppercase tracking-wider text-secondary-500">
                  Reversal Entry
                </span>
                <p className="mt-1 text-sm text-secondary-900">{entry.reversal_entry_id}</p>
              </div>
            )}
            {entry.reversed_entry_id && (
              <div>
                <span className="text-xs font-medium uppercase tracking-wider text-secondary-500">
                  Reversed Entry
                </span>
                <p className="mt-1 text-sm text-secondary-900">{entry.reversed_entry_id}</p>
              </div>
            )}
          </div>
          {entry.description && (
            <div className="mt-3">
              <span className="text-xs font-medium uppercase tracking-wider text-secondary-500">
                Description
              </span>
              <p className="mt-1 text-sm text-secondary-900">{entry.description}</p>
            </div>
          )}
        </AccordionSection>

        {/* Line items */}
        <AccordionSection
          title={`Line Items (${entry.lines?.length || 0})`}
          isOpen={true}
          onToggle={() => {}}
        >
          <LineItemsReadonlyTable lines={entry.lines || []} />
        </AccordionSection>
      </div>
    );
  };

  // ── Render: Main Layout ──

  // Mobile: list view
  if (isMobile && !showMobileDetail) {
    return (
      <div className="p-4">
        <div className="mb-4 flex items-center justify-between">
          <h1 className="text-lg font-bold text-secondary-900">Journal Entries</h1>
          <button
            onClick={handleCreateOpen}
            className="inline-flex items-center justify-center rounded-lg bg-primary-600 p-2 text-white hover:bg-primary-700"
          >
            <Plus className="h-5 w-5" />
          </button>
        </div>
        {renderSearchAndFilter()}
        <div className="mt-4">{renderMobileCards()}</div>

        {/* Form Modal */}
        {showFormModal && (
          <JournalEntryFormModal
            editingEntry={editingEntry}
            onClose={() => {
              setShowFormModal(false);
              setEditingEntry(null);
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
          Back to Journal Entries
        </button>
        {renderDetail()}

        {/* Form Modal */}
        {showFormModal && (
          <JournalEntryFormModal
            editingEntry={editingEntry}
            onClose={() => {
              setShowFormModal(false);
              setEditingEntry(null);
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
          label: "Journal Entries",
          content: (
            <div>
              <div className="mb-4 flex items-center justify-between">
                <h1 className="text-xl font-bold text-secondary-900">Journal Entries</h1>
                <button
                  onClick={handleCreateOpen}
                  className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
                >
                  + New Entry
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
        <JournalEntryFormModal
          editingEntry={editingEntry}
          onClose={() => {
            setShowFormModal(false);
            setEditingEntry(null);
          }}
          onDone={handleFormDone}
        />
      )}
    </div>
  );
}
