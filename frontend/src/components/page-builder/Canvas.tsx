import { useMemo, useCallback } from "react";
import {
  DndContext,
  closestCenter,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragOverEvent,
  DragOverlay,
  useDroppable,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { PageConfigField } from "@/hooks/usePageConfig";
import { useBuilderStore, createDefaultField } from "./builderStore";

interface CanvasFieldProps {
  field: PageConfigField;
  isSelected: boolean;
  onSelect: (id: string) => void;
  onRemove: (id: string) => void;
  previewMode: "desktop" | "mobile";
}

function SortableField({ field, isSelected, onSelect, onRemove, previewMode }: CanvasFieldProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: field.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
    gridColumn: previewMode === "mobile" ? "span 12" : `span ${Math.min(field.desktop_col_span || 6, 12)}`,
  };

  const fieldTypeLabel = field.field_type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`relative rounded-md border-2 bg-white p-3 transition-all ${
        isSelected
          ? "border-primary-500 shadow-md ring-2 ring-primary-200"
          : "border-secondary-200 hover:border-secondary-300"
      }`}
      onClick={() => onSelect(field.id)}
    >
      {/* Drag handle */}
      <div
        {...attributes}
        {...listeners}
        className="absolute left-1 top-1 cursor-grab rounded p-0.5 text-secondary-300 hover:text-secondary-500"
      >
        <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
          <path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z" />
        </svg>
      </div>

      {/* Remove button */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onRemove(field.id);
        }}
        className="absolute right-1 top-1 rounded p-0.5 text-secondary-300 hover:bg-danger-50 hover:text-danger-500"
        aria-label={`Remove ${field.field_name}`}
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      {/* Field preview */}
      <div className="mt-1">
        <div className="mb-1 flex items-center gap-2">
          {field.icon && <span className="text-sm">{field.icon}</span>}
          <span className="text-xs font-medium text-secondary-500">
            {fieldTypeLabel}
          </span>
          {field.required && (
            <span className="text-xs text-danger-500">*</span>
          )}
          {field.hidden && (
            <span className="rounded bg-secondary-100 px-1.5 py-0.5 text-[10px] text-secondary-500">Hidden</span>
          )}
        </div>
        {field.label && (
          <label className="mb-1 block text-sm font-medium text-secondary-700">
            {field.label}
          </label>
        )}
        {field.placeholder && (
          <div className="rounded-md border border-secondary-200 bg-secondary-50 px-3 py-2 text-sm text-secondary-400">
            {field.placeholder}
          </div>
        )}
        {!field.label && !field.placeholder && (
          <div className="rounded-md border border-dashed border-secondary-300 bg-secondary-50 px-3 py-4 text-center text-xs text-secondary-400">
            {field.field_name} — click to edit
          </div>
        )}
      </div>
    </div>
  );
}

function DroppableCanvas({ children }: { children: React.ReactNode }) {
  const { setNodeRef, isOver } = useDroppable({ id: "canvas-drop-zone" });

  return (
    <div
      ref={setNodeRef}
      className={`min-h-full rounded-lg border-2 border-dashed p-4 transition-colors ${
        isOver
          ? "border-primary-400 bg-primary-50/30"
          : "border-secondary-200"
      }`}
    >
      {children}
    </div>
  );
}

export default function Canvas() {
  const fields = useBuilderStore((s) => s.fields);
  const selectedFieldId = useBuilderStore((s) => s.selectedFieldId);
  const previewMode = useBuilderStore((s) => s.previewMode);
  const selectField = useBuilderStore((s) => s.selectField);
  const removeField = useBuilderStore((s) => s.removeField);
  const reorderFields = useBuilderStore((s) => s.reorderFields);
  const addField = useBuilderStore((s) => s.addField);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const fieldIds = useMemo(() => fields.map((f) => f.id), [fields]);

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over || active.id === over.id) return;

      const activeData = active.data.current;
      if (activeData?.type === "palette") {
        const fieldType = activeData.fieldType || activeData.defaultFieldType;
        const newField = createDefaultField(fieldType, {
          label: activeData.fieldType
            ? activeData.fieldType.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase())
            : "New Field",
          field_name: `field_${Date.now()}`,
        });
        const overId = over.id === "canvas-drop-zone" ? undefined : (over.id as string);
        addField(newField, overId);
        return;
      }

      const oldIndex = fields.findIndex((f) => f.id === active.id);
      const newIndex = fields.findIndex((f) => f.id === over.id);
      if (oldIndex !== -1 && newIndex !== -1) {
        reorderFields(oldIndex, newIndex);
      }
    },
    [fields, addField, reorderFields]
  );

  function handleDragOver(event: DragOverEvent) {
    const { active } = event;
    if (active.data.current?.type === "palette") {
      const overId = event.over?.id;
      if (overId && overId !== "canvas-drop-zone" && fieldIds.includes(overId as string)) {
        return;
      }
    }
  }

  const groupedFields = useMemo(() => {
    const groups: Record<string, PageConfigField[]> = {};
    for (const f of fields) {
      const key = f.group_name || "_ungrouped";
      if (!groups[key]) groups[key] = [];
      groups[key].push(f);
    }
    return groups;
  }, [fields]);

  const groupNames = Object.keys(groupedFields);

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={handleDragEnd}
      onDragOver={handleDragOver}
    >
      <div className="h-full overflow-y-auto p-4">
        {fields.length === 0 ? (
          <DroppableCanvas>
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <div className="mb-4 text-4xl text-secondary-300">📋</div>
              <h3 className="text-lg font-medium text-secondary-500">Empty Form</h3>
              <p className="mt-1 text-sm text-secondary-400">
                Drag components from the palette to start building
              </p>
            </div>
          </DroppableCanvas>
        ) : (
          <div
            className={`grid gap-3 ${
              previewMode === "mobile" ? "grid-cols-1" : "grid-cols-12"
            }`}
          >
            {groupNames.map((groupName) => {
              const groupFields = groupedFields[groupName];
              return (
                <div
                  key={groupName}
                  className={`col-span-12 ${groupName !== "_ungrouped" ? "rounded-lg border border-secondary-200 bg-secondary-50 p-3" : ""}`}
                >
                  {groupName !== "_ungrouped" && (
                    <div className="mb-3 text-xs font-semibold uppercase tracking-wider text-secondary-500">
                      {groupName}
                    </div>
                  )}
                  <SortableContext
                    items={groupFields.map((f) => f.id)}
                    strategy={verticalListSortingStrategy}
                  >
                    <div
                      className={`grid gap-3 ${
                        previewMode === "mobile" ? "grid-cols-1" : "grid-cols-12"
                      }`}
                    >
                      {groupFields.map((f) => (
                        <SortableField
                          key={f.id}
                          field={f}
                          isSelected={f.id === selectedFieldId}
                          onSelect={selectField}
                          onRemove={removeField}
                          previewMode={previewMode}
                        />
                      ))}
                    </div>
                  </SortableContext>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <DragOverlay>
        {selectedFieldId ? (
          <div className="rounded-md border-2 border-primary-400 bg-white p-3 shadow-lg opacity-80">
            <span className="text-sm text-secondary-500">Drop to reorder</span>
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}
