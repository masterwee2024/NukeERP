import { useState, useRef, useEffect } from "react";
import { useOptionsResolver } from "@/hooks/useOptionsResolver";
import type { DynamicFieldProps } from "./types";

export default function AutocompleteField({
  field,
  value,
  onChange,
  error,
  disabled,
}: DynamicFieldProps) {
  const { options, loading } = useOptionsResolver(field);
  const [search, setSearch] = useState(() => {
    const found = options.find((o) => o.value === value);
    return found ? found.label : String(value ?? "");
  });
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const filtered = options.filter((opt) =>
    opt.label.toLowerCase().includes(search.toLowerCase())
  );

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function handleSelect(opt: { label: string; value: string }) {
    setSearch(opt.label);
    onChange(field.field_name, opt.value);
    setOpen(false);
  }

  return (
    <div className="space-y-1 relative" ref={ref}>
      <label className="block text-sm font-medium text-secondary-700">
        {field.label}
        {field.required && <span className="text-danger-500 ml-0.5">*</span>}
      </label>
      <input
        type="text"
        value={search}
        onChange={(e) => {
          setSearch(e.target.value);
          setOpen(true);
          onChange(field.field_name, e.target.value);
        }}
        onFocus={() => setOpen(true)}
        placeholder={field.placeholder}
        disabled={disabled || field.readonly}
        className={`w-full rounded-md border px-3 py-2 text-sm outline-none transition-colors ${
          error
            ? "border-danger-500 focus:border-danger-500"
            : "border-secondary-300 focus:border-primary-500"
        } ${disabled || field.readonly ? "bg-secondary-50 text-secondary-400" : "bg-white"}`}
      />
      {open && !disabled && !field.readonly && (
        <div className="absolute z-10 mt-1 max-h-48 w-full overflow-y-auto rounded-md border border-secondary-200 bg-white shadow-lg">
          {loading && (
            <div className="px-3 py-2 text-sm text-secondary-400">Loading...</div>
          )}
          {!loading && filtered.length === 0 && (
            <div className="px-3 py-2 text-sm text-secondary-400">No results</div>
          )}
          {!loading &&
            filtered.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => handleSelect(opt)}
                className={`w-full px-3 py-2 text-left text-sm hover:bg-primary-50 ${
                  opt.value === value
                    ? "bg-primary-50 font-medium text-primary-700"
                    : "text-secondary-700"
                }`}
              >
                {opt.label}
              </button>
            ))}
        </div>
      )}
      {field.help_text && !error && (
        <p className="text-xs text-secondary-400">{field.help_text}</p>
      )}
      {error && <p className="text-xs text-danger-500">{error}</p>}
    </div>
  );
}
