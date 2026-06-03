import { useState } from "react";

const icons = [
  { value: "", label: "None" },
  { value: "user", label: "👤" },
  { value: "email", label: "✉️" },
  { value: "phone", label: "📞" },
  { value: "calendar", label: "📅" },
  { value: "clock", label: "🕐" },
  { value: "dollar", label: "💰" },
  { value: "percent", label: "💯" },
  { value: "location", label: "📍" },
  { value: "note", label: "📝" },
  { value: "search", label: "🔍" },
  { value: "filter", label: "🔎" },
  { value: "download", label: "⬇️" },
  { value: "upload", label: "⬆️" },
  { value: "attachment", label: "📎" },
  { value: "image", label: "🖼️" },
  { value: "tag", label: "🏷️" },
  { value: "star", label: "⭐" },
  { value: "heart", label: "❤️" },
  { value: "lock", label: "🔒" },
  { value: "globe", label: "🌐" },
  { value: "building", label: "🏢" },
  { value: "home", label: "🏠" },
  { value: "settings", label: "⚙️" },
  { value: "bell", label: "🔔" },
  { value: "chart", label: "📊" },
  { value: "print", label: "🖨️" },
  { value: "info", label: "ℹ️" },
  { value: "warning", label: "⚠️" },
  { value: "check", label: "✅" },
  { value: "close", label: "❌" },
];

interface IconPickerProps {
  value: string;
  onChange: (value: string) => void;
}

export default function IconPicker({ value, onChange }: IconPickerProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");

  const filtered = icons.filter(
    (icon) =>
      !search ||
      icon.value.toLowerCase().includes(search.toLowerCase()) ||
      icon.label.includes(search)
  );

  const selected = icons.find((i) => i.value === value);

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 rounded-md border border-secondary-300 px-2 py-1.5 text-xs hover:border-secondary-400 focus:outline-none"
      >
        {selected && selected.value ? (
          <>
            <span className="text-base">{selected.label}</span>
            <span className="text-secondary-500">{selected.value}</span>
          </>
        ) : (
          <span className="text-secondary-400">Select icon...</span>
        )}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute left-0 top-full z-20 mt-1 w-56 rounded-md border border-secondary-200 bg-white shadow-lg">
            <div className="border-b border-secondary-100 p-2">
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search icons..."
                className="w-full rounded border border-secondary-200 px-2 py-1 text-xs focus:border-primary-500 focus:outline-none"
                autoFocus
              />
            </div>
            <div className="grid grid-cols-5 gap-1 p-2">
              {filtered.map((icon) => (
                <button
                  key={icon.value}
                  onClick={() => {
                    onChange(icon.value);
                    setOpen(false);
                    setSearch("");
                  }}
                  className={`flex aspect-square items-center justify-center rounded-md text-lg transition-colors ${
                    value === icon.value
                      ? "bg-primary-100 ring-1 ring-primary-400"
                      : "hover:bg-secondary-100"
                  }`}
                  title={icon.value || "None"}
                >
                  {icon.value ? icon.label : "—"}
                </button>
              ))}
            </div>
            {filtered.length === 0 && (
              <p className="p-3 text-center text-xs text-secondary-400">No icons found</p>
            )}
          </div>
        </>
      )}
    </div>
  );
}
