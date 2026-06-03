import { create } from "zustand";
import type { PageConfig, PageConfigField } from "@/hooks/usePageConfig";

interface BuilderState {
  fields: PageConfigField[];
  selectedFieldId: string | null;
  config: Partial<PageConfig>;
  isDirty: boolean;
  previewMode: "desktop" | "mobile";

  addField: (field: PageConfigField, afterId?: string) => void;
  updateField: (id: string, updates: Partial<PageConfigField>) => void;
  removeField: (id: string) => void;
  reorderFields: (fromIndex: number, toIndex: number) => void;
  selectField: (id: string | null) => void;
  setConfig: (config: Partial<PageConfig>) => void;
  setFields: (fields: PageConfigField[]) => void;
  setPreviewMode: (mode: "desktop" | "mobile") => void;
  markClean: () => void;
  reset: () => void;
}

let fieldCounter = 0;

function makeId(): string {
  fieldCounter += 1;
  return `field_${Date.now()}_${fieldCounter}`;
}

function createDefaultField(
  fieldType: string,
  base: Partial<PageConfigField> = {}
): PageConfigField {
  const id = makeId();
  return {
    id,
    field_name: `field_${id}`,
    label: "",
    placeholder: "",
    help_text: "",
    field_type: fieldType,
    data_type: "string",
    required: false,
    readonly: false,
    hidden: false,
    disabled: false,
    default_value: "",
    sort_order: 0,
    group_name: "",
    col_span: 6,
    width: "100%",
    show_on_desktop: true,
    show_on_mobile: true,
    desktop_col_span: 6,
    mobile_col_span: 12,
    mobile_render_as: "",
    min_length: null,
    max_length: null,
    min_value: null,
    max_value: null,
    pattern: "",
    custom_validator: "",
    options_source: "manual",
    options: [],
    options_api: "",
    options_label_field: "label",
    options_value_field: "value",
    option_group_by: "",
    related_entity: "",
    related_display: "",
    related_search: {},
    related_fields: [],
    show_when: {},
    depends_on: {},
    is_column: false,
    column_order: 0,
    column_width: "150px",
    column_align: "left",
    sortable: false,
    filterable: false,
    searchable: false,
    aggregate: "",
    render_as: "",
    parent_field: null,
    line_entity: "",
    line_fields: [],
    permission_read: "",
    permission_write: "",
    icon: "",
    prefix: "",
    suffix: "",
    format: "",
    badge_color: {},
    css_class: "",
    ...base,
  };
}

export { createDefaultField, makeId };

export const useBuilderStore = create<BuilderState>((set) => ({
  fields: [],
  selectedFieldId: null,
  config: {},
  isDirty: false,
  previewMode: "desktop",

  addField: (field, afterId) =>
    set((state) => {
      const newField = { ...field, id: field.id || makeId() };
      if (!afterId) {
        return { fields: [...state.fields, newField], isDirty: true };
      }
      const idx = state.fields.findIndex((f) => f.id === afterId);
      if (idx === -1) return { fields: [...state.fields, newField], isDirty: true };
      const copy = [...state.fields];
      copy.splice(idx + 1, 0, newField);
      return { fields: copy, isDirty: true };
    }),

  updateField: (id, updates) =>
    set((state) => ({
      fields: state.fields.map((f) =>
        f.id === id ? { ...f, ...updates } : f
      ),
      isDirty: true,
    })),

  removeField: (id) =>
    set((state) => ({
      fields: state.fields.filter((f) => f.id !== id),
      selectedFieldId:
        state.selectedFieldId === id ? null : state.selectedFieldId,
      isDirty: true,
    })),

  reorderFields: (fromIndex, toIndex) =>
    set((state) => {
      const copy = [...state.fields];
      const [moved] = copy.splice(fromIndex, 1);
      copy.splice(toIndex, 0, moved);
      return { fields: copy, isDirty: true };
    }),

  selectField: (id) => set({ selectedFieldId: id }),

  setConfig: (config) => set({ config, isDirty: true }),

  setFields: (fields) => set({ fields, isDirty: false }),

  setPreviewMode: (mode) => set({ previewMode: mode }),

  markClean: () => set({ isDirty: false }),

  reset: () =>
    set({
      fields: [],
      selectedFieldId: null,
      config: {},
      isDirty: false,
      previewMode: "desktop",
    }),
}));
