import { useState, useEffect } from "react";

interface FilterPresetManagerProps {
  reportCode: string;
  currentValues: Record<string, unknown>;
  onLoad: (values: Record<string, unknown>) => void;
}

export default function FilterPresetManager({
  reportCode,
  currentValues,
  onLoad,
}: FilterPresetManagerProps) {
  const [presets, setPresets] = useState<Record<string, Record<string, unknown>>>({});
  const [presetName, setPresetName] = useState("");
  const [showSave, setShowSave] = useState(false);

  const storageKey = `report-presets-${reportCode}`;

  useEffect(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) setPresets(JSON.parse(saved));
    } catch {
      // ignore
    }
  }, [storageKey]);

  const savePresets = (newPresets: Record<string, Record<string, unknown>>) => {
    setPresets(newPresets);
    localStorage.setItem(storageKey, JSON.stringify(newPresets));
  };

  const handleSave = () => {
    if (!presetName.trim()) return;
    const newPresets = { ...presets, [presetName.trim()]: currentValues };
    savePresets(newPresets);
    setPresetName("");
    setShowSave(false);
  };

  const handleLoad = (name: string) => {
    const preset = presets[name];
    if (preset) onLoad(preset);
  };

  const handleDelete = (name: string) => {
    const newPresets = { ...presets };
    delete newPresets[name];
    savePresets(newPresets);
  };

  const presetNames = Object.keys(presets);

  return (
    <div className="flex flex-wrap items-center gap-2">
      {presetNames.length > 0 && (
        <select
          className="rounded-md border border-gray-300 px-2 py-2 text-sm"
          value=""
          onChange={(e) => {
            if (e.target.value) handleLoad(e.target.value);
          }}
        >
          <option value="">Load Preset...</option>
          {presetNames.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      )}

      {showSave ? (
        <div className="flex items-center gap-1">
          <input
            type="text"
            value={presetName}
            onChange={(e) => setPresetName(e.target.value)}
            placeholder="Preset name"
            className="rounded-md border border-gray-300 px-2 py-1 text-sm"
          />
          <button
            onClick={handleSave}
            className="rounded-md bg-primary-600 px-2 py-1 text-xs text-white"
          >
            Save
          </button>
          <button onClick={() => setShowSave(false)} className="text-xs text-gray-500">
            Cancel
          </button>
        </div>
      ) : (
        <button
          onClick={() => setShowSave(true)}
          className="text-sm text-primary-600 hover:underline"
        >
          + Save Preset
        </button>
      )}

      {presetNames.length > 0 && (
        <div className="relative group">
          <button className="text-xs text-red-500 hover:underline">Delete Presets</button>
          <div className="absolute right-0 z-10 hidden rounded-md border bg-white shadow-lg group-hover:block">
            {presetNames.map((name) => (
              <button
                key={name}
                onClick={() => handleDelete(name)}
                className="block w-full px-3 py-1 text-left text-xs text-red-600 hover:bg-red-50"
              >
                {name}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
