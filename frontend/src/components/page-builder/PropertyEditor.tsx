import { useState, useCallback } from "react";
import type { PageConfigField } from "@/hooks/usePageConfig";
import { useBuilderStore } from "./builderStore";
import ConditionBuilder from "./ConditionBuilder";
import JSONEditor from "./JSONEditor";
import IconPicker from "./IconPicker";
import ColorPicker from "./ColorPicker";

const fieldTypeOptions = [
  { value: "text", label: "Text" },
  { value: "number", label: "Number" },
  { value: "email", label: "Email" },
  { value: "textarea", label: "Textarea" },
  { value: "select", label: "Select" },
  { value: "multi_select", label: "Multi Select" },
  { value: "autocomplete", label: "Autocomplete" },
  { value: "date", label: "Date" },
  { value: "datetime", label: "DateTime" },
  { value: "time", label: "Time" },
  { value: "toggle", label: "Toggle" },
  { value: "checkbox", label: "Checkbox" },
  { value: "radio", label: "Radio" },
  { value: "file", label: "File" },
  { value: "image", label: "Image" },
  { value: "heading", label: "Heading" },
  { value: "separator", label: "Separator" },
  { value: "readonly_text", label: "Readonly Text" },
  { value: "badge", label: "Badge" },
  { value: "inline_table", label: "Inline Table" },
  { value: "spacer", label: "Spacer" },
];

const dataTypeOptions = [
  { value: "string", label: "String" },
  { value: "number", label: "Number" },
  { value: "boolean", label: "Boolean" },
  { value: "date", label: "Date" },
  { value: "datetime", label: "DateTime" },
  { value: "json", label: "JSON" },
  { value: "array", label: "Array" },
];

const optionsSourceOptions = [
  { value: "manual", label: "Manual" },
  { value: "api", label: "API" },
  { value: "model", label: "Model" },
];

const columnAlignOptions = [
  { value: "left", label: "Left" },
  { value: "center", label: "Center" },
  { value: "right", label: "Right" },
];

type TabKey =
  | "general"
  | "type"
  | "validation"
  | "options"
  | "relationship"
  | "conditional"
  | "table"
  | "inline"
  | "permissions"
  | "ui"
  | "responsive";

const tabs: { key: TabKey; label: string }[] = [
  { key: "general", label: "General" },
  { key: "type", label: "Type & Data" },
  { key: "validation", label: "Validation" },
  { key: "options", label: "Options" },
  { key: "relationship", label: "Relationship" },
  { key: "conditional", label: "Conditional" },
  { key: "table", label: "Table Columns" },
  { key: "inline", label: "Inline Table" },
  { key: "permissions", label: "Permissions" },
  { key: "ui", label: "UI" },
  { key: "responsive", label: "Responsive" },
];

interface PropertyEditorProps {
  open: boolean;
  onClose: () => void;
}

function FieldInput({
  label,
  value,
  onChange,
  type = "text",
  options,
  placeholder,
}: {
  label: string;
  value: string | number | boolean | null | undefined;
  onChange: (val: string) => void;
  type?: "text" | "number" | "select" | "checkbox";
  options?: { value: string; label: string }[];
  placeholder?: string;
}) {
  return (
    <div className="space-y-1">
      <label className="block text-xs font-medium text-secondary-600">{label}</label>
      {type === "select" && options ? (
        <select
          value={String(value ?? "")}
          onChange={(e) => onChange(e.target.value)}
          className="w-full rounded-md border border-secondary-300 px-2 py-1.5 text-xs focus:border-primary-500 focus:outline-none"
        >
          <option value="">---</option>
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      ) : type === "number" ? (
        <input
          type="number"
          value={value == null ? "" : Number(value)}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full rounded-md border border-secondary-300 px-2 py-1.5 text-xs focus:border-primary-500 focus:outline-none"
        />
      ) : (
        <input
          type="text"
          value={String(value ?? "")}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full rounded-md border border-secondary-300 px-2 py-1.5 text-xs focus:border-primary-500 focus:outline-none"
        />
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-3">
      <h4 className="text-xs font-semibold uppercase tracking-wider text-secondary-400">
        {title}
      </h4>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

export default function PropertyEditor({ open, onClose }: PropertyEditorProps) {
  const [activeTab, setActiveTab] = useState<TabKey>("general");
  const selectedFieldId = useBuilderStore((s) => s.selectedFieldId);
  const fields = useBuilderStore((s) => s.fields);
  const updateField = useBuilderStore((s) => s.updateField);

  const field = fields.find((f) => f.id === selectedFieldId);

  const handleChange = useCallback(
    (key: keyof PageConfigField, value: string | number | boolean | Record<string, unknown> | PageConfigField[]) => {
      if (!field) return;
      const parsed = key === "sort_order" || key === "column_order" || key === "desktop_col_span" || key === "mobile_col_span" || key === "col_span"
        ? Number(value)
        : value;
      updateField(field.id, { [key]: parsed });
    },
    [field, updateField]
  );

  if (!field) {
    return (
      <>
        {open && (
          <div className="fixed inset-0 z-30 bg-black/30 md:hidden" onClick={onClose} />
        )}
        <aside
          className={`fixed right-0 top-0 z-40 h-full w-80 shrink-0 border-l border-secondary-200 bg-white transition-transform md:relative md:translate-x-0 ${
            open ? "translate-x-0" : "translate-x-full"
          }`}
        >
          <div className="flex items-center justify-between border-b border-secondary-200 px-4 py-3">
            <h3 className="text-sm font-semibold text-secondary-800">Properties</h3>
            <button onClick={onClose} className="rounded p-1 text-secondary-400 hover:bg-secondary-100 md:hidden" aria-label="Close properties">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div className="flex items-center justify-center p-8 text-sm text-secondary-400">
            Select a field to edit its properties
          </div>
        </aside>
      </>
    );
  }

  return (
    <>
      {open && (
        <div className="fixed inset-0 z-30 bg-black/30 md:hidden" onClick={onClose} />
      )}
      <aside
        className={`fixed right-0 top-0 z-40 h-full w-80 shrink-0 border-l border-secondary-200 bg-white transition-transform md:relative md:translate-x-0 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between border-b border-secondary-200 px-4 py-3">
          <h3 className="text-sm font-semibold text-secondary-800">Properties</h3>
          <button onClick={onClose} className="rounded p-1 text-secondary-400 hover:bg-secondary-100 md:hidden" aria-label="Close properties">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tab bar */}
        <div className="flex overflow-x-auto border-b border-secondary-200">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`shrink-0 px-3 py-2 text-xs font-medium transition-colors ${
                activeTab === tab.key
                  ? "border-b-2 border-primary-500 text-primary-600"
                  : "text-secondary-500 hover:text-secondary-700"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="h-[calc(100%-88px)] overflow-y-auto p-4">
          {activeTab === "general" && (
            <div className="space-y-3">
              <Section title="Basic">
                <FieldInput label="Field Name" value={field.field_name} onChange={(v) => handleChange("field_name", v)} />
                <FieldInput label="Label" value={field.label} onChange={(v) => handleChange("label", v)} />
                <FieldInput label="Placeholder" value={field.placeholder} onChange={(v) => handleChange("placeholder", v)} />
                <FieldInput label="Help Text" value={field.help_text} onChange={(v) => handleChange("help_text", v)} />
                <FieldInput label="Default Value" value={field.default_value} onChange={(v) => handleChange("default_value", v)} />
              </Section>
            </div>
          )}

          {activeTab === "type" && (
            <div className="space-y-3">
              <Section title="Field Configuration">
                <FieldInput
                  label="Field Type"
                  value={field.field_type}
                  onChange={(v) => handleChange("field_type", v)}
                  type="select"
                  options={fieldTypeOptions}
                />
                <FieldInput
                  label="Data Type"
                  value={field.data_type}
                  onChange={(v) => handleChange("data_type", v)}
                  type="select"
                  options={dataTypeOptions}
                />
                <FieldInput label="Width" value={field.width} onChange={(v) => handleChange("width", v)} />
                <FieldInput label="Col Span" value={field.col_span} onChange={(v) => handleChange("col_span", v)} type="number" />
              </Section>
            </div>
          )}

          {activeTab === "validation" && (
            <div className="space-y-3">
              <Section title="Validation Rules">
                <FieldInput label="Required" value={field.required} onChange={(v) => handleChange("required", v === "true")} type="select" options={[{ value: "true", label: "Yes" }, { value: "false", label: "No" }]} />
                <FieldInput label="Readonly" value={field.readonly} onChange={(v) => handleChange("readonly", v === "true")} type="select" options={[{ value: "true", label: "Yes" }, { value: "false", label: "No" }]} />
                <FieldInput label="Disabled" value={field.disabled} onChange={(v) => handleChange("disabled", v === "true")} type="select" options={[{ value: "true", label: "Yes" }, { value: "false", label: "No" }]} />
                <FieldInput label="Hidden" value={field.hidden} onChange={(v) => handleChange("hidden", v === "true")} type="select" options={[{ value: "true", label: "Yes" }, { value: "false", label: "No" }]} />
                <FieldInput label="Min Length" value={field.min_length} onChange={(v) => handleChange("min_length", v)} type="number" />
                <FieldInput label="Max Length" value={field.max_length} onChange={(v) => handleChange("max_length", v)} type="number" />
                <FieldInput label="Min Value" value={field.min_value} onChange={(v) => handleChange("min_value", v)} type="number" />
                <FieldInput label="Max Value" value={field.max_value} onChange={(v) => handleChange("max_value", v)} type="number" />
                <FieldInput label="Pattern (Regex)" value={field.pattern} onChange={(v) => handleChange("pattern", v)} />
                <FieldInput label="Custom Validator" value={field.custom_validator} onChange={(v) => handleChange("custom_validator", v)} />
              </Section>
            </div>
          )}

          {activeTab === "options" && (
            <div className="space-y-3">
              <Section title="Options Source">
                <FieldInput
                  label="Options Source"
                  value={field.options_source}
                  onChange={(v) => handleChange("options_source", v)}
                  type="select"
                  options={optionsSourceOptions}
                />
                {field.options_source === "api" && (
                  <>
                    <FieldInput label="Options API" value={field.options_api} onChange={(v) => handleChange("options_api", v)} />
                    <FieldInput label="Label Field" value={field.options_label_field} onChange={(v) => handleChange("options_label_field", v)} />
                    <FieldInput label="Value Field" value={field.options_value_field} onChange={(v) => handleChange("options_value_field", v)} />
                    <FieldInput label="Group By" value={field.option_group_by} onChange={(v) => handleChange("option_group_by", v)} />
                  </>
                )}
                {field.options_source === "model" && (
                  <>
                    <FieldInput label="Related Entity" value={field.related_entity} onChange={(v) => handleChange("related_entity", v)} />
                    <FieldInput label="Display Field" value={field.related_display} onChange={(v) => handleChange("related_display", v)} />
                  </>
                )}
                {field.options_source === "manual" && (
                  <div className="space-y-1">
                    <label className="block text-xs font-medium text-secondary-600">Options (JSON)</label>
                    <JSONEditor
                      value={JSON.stringify(field.options || [], null, 2)}
                      onChange={(val) => {
                        try {
                          const parsed = JSON.parse(val);
                          handleChange("options", parsed);
                        } catch {
                          // invalid JSON — don't update
                        }
                      }}
                    />
                  </div>
                )}
              </Section>
            </div>
          )}

          {activeTab === "relationship" && (
            <div className="space-y-3">
              <Section title="Entity Relationship">
                <FieldInput label="Related Entity" value={field.related_entity} onChange={(v) => handleChange("related_entity", v)} />
                <FieldInput label="Display Field" value={field.related_display} onChange={(v) => handleChange("related_display", v)} />
                <FieldInput label="Search Config" value={field.related_search ? JSON.stringify(field.related_search) : ""} onChange={(v) => {
                  try { handleChange("related_search", JSON.parse(v)); } catch {}
                }} />
                <div className="space-y-1">
                  <label className="block text-xs font-medium text-secondary-600">Related Fields</label>
                  <JSONEditor
                    value={JSON.stringify(field.related_fields, null, 2)}
                    onChange={(val) => {
                      try { handleChange("related_fields", JSON.parse(val)); } catch {}
                    }}
                  />
                </div>
              </Section>
            </div>
          )}

          {activeTab === "conditional" && (
            <div className="space-y-3">
              <Section title="Conditional Display">
                <ConditionBuilder
                  value={(field.show_when as Record<string, unknown>) || {}}
                  onChange={(v) => handleChange("show_when", v as Record<string, unknown>)}
                />
              </Section>
              <Section title="Depends On">
                <ConditionBuilder
                  value={(field.depends_on as Record<string, unknown>) || {}}
                  onChange={(v) => handleChange("depends_on", v as Record<string, unknown>)}
                />
              </Section>
            </div>
          )}

          {activeTab === "table" && (
            <div className="space-y-3">
              <Section title="Column Settings">
                <FieldInput label="Is Column" value={field.is_column} onChange={(v) => handleChange("is_column", v === "true")} type="select" options={[{ value: "true", label: "Yes" }, { value: "false", label: "No" }]} />
                <FieldInput label="Column Order" value={field.column_order} onChange={(v) => handleChange("column_order", v)} type="number" />
                <FieldInput label="Column Width" value={field.column_width} onChange={(v) => handleChange("column_width", v)} />
                <FieldInput label="Column Align" value={field.column_align} onChange={(v) => handleChange("column_align", v)} type="select" options={columnAlignOptions} />
                <FieldInput label="Sortable" value={field.sortable} onChange={(v) => handleChange("sortable", v === "true")} type="select" options={[{ value: "true", label: "Yes" }, { value: "false", label: "No" }]} />
                <FieldInput label="Filterable" value={field.filterable} onChange={(v) => handleChange("filterable", v === "true")} type="select" options={[{ value: "true", label: "Yes" }, { value: "false", label: "No" }]} />
                <FieldInput label="Searchable" value={field.searchable} onChange={(v) => handleChange("searchable", v === "true")} type="select" options={[{ value: "true", label: "Yes" }, { value: "false", label: "No" }]} />
                <FieldInput label="Aggregate" value={field.aggregate} onChange={(v) => handleChange("aggregate", v)} />
                <FieldInput label="Render As" value={field.render_as} onChange={(v) => handleChange("render_as", v)} />
              </Section>
            </div>
          )}

          {activeTab === "inline" && (
            <div className="space-y-3">
              <Section title="Inline Table">
                <FieldInput label="Line Entity" value={field.line_entity} onChange={(v) => handleChange("line_entity", v)} />
                <div className="space-y-1">
                  <label className="block text-xs font-medium text-secondary-600">Line Fields</label>
                  <JSONEditor
                    value={JSON.stringify(field.line_fields, null, 2)}
                    onChange={(val) => {
                      try { handleChange("line_fields", JSON.parse(val)); } catch {}
                    }}
                  />
                </div>
              </Section>
            </div>
          )}

          {activeTab === "permissions" && (
            <div className="space-y-3">
              <Section title="Access Control">
                <FieldInput label="Read Permission" value={field.permission_read} onChange={(v) => handleChange("permission_read", v)} />
                <FieldInput label="Write Permission" value={field.permission_write} onChange={(v) => handleChange("permission_write", v)} />
              </Section>
            </div>
          )}

          {activeTab === "ui" && (
            <div className="space-y-3">
              <Section title="UI Customization">
                <div className="space-y-1">
                  <label className="block text-xs font-medium text-secondary-600">Icon</label>
                  <IconPicker value={field.icon} onChange={(v) => handleChange("icon", v)} />
                </div>
                <FieldInput label="Prefix" value={field.prefix} onChange={(v) => handleChange("prefix", v)} />
                <FieldInput label="Suffix" value={field.suffix} onChange={(v) => handleChange("suffix", v)} />
                <FieldInput label="Format" value={field.format} onChange={(v) => handleChange("format", v)} />
                <div className="space-y-1">
                  <label className="block text-xs font-medium text-secondary-600">Badge Color</label>
                  <ColorPicker
                    value={field.badge_color}
                    onChange={(v) => handleChange("badge_color", v)}
                  />
                </div>
                <FieldInput label="CSS Class" value={field.css_class} onChange={(v) => handleChange("css_class", v)} />
              </Section>
            </div>
          )}

          {activeTab === "responsive" && (
            <div className="space-y-3">
              <Section title="Responsive Settings">
                <FieldInput label="Show on Desktop" value={field.show_on_desktop} onChange={(v) => handleChange("show_on_desktop", v === "true")} type="select" options={[{ value: "true", label: "Yes" }, { value: "false", label: "No" }]} />
                <FieldInput label="Show on Mobile" value={field.show_on_mobile} onChange={(v) => handleChange("show_on_mobile", v === "true")} type="select" options={[{ value: "true", label: "Yes" }, { value: "false", label: "No" }]} />
                <FieldInput label="Desktop Col Span" value={field.desktop_col_span} onChange={(v) => handleChange("desktop_col_span", v)} type="number" />
                <FieldInput label="Mobile Col Span" value={field.mobile_col_span} onChange={(v) => handleChange("mobile_col_span", v)} type="number" />
                <FieldInput label="Mobile Render As" value={field.mobile_render_as} onChange={(v) => handleChange("mobile_render_as", v)} />
              </Section>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
