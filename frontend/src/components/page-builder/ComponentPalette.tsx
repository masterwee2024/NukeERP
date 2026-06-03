import { useState } from "react";
import { useDraggable } from "@dnd-kit/core";
import { paletteCategories, type PaletteItem } from "./paletteItems";

function DraggablePaletteItem({ item }: { item: PaletteItem }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `palette-${item.type}`,
    data: { type: "palette", fieldType: item.type, defaultFieldType: item.defaultFieldType },
  });

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      className={`flex cursor-grab items-center gap-2 rounded-md border border-secondary-200 bg-white px-3 py-2 text-sm text-secondary-700 shadow-sm transition-colors hover:border-primary-300 hover:bg-primary-50 ${
        isDragging ? "opacity-50" : ""
      }`}
      role="button"
      tabIndex={0}
    >
      <span className="text-base">{item.icon}</span>
      <span>{item.label}</span>
    </div>
  );
}

interface ComponentPaletteProps {
  open: boolean;
  onClose: () => void;
}

export default function ComponentPalette({ open, onClose }: ComponentPaletteProps) {
  const [collapsedCategories, setCollapsedCategories] = useState<Set<string>>(new Set());

  function toggleCategory(name: string) {
    setCollapsedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  }

  return (
    <>
      {/* Overlay for mobile */}
      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/30 md:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed left-0 top-0 z-40 h-full w-60 shrink-0 overflow-y-auto border-r border-secondary-200 bg-white transition-transform md:relative md:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between border-b border-secondary-200 px-4 py-3">
          <h3 className="text-sm font-semibold text-secondary-800">Components</h3>
          <button
            onClick={onClose}
            className="rounded p-1 text-secondary-400 hover:bg-secondary-100 hover:text-secondary-600 md:hidden"
            aria-label="Close palette"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="space-y-1 p-3">
          {paletteCategories.map((category) => {
            const isCollapsed = collapsedCategories.has(category.name);
            return (
              <div key={category.name}>
                <button
                  onClick={() => toggleCategory(category.name)}
                  className="flex w-full items-center justify-between rounded-md px-2 py-1.5 text-xs font-semibold uppercase tracking-wider text-secondary-500 hover:bg-secondary-50"
                >
                  {category.name}
                  <svg
                    className={`h-3 w-3 transition-transform ${isCollapsed ? "" : "rotate-180"}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                {!isCollapsed && (
                  <div className="space-y-1 pl-2">
                    {category.items.map((item) => (
                      <DraggablePaletteItem key={item.type} item={item} />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </aside>
    </>
  );
}
