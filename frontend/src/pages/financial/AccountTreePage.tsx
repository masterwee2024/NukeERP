import { useState, useMemo, useEffect, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAction } from "@/components/ui/ConfirmDialog";
import api from "@/lib/api";
import { useIsMobile } from "@/hooks/useIsMobile";
import { useDebounce } from "@/hooks/useDebounce";
import {
  ChevronRight,
  ChevronDown,
  Plus,
  Pencil,
  Trash2,
  ArrowLeft,
  Upload,
  Download,
  X,
  Search,
  Loader2,
  Building2,
  CheckSquare,
  Square,
  FileText,
} from "lucide-react";

// ── Types ──

interface Account {
  id: string;
  code: string;
  name: string;
  account_type: string;
  subtype: string | null;
  level: number;
  is_group: boolean;
  is_active: boolean;
  mfrs_code: string | null;
  parent_id: string | null;
  children: Account[];
  updated_at?: string;
}

interface AccountAssignment {
  id: string;
  code: string;
  name: string;
  is_assigned: boolean;
}

type AccountTypeOption = "asset" | "liability" | "equity" | "revenue" | "expense";

const ACCOUNT_TYPE_OPTIONS: { value: AccountTypeOption; label: string }[] = [
  { value: "asset", label: "Asset" },
  { value: "liability", label: "Liability" },
  { value: "equity", label: "Equity" },
  { value: "revenue", label: "Revenue" },
  { value: "expense", label: "Expense" },
];

const SUBTYPE_MAP: Record<AccountTypeOption, { value: string; label: string }[]> = {
  asset: [
    { value: "current", label: "Current Asset" },
    { value: "fixed", label: "Fixed Asset" },
    { value: "other", label: "Other Asset" },
  ],
  liability: [
    { value: "current", label: "Current Liability" },
    { value: "long_term", label: "Long-term Liability" },
    { value: "other", label: "Other Liability" },
  ],
  equity: [
    { value: "equity", label: "Equity" },
    { value: "retained_earnings", label: "Retained Earnings" },
    { value: "other", label: "Other Equity" },
  ],
  revenue: [
    { value: "operating", label: "Operating Revenue" },
    { value: "other", label: "Other Revenue" },
  ],
  expense: [
    { value: "operating", label: "Operating Expense" },
    { value: "cost_of_goods_sold", label: "Cost of Goods Sold" },
    { value: "other", label: "Other Expense" },
  ],
};

// ── Colour map for account type badges ──

const TYPE_BADGE: Record<string, string> = {
  asset: "bg-blue-50 text-blue-700 border-blue-200",
  liability: "bg-amber-50 text-amber-700 border-amber-200",
  equity: "bg-green-50 text-green-700 border-green-200",
  revenue: "bg-purple-50 text-purple-700 border-purple-200",
  expense: "bg-red-50 text-red-700 border-red-200",
};

// ── Helpers ──

function flattenAccounts(accounts: Account[]): Account[] {
  const result: Account[] = [];
  function walk(list: Account[]) {
    for (const acc of list) {
      result.push(acc);
      if (acc.children && acc.children.length > 0) walk(acc.children);
    }
  }
  walk(accounts);
  return result;
}

function buildParentOptions(accounts: Account[]): { id: string; code: string; name: string; level: number }[] {
  const result: { id: string; code: string; name: string; level: number }[] = [];
  function walk(list: Account[], depth: number) {
    for (const acc of list) {
      if (acc.is_group) {
        result.push({ id: acc.id, code: acc.code, name: acc.name, level: depth });
      }
      if (acc.children && acc.children.length > 0) walk(acc.children, depth + 1);
    }
  }
  walk(accounts, 0);
  return result;
}

function getDefaultFormValues() {
  return {
    code: "",
    name: "",
    account_type: "asset" as AccountTypeOption,
    subtype: "",
    parent_id: "",
    is_group: false,
    mfrs_code: "",
  };
}

// ── Tree Node Component ──

function TreeNode({
  account,
  expandedIds,
  onToggle,
  onSelect,
  selectedId,
  searchQuery,
  depth,
}: {
  account: Account;
  expandedIds: Set<string>;
  onToggle: (id: string) => void;
  onSelect: (acc: Account) => void;
  selectedId: string | null;
  searchQuery: string;
  depth: number;
}) {
  const hasChildren = account.children && account.children.length > 0;
  const isExpanded = expandedIds.has(account.id);
  const isSelected = selectedId === account.id;
  const matchesSearch =
    !searchQuery ||
    account.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
    account.name.toLowerCase().includes(searchQuery.toLowerCase());

  // If searching and this node matches, show it + all ancestors
  // If searching and this node doesn't match but children do, still render
  const childrenMatch = hasChildren && account.children.some((c) => {
    if (searchQuery) {
      return (
        c.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (c.children && c.children.some((gc) =>
          gc.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
          gc.name.toLowerCase().includes(searchQuery.toLowerCase())
        ))
      );
    }
    return false;
  });

  const shouldRender = matchesSearch || childrenMatch || !searchQuery;

  if (!shouldRender) return null;

  return (
    <>
      <div
        onClick={() => onSelect(account)}
        className={`flex cursor-pointer items-center gap-1 rounded-lg px-2 py-1.5 text-sm transition-colors ${
          isSelected
            ? "bg-primary-50 text-primary-700"
            : "text-secondary-700 hover:bg-secondary-50"
        }`}
        style={{ paddingLeft: `${12 + depth * 20}px` }}
      >
        {/* Expand/collapse chevron */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            if (hasChildren) onToggle(account.id);
          }}
          className={`flex h-5 w-5 items-center justify-center rounded ${
            hasChildren
              ? "text-secondary-400 hover:bg-secondary-100"
              : "text-transparent"
          }`}
        >
          {hasChildren ? (
            isExpanded ? (
              <ChevronDown className="h-3.5 w-3.5" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5" />
            )
          ) : (
            <span className="inline-block h-3.5 w-3.5" />
          )}
        </button>

        {/* Code */}
        <span className="font-mono text-xs text-secondary-500 w-20 shrink-0 truncate">
          {account.code}
        </span>

        {/* Name */}
        <span className="flex-1 truncate font-medium">{account.name}</span>

        {/* Type badge */}
        <span
          className={`hidden shrink-0 rounded-full border px-2 py-0.5 text-xs capitalize sm:inline-block ${
            TYPE_BADGE[account.account_type] || "bg-secondary-50 text-secondary-600 border-secondary-200"
          }`}
        >
          {account.account_type}
        </span>

        {/* Group indicator */}
        {account.is_group && (
          <span className="hidden shrink-0 rounded bg-secondary-100 px-1.5 py-0.5 text-[10px] font-medium text-secondary-500 sm:inline-block">
            Group
          </span>
        )}
      </div>

      {/* Children (recursive) */}
      {hasChildren && isExpanded && (
        <>
          {account.children.map((child) => (
            <TreeNode
              key={child.id}
              account={child}
              expandedIds={expandedIds}
              onToggle={onToggle}
              onSelect={onSelect}
              selectedId={selectedId}
              searchQuery={searchQuery}
              depth={depth + 1}
            />
          ))}
        </>
      )}
    </>
  );
}

// ── Form Fields for Create/Edit ──

function AccountFormFields({
  form,
  setForm,
  accounts,
  parentId,
}: {
  form: ReturnType<typeof getDefaultFormValues>;
  setForm: (f: typeof form) => void;
  accounts: Account[];
  parentId?: string;
}) {
  const parentOptions = useMemo(() => buildParentOptions(accounts), [accounts]);
  const subtypes = SUBTYPE_MAP[form.account_type] || [];

  // Auto-clear subtype if type changes and current subtype not valid
  useEffect(() => {
    const valid = subtypes.some((s) => s.value === form.subtype);
    if (!valid && subtypes.length > 0) {
      setForm({ ...form, subtype: subtypes[0].value });
    } else if (!valid) {
      setForm({ ...form, subtype: "" });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.account_type]);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {/* Code */}
        <div>
          <label className="block text-sm font-medium text-secondary-700">
            Code <span className="text-danger-500">*</span>
          </label>
          <input
            type="text"
            value={form.code}
            onChange={(e) => setForm({ ...form, code: e.target.value })}
            placeholder="e.g. 1000"
            className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
            required
          />
        </div>

        {/* Name */}
        <div>
          <label className="block text-sm font-medium text-secondary-700">
            Name <span className="text-danger-500">*</span>
          </label>
          <input
            type="text"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="e.g. Cash & Bank"
            className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
            required
          />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {/* Account Type */}
        <div>
          <label className="block text-sm font-medium text-secondary-700">
            Account Type <span className="text-danger-500">*</span>
          </label>
          <select
            value={form.account_type}
            onChange={(e) =>
              setForm({
                ...form,
                account_type: e.target.value as AccountTypeOption,
                subtype: "",
              })
            }
            className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
          >
            {ACCOUNT_TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Subtype */}
        <div>
          <label className="block text-sm font-medium text-secondary-700">Subtype</label>
          <select
            value={form.subtype}
            onChange={(e) => setForm({ ...form, subtype: e.target.value })}
            className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
          >
            <option value="">— None —</option>
            {subtypes.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Parent Account */}
      <div>
        <label className="block text-sm font-medium text-secondary-700">Parent Account</label>
        <select
          value={form.parent_id}
          onChange={(e) => setForm({ ...form, parent_id: e.target.value })}
          className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
        >
          <option value="">— None (Top Level) —</option>
          {parentOptions
            .filter((p) => p.id !== parentId) // prevent self-reference during edit
            .map((p) => (
              <option key={p.id} value={p.id}>
                {"  ".repeat(p.level)}
                {p.code} — {p.name}
              </option>
            ))}
        </select>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {/* MFRS Code */}
        <div>
          <label className="block text-sm font-medium text-secondary-700">MFRS Code</label>
          <input
            type="text"
            value={form.mfrs_code}
            onChange={(e) => setForm({ ...form, mfrs_code: e.target.value })}
            placeholder="e.g. MFRS 101"
            className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
          />
        </div>

        {/* Is Group */}
        <div className="flex items-end pb-2">
          <label className="flex items-center gap-2 text-sm text-secondary-700">
            <input
              type="checkbox"
              checked={form.is_group}
              onChange={(e) => setForm({ ...form, is_group: e.target.checked })}
              className="h-4 w-4 rounded border-secondary-300 text-primary-600 focus:ring-primary-500"
            />
            Is Group Account (can have children)
          </label>
        </div>
      </div>
    </div>
  );
}

// ── Company Assignment Modal ──

function CompanyAssignmentModal({
  onClose,
  onDone,
}: {
  onClose: () => void;
  onDone: () => void;
}) {
  const currentCompanyId = localStorage.getItem("current_company_id");
  const { execute } = useAction();
  const queryClient = useQueryClient();

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [loaded, setLoaded] = useState(false);

  const { data: assignmentsData, isLoading: assignmentsLoading } = useQuery({
    queryKey: ["account-assignments", currentCompanyId],
    queryFn: async (): Promise<AccountAssignment[]> => {
      const { data } = await api.get(
        `/financial/accounts/assignments/${currentCompanyId}/`
      );
      return data.results || data;
    },
    enabled: !!currentCompanyId,
  });

  // Initialize selected IDs from loaded data
  useEffect(() => {
    if (assignmentsData && !loaded) {
      setSelectedIds(
        new Set(
          assignmentsData
            .filter((a) => a.is_assigned)
            .map((a) => a.id)
        )
      );
      setLoaded(true);
    }
  }, [assignmentsData, loaded]);

  const toggleId = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    if (assignmentsData) {
      setSelectedIds(new Set(assignmentsData.map((a) => a.id)));
    }
  };

  const deselectAll = () => {
    setSelectedIds(new Set());
  };

  const handleSave = async () => {
    const result = await execute({
      confirm: {
        title: "Save Account Assignments",
        message: `Assign ${selectedIds.size} account(s) to the current company?`,
        variant: "info",
        confirmText: "Save",
      },
      action: async () => {
        const { data } = await api.post(
          `/financial/accounts/assignments/${currentCompanyId}/`,
          { record_ids: Array.from(selectedIds) }
        );
        return data;
      },
      success: {
        title: "Assignments Saved",
        variant: "info",
      },
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["account-assignments"] });
        onDone();
        onClose();
      },
    });
    if (!result) return;
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 pt-10"
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
              Company Account Assignments
            </h2>
            <button
              onClick={onClose}
              className="rounded p-1 text-secondary-400 hover:text-secondary-600"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {assignmentsLoading && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-primary-500" />
            </div>
          )}

          {!assignmentsLoading && assignmentsData && (
            <>
              {/* Count + Select All / Deselect All */}
              <div className="mb-3 flex items-center justify-between text-sm">
                <span className="text-secondary-500">
                  {selectedIds.size} of {assignmentsData.length} selected
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={selectAll}
                    className="text-primary-600 hover:text-primary-700 text-xs font-medium"
                  >
                    Select All
                  </button>
                  <button
                    onClick={deselectAll}
                    className="text-secondary-500 hover:text-secondary-700 text-xs font-medium"
                  >
                    Deselect All
                  </button>
                </div>
              </div>

              {/* Account list */}
              <div className="max-h-80 space-y-1 overflow-y-auto rounded-lg border border-secondary-200 p-2">
                {assignmentsData.map((acc) => (
                  <div
                    key={acc.id}
                    onClick={() => toggleId(acc.id)}
                    className="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 text-sm hover:bg-secondary-50"
                  >
                    {selectedIds.has(acc.id) ? (
                      <CheckSquare className="h-4 w-4 shrink-0 text-primary-600" />
                    ) : (
                      <Square className="h-4 w-4 shrink-0 text-secondary-300" />
                    )}
                    <span className="font-mono text-xs text-secondary-500 w-16 shrink-0">
                      {acc.code}
                    </span>
                    <span className="flex-1 truncate text-secondary-900">{acc.name}</span>
                  </div>
                ))}
                {assignmentsData.length === 0 && (
                  <p className="py-4 text-center text-sm text-secondary-500">
                    No accounts found.
                  </p>
                )}
              </div>

              {/* Footer */}
              <div className="mt-4 flex justify-end gap-3">
                <button
                  onClick={onClose}
                  className="rounded-lg border border-secondary-300 px-4 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSave}
                  className="rounded-lg bg-primary-600 px-6 py-2 text-sm font-medium text-white hover:bg-primary-700"
                >
                  Save Assignments
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Create/Edit Account Modal ──

function AccountFormModal({
  accounts,
  editingAccount,
  defaultParentId,
  onClose,
  onDone,
}: {
  accounts: Account[];
  editingAccount: Account | null;
  defaultParentId?: string;
  onClose: () => void;
  onDone: () => void;
}) {
  const { execute } = useAction();
  const isEditing = !!editingAccount;
  const [form, setForm] = useState(() => ({
    ...getDefaultFormValues(),
    parent_id: defaultParentId || "",
  }));
  const [initialized, setInitialized] = useState(false);

  // Pre-populate form when editing
  useEffect(() => {
    if (isEditing && editingAccount && !initialized) {
      setForm({
        code: editingAccount.code || "",
        name: editingAccount.name || "",
        account_type: (editingAccount.account_type as AccountTypeOption) || "asset",
        subtype: editingAccount.subtype || "",
        parent_id: editingAccount.parent_id || "",
        is_group: editingAccount.is_group || false,
        mfrs_code: editingAccount.mfrs_code || "",
      });
      setInitialized(true);
    }
  }, [editingAccount, isEditing, initialized]);

  const handleSave = async () => {
    if (!form.code.trim() || !form.name.trim()) {
      return;
    }

    const payload: Record<string, unknown> = {
      code: form.code.trim(),
      name: form.name.trim(),
      account_type: form.account_type,
      subtype: form.subtype || null,
      parent_id: form.parent_id || null,
      is_group: form.is_group,
      mfrs_code: form.mfrs_code || null,
    };

    if (isEditing && editingAccount) {
      payload.updated_at = editingAccount.updated_at;
    }

    const result = await execute({
      confirm: {
        title: isEditing ? "Update Account" : "Create Account",
        message: isEditing
          ? `Update "${editingAccount!.code} — ${editingAccount!.name}"?`
          : `Create account "${form.code} — ${form.name}"?`,
        variant: "info",
        confirmText: isEditing ? "Update" : "Create",
      },
      action: async () => {
        if (isEditing && editingAccount) {
          const { data } = await api.put(
            `/financial/accounts/${editingAccount.id}/`,
            payload
          );
          return data;
        } else {
          const { data } = await api.post("/financial/accounts/", payload);
          return data;
        }
      },
      success: {
        title: isEditing ? "Account Updated" : "Account Created",
        variant: "info",
      },
      onSuccess: () => {
        onDone();
        onClose();
      },
    });
    if (!result) return;
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 pt-10"
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
              {isEditing ? "Edit Account" : "New Account"}
            </h2>
            <button
              onClick={onClose}
              className="rounded p-1 text-secondary-400 hover:text-secondary-600"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <AccountFormFields
            form={form}
            setForm={setForm}
            accounts={accounts}
            parentId={editingAccount?.id}
          />

          {/* Footer */}
          <div className="mt-6 flex justify-end gap-3 border-t border-secondary-200 pt-4">
            <button
              onClick={onClose}
              className="rounded-lg border border-secondary-300 px-4 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={!form.code.trim() || !form.name.trim()}
              className="rounded-lg bg-primary-600 px-6 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            >
              {isEditing ? "Update Account" : "Create Account"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Account Detail Panel ──

function AccountDetailPanel({
  account,
  onEdit,
  onDelete,
  onAddChild,
  isDeleting,
}: {
  account: Account;
  onEdit: () => void;
  onDelete: () => void;
  onAddChild: () => void;
  isDeleting: boolean;
}) {
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-semibold text-secondary-900">{account.name}</h2>
          <p className="font-mono text-sm text-secondary-500">{account.code}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onAddChild}
            title="Add Child"
            className="inline-flex items-center gap-1 rounded-lg border border-secondary-300 px-3 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-50"
          >
            <Plus className="h-4 w-4" />
            <span className="hidden sm:inline">Add Child</span>
          </button>
          <button
            onClick={onEdit}
            title="Edit"
            className="inline-flex items-center gap-1 rounded-lg border border-secondary-300 px-3 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-50"
          >
            <Pencil className="h-4 w-4" />
            <span className="hidden sm:inline">Edit</span>
          </button>
          <button
            onClick={onDelete}
            disabled={isDeleting}
            title="Delete"
            className="inline-flex items-center gap-1 rounded-lg border border-danger-300 px-3 py-2 text-sm font-medium text-danger-600 hover:bg-danger-50 disabled:opacity-50"
          >
            {isDeleting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Trash2 className="h-4 w-4" />
            )}
            <span className="hidden sm:inline">Delete</span>
          </button>
        </div>
      </div>

      {/* Info fields */}
      <div className="rounded-lg border border-secondary-200 bg-white">
        <div className="grid grid-cols-2 gap-4 p-4">
          <div>
            <span className="text-xs font-medium text-secondary-500 uppercase tracking-wider">
              Type
            </span>
            <p className="mt-1 text-sm text-secondary-900 capitalize">{account.account_type}</p>
          </div>
          <div>
            <span className="text-xs font-medium text-secondary-500 uppercase tracking-wider">
              Subtype
            </span>
            <p className="mt-1 text-sm text-secondary-900 capitalize">
              {account.subtype || "—"}
            </p>
          </div>
          <div>
            <span className="text-xs font-medium text-secondary-500 uppercase tracking-wider">
              Group
            </span>
            <p className="mt-1 text-sm text-secondary-900">
              {account.is_group ? "Yes" : "No"}
            </p>
          </div>
          <div>
            <span className="text-xs font-medium text-secondary-500 uppercase tracking-wider">
              MFRS Code
            </span>
            <p className="mt-1 text-sm text-secondary-900">
              {account.mfrs_code || "—"}
            </p>
          </div>
          <div>
            <span className="text-xs font-medium text-secondary-500 uppercase tracking-wider">
              Active
            </span>
            <p className="mt-1 text-sm text-secondary-900">
              {account.is_active ? "Yes" : "No"}
            </p>
          </div>
          <div>
            <span className="text-xs font-medium text-secondary-500 uppercase tracking-wider">
              Level
            </span>
            <p className="mt-1 text-sm text-secondary-900">{account.level}</p>
          </div>
        </div>
      </div>

      {/* Children summary */}
      {account.children && account.children.length > 0 && (
        <div className="rounded-lg border border-secondary-200 bg-white p-4">
          <h3 className="mb-2 text-sm font-semibold text-secondary-900">
            Children ({account.children.length})
          </h3>
          <div className="space-y-1">
            {account.children.map((child) => (
              <div
                key={child.id}
                className="flex items-center gap-2 text-sm text-secondary-600"
              >
                <span className="font-mono text-xs text-secondary-400 w-16 shrink-0">
                  {child.code}
                </span>
                <span className="flex-1 truncate">{child.name}</span>
                <span
                  className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] capitalize ${
                    TYPE_BADGE[child.account_type] || "bg-secondary-50 text-secondary-600 border-secondary-200"
                  }`}
                >
                  {child.account_type}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── CSV Import Overlay ──

function CsvImportOverlay({
  onClose,
  onDone,
}: {
  onClose: () => void;
  onDone: () => void;
}) {
  const { execute } = useAction();
  const [file, setFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);

  const handleDownloadTemplate = () => {
    // Open template download in new tab
    window.open("/api/v1/financial/accounts/template/", "_blank");
    // ^ uses full path because it's a direct window.open, not via api client
  };

  const handleImport = async () => {
    if (!file) return;

    setImporting(true);
    const result = await execute({
      confirm: {
        title: "Import CSV",
        message: `Import accounts from "${file.name}"?`,
        variant: "info",
        confirmText: "Import",
      },
      action: async () => {
        const formData = new FormData();
        formData.append("file", file);
        const { data } = await api.post(
          "/financial/accounts/import/",
          formData,
          {
            headers: { "Content-Type": "multipart/form-data" },
          }
        );
        return data;
      },
      success: {
        title: "Import Complete",
        message: "Accounts have been imported successfully.",
        variant: "info",
      },
      onSuccess: () => {
        setImporting(false);
        onDone();
        onClose();
      },
    });
    if (!result) {
      setImporting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 pt-10"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-md rounded-lg bg-white shadow-xl mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-4 md:p-6">
          {/* Header */}
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-secondary-900">Import Accounts (CSV)</h2>
            <button
              onClick={onClose}
              className="rounded p-1 text-secondary-400 hover:text-secondary-600"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Content */}
          <div className="space-y-4">
            <p className="text-sm text-secondary-600">
              Upload a CSV file with account data. The file must have columns for code, name,
              account_type, and optional columns for subtype, parent, is_group, mfrs_code.
            </p>

            {/* Download template link */}
            <button
              onClick={handleDownloadTemplate}
              className="inline-flex items-center gap-2 text-sm font-medium text-primary-600 hover:text-primary-700"
            >
              <Download className="h-4 w-4" />
              Download CSV Template
            </button>

            {/* File picker */}
            <div>
              <label className="mb-1 block text-sm font-medium text-secondary-700">
                CSV File
              </label>
              <input
                type="file"
                accept=".csv"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    setFile(e.target.files[0]);
                  }
                }}
                className="w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm file:mr-3 file:rounded file:border-0 file:bg-primary-50 file:px-3 file:py-1 file:text-sm file:font-medium file:text-primary-700 hover:file:bg-primary-100"
              />
            </div>

            {file && (
              <div className="rounded-lg bg-secondary-50 p-3 text-sm text-secondary-700">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-secondary-400" />
                  <span className="font-medium">{file.name}</span>
                  <span className="text-secondary-400">
                    ({(file.size / 1024).toFixed(1)} KB)
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="mt-6 flex justify-end gap-3 border-t border-secondary-200 pt-4">
            <button
              onClick={onClose}
              className="rounded-lg border border-secondary-300 px-4 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-50"
            >
              Cancel
            </button>
            <button
              onClick={handleImport}
              disabled={!file || importing}
              className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-6 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            >
              {importing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Importing...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4" />
                  Import
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Main Page Component ──

export default function AccountTreePage() {
  const queryClient = useQueryClient();
  const { execute } = useAction();
  const isMobile = useIsMobile();

  // Data state
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [selectedAccount, setSelectedAccount] = useState<Account | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingAccount, setEditingAccount] = useState<Account | null>(null);
  const [showAssignmentModal, setShowAssignmentModal] = useState(false);
  const [showImportOverlay, setShowImportOverlay] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [showMobileDetail, setShowMobileDetail] = useState(false);
  const [creatingChildOf, setCreatingChildOf] = useState<Account | null>(null);

  const debouncedSearch = useDebounce(searchQuery, 300);

  // Fetch accounts (nested tree)
  const {
    data: accountsData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["financial-accounts"],
    queryFn: async (): Promise<Account[]> => {
      const { data } = await api.get("/financial/accounts/");
      return data.results || data || [];
    },
    staleTime: 30_000,
  });

  const accounts = accountsData || [];

  // Auto-expand level 0 and level 1 accounts when tree first loads
  useEffect(() => {
    if (accounts.length > 0 && expandedIds.size === 0) {
      const ids = new Set<string>();
      function walk(list: Account[], depth: number) {
        for (const acc of list) {
          if (depth <= 1 && acc.children?.length) ids.add(acc.id);
          if (acc.children?.length) walk(acc.children, depth + 1);
        }
      }
      walk(accounts, 0);
      setExpandedIds(ids);
    }
  }, [accounts]);

  // Filtered accounts based on search
  const filteredAccounts = useMemo(() => {
    if (!debouncedSearch) return accounts;
    const allFlat = flattenAccounts(accounts);
    const matchedIds = new Set(
      allFlat
        .filter(
          (a) =>
            a.code.toLowerCase().includes(debouncedSearch.toLowerCase()) ||
            a.name.toLowerCase().includes(debouncedSearch.toLowerCase())
        )
        .map((a) => a.id)
    );
    // Also include ancestors of matches
    function collectAncestors(list: Account[]): Set<string> {
      const ancestors = new Set<string>();
      function walk(list: Account[]): boolean {
        for (const acc of list) {
          if (matchedIds.has(acc.id)) {
            ancestors.add(acc.id);
            continue;
          }
          if (acc.children && acc.children.length > 0) {
            const childMatched = walk(acc.children);
            if (childMatched) ancestors.add(acc.id);
          }
        }
        return ancestors.size > 0;
      }
      walk(list);
      return ancestors;
    }
    const ancestorIds = collectAncestors(accounts);
    const allRelevantIds = new Set([...matchedIds, ...ancestorIds]);

    // Filter tree to only relevant nodes
    function filterTree(list: Account[]): Account[] {
      return list
        .filter((a) => allRelevantIds.has(a.id))
        .map((a) => ({
          ...a,
          children: a.children ? filterTree(a.children) : [],
        }));
    }

    return filterTree(accounts);
  }, [accounts, debouncedSearch]);

  // Auto-expand when searching
  useEffect(() => {
    if (debouncedSearch) {
      const flat = flattenAccounts(accounts);
      const allIds = new Set(flat.map((a) => a.id));
      setExpandedIds(allIds);
    }
  }, [debouncedSearch, accounts]);

  // When accounts change, ensure selected account is still valid
  useEffect(() => {
    if (selectedAccount) {
      const flat = flattenAccounts(accounts);
      const stillExists = flat.some((a) => a.id === selectedAccount.id);
      if (!stillExists) {
        setSelectedAccount(null);
        setShowMobileDetail(false);
      }
    }
  }, [accounts, selectedAccount]);

  const handleToggle = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const handleSelect = useCallback(
    (acc: Account) => {
      setSelectedAccount(acc);
      if (isMobile) setShowMobileDetail(true);
    },
    [isMobile]
  );

  const handleRefresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["financial-accounts"] });
  }, [queryClient]);

  const handleCreate = useCallback(() => {
    setCreatingChildOf(null);
    setEditingAccount(null);
    setShowCreateModal(true);
  }, []);

  const handleAddChild = useCallback(
    (parent: Account) => {
      setCreatingChildOf(parent);
      setEditingAccount(null);
      setShowCreateModal(true);
    },
    []
  );

  const handleEdit = useCallback(
    (acc: Account) => {
      setEditingAccount(acc);
      setCreatingChildOf(null);
      setShowCreateModal(true);
    },
    []
  );

  const handleDelete = useCallback(
    async (acc: Account) => {
      setDeleteLoading(true);
      await execute({
        confirm: {
          title: "Delete Account",
          message: `Delete "${acc.code} — ${acc.name}"? This action cannot be undone.${
            acc.children && acc.children.length > 0
              ? " This account has children and cannot be deleted."
              : ""
          }`,
          variant: "danger",
          confirmText: "Delete",
        },
        action: async () => {
          const { data } = await api.delete(`/financial/accounts/${acc.id}/`);
          return data;
        },
        success: {
          title: "Account Deleted",
          variant: "info",
        },
        onSuccess: () => {
          if (selectedAccount?.id === acc.id) {
            setSelectedAccount(null);
            setShowMobileDetail(false);
          }
          handleRefresh();
        },
      });
      setDeleteLoading(false);
    },
    [execute, handleRefresh, selectedAccount]
  );

  // Reset creating-child mode when modal closes
  useEffect(() => {
    if (!showCreateModal) {
      setCreatingChildOf(null);
    }
  }, [showCreateModal]);

  // ── Render: Tree View ──

  const renderTree = () => (
    <div className="space-y-4">
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-secondary-400" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search by code or name..."
          className="w-full rounded-lg border border-secondary-300 pl-9 pr-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
        />
        {searchQuery && (
          <button
            onClick={() => setSearchQuery("")}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-secondary-400 hover:text-secondary-600"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Account count */}
      <div className="flex items-center justify-between">
        <p className="text-xs text-secondary-500">
          {flattenAccounts(accounts).length} accounts
          {debouncedSearch && ` (${flattenAccounts(filteredAccounts).length} filtered)`}
        </p>
      </div>

      {/* Tree */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-primary-500" />
        </div>
      ) : error ? (
        <div className="rounded-lg bg-danger-50 p-4 text-sm text-danger-700">
          Failed to load accounts. Please try again.
        </div>
      ) : filteredAccounts.length === 0 ? (
        <div className="rounded-lg bg-secondary-50 p-8 text-center">
          <FileText className="mx-auto h-8 w-8 text-secondary-300" />
          <p className="mt-2 text-sm text-secondary-500">
            {debouncedSearch ? "No accounts match your search." : "No accounts yet. Create one to get started."}
          </p>
        </div>
      ) : (
        <div className="space-y-0.5">
          {filteredAccounts.map((acc) => (
            <TreeNode
              key={acc.id}
              account={acc}
              expandedIds={expandedIds}
              onToggle={handleToggle}
              onSelect={handleSelect}
              selectedId={selectedAccount?.id ?? null}
              searchQuery={debouncedSearch}
              depth={0}
            />
          ))}
        </div>
      )}
    </div>
  );

  // ── Render: Detail / Form Content ──

  const renderDetail = () => {
    if (!selectedAccount) {
      return (
        <div className="flex h-full items-center justify-center">
          <div className="text-center">
            <FileText className="mx-auto h-10 w-10 text-secondary-200" />
            <p className="mt-2 text-sm text-secondary-500">Select an account to view details</p>
          </div>
        </div>
      );
    }

    return (
      <AccountDetailPanel
        account={selectedAccount}
        onEdit={() => handleEdit(selectedAccount)}
        onDelete={() => handleDelete(selectedAccount)}
        onAddChild={() => handleAddChild(selectedAccount)}
        isDeleting={deleteLoading}
      />
    );
  };

  // ── Render: Main ──

  return (
    <div className="h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between border-b border-secondary-200 px-4 py-3">
        <h1 className="text-lg font-bold text-secondary-900 md:text-xl">Chart of Accounts</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowImportOverlay(true)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-secondary-300 px-3 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-50"
            title="Import CSV"
          >
            <Upload className="h-4 w-4" />
            <span className="hidden sm:inline">Import</span>
          </button>
          <button
            onClick={() => setShowAssignmentModal(true)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-secondary-300 px-3 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-50"
            title="Company Assignment"
          >
            <Building2 className="h-4 w-4" />
            <span className="hidden sm:inline">Assign</span>
          </button>
          <button
            onClick={handleCreate}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary-600 px-3 py-2 text-sm font-medium text-white hover:bg-primary-700"
          >
            <Plus className="h-4 w-4" />
            <span className="hidden sm:inline">Add Account</span>
          </button>
        </div>
      </div>

      {/* Mobile: Show either tree or detail */}
      {isMobile && (
        <div className="h-[calc(100vh-120px)] overflow-y-auto">
          {showMobileDetail ? (
            <div className="p-4">
              {/* Back button */}
              <button
                onClick={() => setShowMobileDetail(false)}
                className="mb-3 flex items-center gap-1 text-sm text-secondary-500 hover:text-secondary-900"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to Accounts
              </button>
              {renderDetail()}
            </div>
          ) : (
            <div className="p-4">{renderTree()}</div>
          )}
        </div>
      )}

      {/* Desktop: Split pane */}
      {!isMobile && (
        <div className="flex h-[calc(100vh-120px)]">
          {/* Left: Tree */}
          <div className="w-[380px] shrink-0 overflow-y-auto border-r border-secondary-200 p-4">
            {renderTree()}
          </div>

          {/* Right: Detail */}
          <div className="flex-1 overflow-y-auto p-6">{renderDetail()}</div>
        </div>
      )}

      {/* Create/Edit Modal */}
      {showCreateModal && (
        <AccountFormModal
          accounts={accounts}
          editingAccount={editingAccount}
          defaultParentId={creatingChildOf?.id}
          onClose={() => {
            setShowCreateModal(false);
            setEditingAccount(null);
            setCreatingChildOf(null);
          }}
          onDone={handleRefresh}
        />
      )}

      {/* Company Assignment Modal */}
      {showAssignmentModal && (
        <CompanyAssignmentModal
          onClose={() => setShowAssignmentModal(false)}
          onDone={handleRefresh}
        />
      )}

      {/* CSV Import Overlay */}
      {showImportOverlay && (
        <CsvImportOverlay
          onClose={() => setShowImportOverlay(false)}
          onDone={handleRefresh}
        />
      )}
    </div>
  );
}
