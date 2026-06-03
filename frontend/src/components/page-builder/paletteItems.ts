export interface PaletteCategory {
  name: string;
  items: PaletteItem[];
}

export interface PaletteItem {
  type: string;
  label: string;
  icon: string;
  defaultFieldType: string;
}

export const paletteCategories: PaletteCategory[] = [
  {
    name: "Input Fields",
    items: [
      { type: "text", label: "Text", icon: "📝", defaultFieldType: "text" },
      { type: "number", label: "Number", icon: "🔢", defaultFieldType: "number" },
      { type: "email", label: "Email", icon: "✉️", defaultFieldType: "email" },
      { type: "password", label: "Password", icon: "🔒", defaultFieldType: "text" },
      { type: "textarea", label: "Textarea", icon: "📄", defaultFieldType: "textarea" },
    ],
  },
  {
    name: "Selection",
    items: [
      { type: "select", label: "Select", icon: "📋", defaultFieldType: "select" },
      { type: "multi_select", label: "Multi Select", icon: "📌", defaultFieldType: "multi_select" },
      { type: "autocomplete", label: "Autocomplete", icon: "🔍", defaultFieldType: "autocomplete" },
      { type: "radio", label: "Radio", icon: "⚪", defaultFieldType: "radio" },
      { type: "checkbox", label: "Checkbox", icon: "✅", defaultFieldType: "checkbox" },
      { type: "toggle", label: "Toggle", icon: "🔘", defaultFieldType: "toggle" },
    ],
  },
  {
    name: "Date/Time",
    items: [
      { type: "date", label: "Date", icon: "📅", defaultFieldType: "date" },
      { type: "datetime", label: "DateTime", icon: "📆", defaultFieldType: "datetime" },
      { type: "time", label: "Time", icon: "🕐", defaultFieldType: "time" },
    ],
  },
  {
    name: "Display",
    items: [
      { type: "heading", label: "Heading", icon: "📰", defaultFieldType: "heading" },
      { type: "separator", label: "Separator", icon: "➖", defaultFieldType: "separator" },
      { type: "readonly_text", label: "Readonly Text", icon: "📖", defaultFieldType: "readonly_text" },
      { type: "badge", label: "Badge", icon: "🏷️", defaultFieldType: "badge" },
    ],
  },
  {
    name: "Upload",
    items: [
      { type: "file", label: "File", icon: "📎", defaultFieldType: "file" },
      { type: "image", label: "Image", icon: "🖼️", defaultFieldType: "image" },
    ],
  },
  {
    name: "Layout",
    items: [
      { type: "group", label: "Group", icon: "📦", defaultFieldType: "group" },
      { type: "tabs", label: "Tabs", icon: "📑", defaultFieldType: "tabs" },
      { type: "spacer", label: "Spacer", icon: "⬜", defaultFieldType: "spacer" },
    ],
  },
  {
    name: "Data",
    items: [
      { type: "inline_table", label: "Inline Table", icon: "📊", defaultFieldType: "inline_table" },
      { type: "related_table", label: "Related Table", icon: "🔗", defaultFieldType: "related_table" },
    ],
  },
];
