interface ViewSwitcherProps {
  view: "table" | "chart";
  onChange: (view: "table" | "chart") => void;
}

export default function ViewSwitcher({ view, onChange }: ViewSwitcherProps) {
  return (
    <div className="inline-flex rounded-md border border-secondary-300 overflow-hidden">
      <button
        onClick={() => onChange("table")}
        className={`px-3 py-1.5 text-sm font-medium ${
          view === "table"
            ? "bg-primary-600 text-white"
            : "bg-white text-secondary-600 hover:bg-secondary-50"
        }`}
      >
        Table
      </button>
      <button
        onClick={() => onChange("chart")}
        className={`px-3 py-1.5 text-sm font-medium ${
          view === "chart"
            ? "bg-primary-600 text-white"
            : "bg-white text-secondary-600 hover:bg-secondary-50"
        }`}
      >
        Chart
      </button>
    </div>
  );
}
