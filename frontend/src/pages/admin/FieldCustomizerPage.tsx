import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useIsMobile } from "@/hooks/useIsMobile";
import { useConfirm } from "@/components/ui/ConfirmDialog";
import api from "@/lib/api";
import { ArrowLeft, Plus, Trash2, Loader2, Search, GripVertical } from "lucide-react";

interface PageConfig {
  id: string;
  page_key: string;
  page_title: string;
  page_type: string;
  module: string;
  entity_model: string;
  api_endpoint: string;
}

interface PageConfigField {
  id: string;
  field_name: string;
  is_custom: boolean;
  label: string;
  field_type: string;
  required: boolean;
  hidden: boolean;
  sort_order: number;
  default_value: string;
  options: { label: string; value: string }[];
  placeholder: string;
  help_text: string;
}

interface DetailPageConfig extends PageConfig {
  fields: PageConfigField[];
}

const FIELD_TYPES = [
  { value: "text", label: "Text" },
  { value: "textarea", label: "Textarea" },
  { value: "number", label: "Number" },
  { value: "decimal", label: "Decimal" },
  { value: "email", label: "Email" },
  { value: "date", label: "Date" },
  { value: "datetime", label: "DateTime" },
  { value: "select", label: "Select (Dropdown)" },
  { value: "multi_select", label: "Multi Select" },
  { value: "checkbox", label: "Checkbox" },
  { value: "toggle", label: "Toggle" },
];

const MODULE_LABELS: Record<string, string> = {
  admin: "Administration",
  financial: "Financial",
  scm: "Supply Chain",
  crm: "CRM",
  hrm: "HRM",
  mrp: "MRP",
};

const FORM_FIELD_TYPES = [
  "text",
  "number",
  "decimal",
  "date",
  "datetime",
  "select",
  "multi_select",
  "checkbox",
  "toggle",
  "textarea",
  "email",
];

export default function FieldCustomizerPage() {
  const isMobile = useIsMobile();
  const queryClient = useQueryClient();
  const { confirm } = useConfirm();

  const [selectedPage, setSelectedPage] = useState<string | null>(null);
  const [selectedField, setSelectedField] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [moduleFilter, setModuleFilter] = useState("");
  const [editPanel, setEditPanel] = useState(false);
  const [saveError, setSaveError] = useState("");

  // Page list
  const { data: pages = [], isLoading: pagesLoading } = useQuery({
    queryKey: ["page-configs"],
    queryFn: async (): Promise<PageConfig[]> => {
      const { data } = await api.get("/core/page-configs/");
      return data?.results ?? data ?? [];
    },
  });

  // Page detail (with fields)
  const { data: pageDetail, isLoading: fieldsLoading } = useQuery({
    queryKey: ["page-config", selectedPage],
    queryFn: async (): Promise<DetailPageConfig> => {
      const { data } = await api.get(`/core/page-configs/${selectedPage}/`);
      return data;
    },
    enabled: !!selectedPage,
  });

  const fields = pageDetail?.fields ?? [];
  const standardFields = fields.filter((f) => !f.is_custom);
  const customFields = fields.filter((f) => f.is_custom);
  const selectedFieldData = fields.find((f) => f.id === selectedField) ?? null;
  const isCustomField = selectedFieldData?.is_custom ?? false;

  // Form state for editing
  const [fieldLabel, setFieldLabel] = useState("");
  const [fieldName, setFieldName] = useState("");
  const [fieldType, setFieldType] = useState("text");
  const [fieldRequired, setFieldRequired] = useState(false);
  const [fieldHidden, setFieldHidden] = useState(false);
  const [fieldSortOrder, setFieldSortOrder] = useState(0);
  const [fieldDefault, setFieldDefault] = useState("");
  const [fieldOptions, setFieldOptions] = useState("");
  const [fieldPlaceholder, setFieldPlaceholder] = useState("");

  // ── Mutations ─────────────────────────────────

  const addMutation = useMutation({
    mutationFn: async (data: Record<string, unknown>) => {
      await api.post(`/core/page-configs/${selectedPage}/fields/`, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["page-config", selectedPage] });
      closeEditPanel();
    },
    onError: (e: Error) => setSaveError(e.message),
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Record<string, unknown> }) => {
      await api.put(`/core/page-configs/${selectedPage}/fields/${id}/`, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["page-config", selectedPage] });
      closeEditPanel();
    },
    onError: (e: Error) => setSaveError(e.message),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/core/page-configs/${selectedPage}/fields/${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["page-config", selectedPage] });
      setSelectedField(null);
    },
  });

  // ── Helpers ────────────────────────────────────

  const filteredPages = useMemo(() => {
    return pages
      .filter((p) => {
        if (
          search &&
          !p.page_title.toLowerCase().includes(search.toLowerCase()) &&
          !p.page_key.toLowerCase().includes(search.toLowerCase())
        )
          return false;
        if (moduleFilter && p.module !== moduleFilter) return false;
        return true;
      })
      .sort(
        (a, b) =>
          a.module.localeCompare(b.module) || a.page_title.localeCompare(b.page_title)
      );
  }, [pages, search, moduleFilter]);

  const moduleList = useMemo(() => {
    return [...new Set(pages.map((p) => p.module))].sort();
  }, [pages]);

  function loadFieldIntoForm(f: PageConfigField) {
    setFieldLabel(f.label);
    setFieldName(f.field_name);
    setFieldType(f.field_type);
    setFieldRequired(f.required);
    setFieldHidden(f.hidden);
    setFieldSortOrder(f.sort_order);
    setFieldDefault(f.default_value ?? "");
    setFieldOptions(f.options?.map((o) => o.label).join("\n") ?? "");
    setFieldPlaceholder(f.placeholder ?? "");
  }

  function resetForm() {
    setFieldLabel("");
    setFieldName("");
    setFieldType("text");
    setFieldRequired(false);
    setFieldHidden(false);
    setFieldSortOrder(0);
    setFieldDefault("");
    setFieldOptions("");
    setFieldPlaceholder("");
  }

  function openEditField(f: PageConfigField) {
    setSelectedField(f.id);
    loadFieldIntoForm(f);
    setEditPanel(true);
  }

  function openAddField() {
    setSelectedField(null);
    resetForm();
    setEditPanel(true);
  }

  function closeEditPanel() {
    setEditPanel(false);
    setSelectedField(null);
    resetForm();
  }

  async function handleSave() {
    setSaveError("");
    if (!fieldLabel.trim()) return;
    if (!selectedFieldData && !fieldName.trim()) {
      setSaveError("Field Name is required for custom fields.");
      return;
    }
    const isSaving = addMutation.isPending || updateMutation.isPending;
    if (isSaving) return;
    const data: Record<string, unknown> = {
      label: fieldLabel.trim(),
      field_type: fieldType,
      required: fieldRequired,
      hidden: fieldHidden,
      sort_order: fieldSortOrder,
      default_value: fieldDefault,
      placeholder: fieldPlaceholder,
    };
    if (fieldType === "select" || fieldType === "multi_select") {
      data.options = fieldOptions
        .split("\n")
        .filter(Boolean)
        .map((o) => ({ label: o.trim(), value: o.trim() }));
      data.options_source = "static";
    }
    if (!selectedFieldData || selectedFieldData.is_custom) {
      data.field_name = fieldName.trim();
      data.is_custom = true;
    }
    if (selectedFieldData) {
      if (selectedFieldData.is_custom || isCustomField) {
        updateMutation.mutate({ id: selectedField!, data });
      } else {
        const mutable: Record<string, unknown> = {
          label: data.label,
          required: data.required,
          hidden: data.hidden,
          sort_order: data.sort_order,
          default_value: data.default_value,
          placeholder: data.placeholder,
        };
        if (data.options) mutable.options = data.options;
        if (data.options_source) mutable.options_source = data.options_source;
        updateMutation.mutate({ id: selectedField!, data: mutable });
      }
    } else {
      addMutation.mutate(data);
    }
  }

  async function handleDelete(field: PageConfigField) {
    if (!field.is_custom) return;
    // Check if field has data in any record
    const { data: usage } = await api.get(
      `/core/page-configs/${selectedPage}/fields/${field.id}/usage/`
    );
    if (usage.used) {
      await confirm({
        title: "Cannot Delete",
        message: `"${field.label}" has data in ${usage.count} record(s). Remove the data first before deleting the field.`,
        variant: "danger",
        confirmText: "OK",
      });
      return;
    }
    const ok = await confirm({
      title: "Delete Field",
      message: `Delete custom field "${field.label}"?`,
      variant: "danger",
      confirmText: "Delete",
    });
    if (ok) deleteMutation.mutate(field.id);
  }

  // ── Render: page list ──────────────────────────

  if (!selectedPage) {
    return (
      <div className="p-4 md:p-6">
        <h1 className="mb-4 text-xl font-bold text-secondary-900">Field Customizer</h1>
        <p className="mb-4 text-sm text-secondary-500">
          Select a page to customize its fields.
        </p>

        <div className="mb-4 flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-secondary-400" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search pages..."
              className="w-full rounded-lg border border-secondary-300 py-2 pl-9 pr-3 text-sm focus:border-primary-500 focus:outline-none"
            />
          </div>
          <select
            value={moduleFilter}
            onChange={(e) => setModuleFilter(e.target.value)}
            className="rounded-lg border border-secondary-300 px-3 py-2 text-sm"
          >
            <option value="">All Modules</option>
            {moduleList.map((m) => (
              <option key={m} value={m}>
                {MODULE_LABELS[m] ?? m}
              </option>
            ))}
          </select>
        </div>

        {pagesLoading ? (
          <div className="flex h-32 items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-primary-500" />
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {filteredPages.map((p) => (
              <button
                key={p.id}
                onClick={() => setSelectedPage(p.page_key)}
                className="rounded-lg border border-secondary-200 bg-white p-4 text-left hover:border-primary-400 hover:shadow-sm transition-all"
              >
                <div className="text-sm font-semibold text-secondary-900">
                  {p.page_title}
                </div>
                <div className="mt-1 text-xs text-secondary-500">{p.page_key}</div>
                <div className="mt-2 flex items-center gap-2">
                  <span className="rounded-full bg-secondary-100 px-2 py-0.5 text-xs text-secondary-600">
                    {MODULE_LABELS[p.module] ?? p.module}
                  </span>
                  <span className="text-xs text-secondary-400">{p.page_type}</span>
                </div>
              </button>
            ))}
            {filteredPages.length === 0 && (
              <div className="col-span-full py-8 text-center text-sm text-secondary-400">
                No pages found.
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  // ── Render: field list + edit panel ─────────────

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-secondary-200 px-4 py-3 md:px-6">
        <button
          onClick={() => {
            setSelectedPage(null);
            setSelectedField(null);
            setEditPanel(false);
          }}
          className="inline-flex items-center gap-1 text-sm font-medium text-secondary-600 hover:text-secondary-900"
        >
          <ArrowLeft className="h-4 w-4" /> Back
        </button>
        <h1 className="text-lg font-bold text-secondary-900">
          {pageDetail?.page_title}
        </h1>
        <span className="rounded-full bg-secondary-100 px-2 py-0.5 text-xs text-secondary-600">
          {pageDetail?.page_key}
        </span>
        <div className="flex-1" />
        <button
          onClick={openAddField}
          className="inline-flex items-center gap-1 rounded-lg bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700"
        >
          <Plus className="h-4 w-4" /> Add Custom Field
        </button>
      </div>

      {/* Body */}
      <div className={`flex flex-1 overflow-hidden ${isMobile ? "flex-col" : ""}`}>
        {/* Field list */}
        <div
          className={`overflow-y-auto border-r border-secondary-200 ${isMobile ? "h-1/2" : "w-1/2"}`}
        >
          {fieldsLoading ? (
            <div className="flex h-32 items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-primary-500" />
            </div>
          ) : (
            <div className="divide-y divide-secondary-100">
              {standardFields.map((f) => (
                <button
                  key={f.id}
                  onClick={() => openEditField(f)}
                  className={`flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-secondary-50 transition-colors ${selectedField === f.id ? "bg-primary-50" : ""}`}
                >
                  <GripVertical className="h-4 w-4 shrink-0 text-secondary-300" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-secondary-900">
                        {f.label || "\u2014"}
                      </span>
                      <span className="rounded bg-secondary-100 px-1.5 py-0.5 text-xs text-secondary-500">
                        {f.field_type}
                      </span>
                      {f.required && (
                        <span className="text-xs text-danger-500">required</span>
                      )}
                    </div>
                    <div className="text-xs text-secondary-400">{f.field_name}</div>
                  </div>
                </button>
              ))}
              {customFields.length > 0 && (
                <div className="px-4 py-2 text-xs font-semibold uppercase tracking-wider text-secondary-400 bg-secondary-50">
                  Custom Fields
                </div>
              )}
              {customFields.map((f) => (
                <button
                  key={f.id}
                  onClick={() => openEditField(f)}
                  className={`flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-secondary-50 transition-colors ${selectedField === f.id ? "bg-primary-50" : ""}`}
                >
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(f);
                    }}
                    className="shrink-0 rounded p-1 text-secondary-400 hover:bg-danger-50 hover:text-danger-600"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-primary-700">
                        {f.label || "\u2014"}
                      </span>
                      <span className="rounded bg-primary-50 px-1.5 py-0.5 text-xs text-primary-600">
                        {f.field_type}
                      </span>
                      {f.required && (
                        <span className="text-xs text-danger-500">required</span>
                      )}
                    </div>
                    <div className="text-xs text-secondary-400">{f.field_name}</div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Edit panel */}
        <div
          className={`overflow-y-auto ${isMobile ? "flex-1" : "w-1/2"} ${!editPanel ? "hidden md:flex md:items-center md:justify-center" : ""}`}
        >
          {!editPanel ? (
            <div className="text-sm text-secondary-400">
              Select a field to edit, or click "Add Custom Field".
            </div>
          ) : (
            <div className="p-4 md:p-6 space-y-4">
              <h2 className="text-base font-semibold text-secondary-900">
                {selectedFieldData?.is_custom || !selectedFieldData
                  ? "Custom Field"
                  : "Standard Field"}
              </h2>

              {(selectedFieldData?.is_custom || !selectedFieldData) && (
                <FieldInput
                  label="Field Name"
                  value={fieldName}
                  onChange={setFieldName}
                  placeholder="e.g. color"
                />
              )}
              <FieldInput
                label="Label"
                value={fieldLabel}
                onChange={setFieldLabel}
                placeholder="e.g. Color"
              />
              {(selectedFieldData?.is_custom || !selectedFieldData) && (
                <div>
                  <label className="mb-1 block text-xs font-medium text-secondary-700">
                    Field Type
                  </label>
                  <select
                    value={fieldType}
                    onChange={(e) => setFieldType(e.target.value)}
                    className="w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
                  >
                    {FORM_FIELD_TYPES.map((ft) => (
                      <option key={ft} value={ft}>
                        {FIELD_TYPES.find((t) => t.value === ft)?.label ?? ft}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <div className="flex gap-4">
                <label className="flex items-center gap-2 text-sm text-secondary-700">
                  <input
                    type="checkbox"
                    checked={fieldRequired}
                    onChange={(e) => setFieldRequired(e.target.checked)}
                    className="rounded border-secondary-300 text-primary-600"
                  />
                  Required
                </label>
                <label className="flex items-center gap-2 text-sm text-secondary-700">
                  <input
                    type="checkbox"
                    checked={fieldHidden}
                    onChange={(e) => setFieldHidden(e.target.checked)}
                    className="rounded border-secondary-300 text-primary-600"
                  />
                  Hidden
                </label>
              </div>
              <FieldInput
                label="Sort Order"
                value={String(fieldSortOrder)}
                onChange={(v) => setFieldSortOrder(Number(v) || 0)}
                type="number"
              />
              <FieldInput
                label="Default Value"
                value={fieldDefault}
                onChange={setFieldDefault}
                placeholder="Optional"
              />
              <FieldInput
                label="Placeholder"
                value={fieldPlaceholder}
                onChange={setFieldPlaceholder}
                placeholder="Optional"
              />
              {(fieldType === "select" || fieldType === "multi_select") && (
                <div>
                  <label className="mb-1 block text-xs font-medium text-secondary-700">
                    Options (one per line)
                  </label>
                  <textarea
                    value={fieldOptions}
                    onChange={(e) => setFieldOptions(e.target.value)}
                    rows={4}
                    placeholder="Red&#10;Blue&#10;Green"
                    className="w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
                  />
                </div>
              )}
              <div className="flex gap-3 pt-2">
                <button
                  onClick={handleSave}
                  disabled={
                    !fieldLabel.trim() ||
                    addMutation.isPending ||
                    updateMutation.isPending
                  }
                  className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
                >
                  {addMutation.isPending || updateMutation.isPending
                    ? "Saving..."
                    : "Save"}
                </button>
                <button
                  onClick={closeEditPanel}
                  className="rounded-lg border border-secondary-300 px-4 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-50"
                >
                  Cancel
                </button>
              </div>
              {saveError && (
                <div className="rounded-md border border-danger-200 bg-danger-50 p-3 text-sm text-danger-700">
                  {saveError}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function FieldInput({
  label,
  value,
  onChange,
  placeholder,
  type,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-secondary-700">
        {label}
      </label>
      <input
        type={type ?? "text"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
      />
    </div>
  );
}
