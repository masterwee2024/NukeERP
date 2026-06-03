import { useState } from "react";

const presetColors = [
  { label: "Blue", value: { bg: "bg-blue-100", text: "text-blue-800", hex: "#3b82f6" } },
  { label: "Green", value: { bg: "bg-green-100", text: "text-green-800", hex: "#22c55e" } },
  { label: "Red", value: { bg: "bg-red-100", text: "text-red-800", hex: "#ef4444" } },
  { label: "Yellow", value: { bg: "bg-yellow-100", text: "text-yellow-800", hex: "#eab308" } },
  { label: "Purple", value: { bg: "bg-purple-100", text: "text-purple-800", hex: "#a855f7" } },
  { label: "Pink", value: { bg: "bg-pink-100", text: "text-pink-800", hex: "#ec4899" } },
  { label: "Indigo", value: { bg: "bg-indigo-100", text: "text-indigo-800", hex: "#6366f1" } },
  { label: "Orange", value: { bg: "bg-orange-100", text: "text-orange-800", hex: "#f97316" } },
  { label: "Teal", value: { bg: "bg-teal-100", text: "text-teal-800", hex: "#14b8a6" } },
  { label: "Gray", value: { bg: "bg-gray-100", text: "text-gray-800", hex: "#6b7280" } },
  { label: "Slate", value: { bg: "bg-slate-100", text: "text-slate-800", hex: "#64748b" } },
  { label: "Cyan", value: { bg: "bg-cyan-100", text: "text-cyan-800", hex: "#06b6d4" } },
];

interface ColorValue {
  bg: string;
  text: string;
  hex: string;
}

interface ColorPickerProps {
  value: Record<string, string>;
  onChange: (value: Record<string, string>) => void;
}

export default function ColorPicker({ value, onChange }: ColorPickerProps) {
  const [open, setOpen] = useState(false);

  const currentColor = presetColors.find(
    (c) => c.value.hex === (value as unknown as ColorValue)?.hex
  );
  const hexValue = (value as unknown as ColorValue)?.hex || "";

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 rounded-md border border-secondary-300 px-2 py-1.5 text-xs hover:border-secondary-400 focus:outline-none"
      >
        {hexValue ? (
          <>
            <span
              className="inline-block h-4 w-4 rounded"
              style={{ backgroundColor: hexValue }}
            />
            <span className="text-secondary-600">{currentColor?.label || hexValue}</span>
          </>
        ) : (
          <span className="text-secondary-400">Select color...</span>
        )}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute left-0 top-full z-20 mt-1 w-48 rounded-md border border-secondary-200 bg-white p-2 shadow-lg">
            <div className="mb-2 flex items-center gap-2">
              <input
                type="color"
                value={hexValue || "#3b82f6"}
                onChange={(e) => {
                  const color = presetColors.find((c) => c.value.hex === e.target.value);
                  if (color) {
                    onChange(color.value);
                  } else {
                    onChange({ bg: "bg-blue-100", text: "text-blue-800", hex: e.target.value });
                  }
                }}
                className="h-6 w-6 cursor-pointer rounded border-0 p-0"
              />
              <input
                type="text"
                value={hexValue}
                onChange={(e) => {
                  const v = e.target.value;
                  if (/^#[0-9a-fA-F]{6}$/.test(v)) {
                    const color = presetColors.find((c) => c.value.hex === v);
                    if (color) {
                      onChange(color.value);
                    } else {
                      onChange({ bg: "bg-gray-100", text: "text-gray-800", hex: v });
                    }
                  }
                }}
                placeholder="#000000"
                className="flex-1 rounded border border-secondary-200 px-2 py-1 text-xs focus:border-primary-500 focus:outline-none"
              />
            </div>
            <div className="grid grid-cols-6 gap-1">
              {presetColors.map((color) => (
                <button
                  key={color.value.hex}
                  onClick={() => {
                    onChange(color.value);
                    setOpen(false);
                  }}
                  className={`h-6 w-6 rounded-md ${
                    color.value.bg
                  } ring-1 ring-inset ring-secondary-200 transition-transform hover:scale-110 ${
                    hexValue === color.value.hex ? "ring-2 ring-primary-500" : ""
                  }`}
                  title={color.label}
                />
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
