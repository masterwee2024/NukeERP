import { useState, useCallback } from "react";

interface Condition {
  id: string;
  field: string;
  operator: string;
  value: string;
}

interface ConditionBuilderProps {
  value: Record<string, unknown>;
  onChange: (value: Record<string, unknown>) => void;
}

const operators = [
  { value: "==", label: "==" },
  { value: "!=", label: "!=" },
  { value: ">", label: ">" },
  { value: "<", label: "<" },
  { value: ">=", label: ">=" },
  { value: "<=", label: "<=" },
  { value: "in", label: "In" },
  { value: "not_in", label: "Not In" },
  { value: "contains", label: "Contains" },
  { value: "empty", label: "Empty" },
  { value: "not_empty", label: "Not Empty" },
];

let condCounter = 0;
function newCondId(): string {
  condCounter += 1;
  return `cond_${condCounter}_${Date.now()}`;
}

function defaultCondition(): Condition {
  return { id: newCondId(), field: "", operator: "==", value: "" };
}

export default function ConditionBuilder({ value, onChange }: ConditionBuilderProps) {
  const [logic, setLogic] = useState<"AND" | "OR">(
    (value.logic as "AND" | "OR") || "AND"
  );
  const [conditions, setConditions] = useState<Condition[]>(() => {
    const raw = value.conditions as Array<Record<string, string>>;
    if (Array.isArray(raw) && raw.length > 0) {
      return raw.map((c) => ({
        id: newCondId(),
        field: c.field || "",
        operator: c.operator || "==",
        value: c.value || "",
      }));
    }
    return [];
  });

  const emitChange = useCallback(
    (newLogic: "AND" | "OR", newConditions: Condition[]) => {
      if (newConditions.length === 0) {
        onChange({});
      } else {
        onChange({
          logic: newLogic,
          conditions: newConditions.map(({ id, ...rest }) => rest),
        });
      }
    },
    [onChange]
  );

  function addCondition() {
    const next = [...conditions, defaultCondition()];
    setConditions(next);
    emitChange(logic, next);
  }

  function removeCondition(id: string) {
    const next = conditions.filter((c) => c.id !== id);
    setConditions(next);
    emitChange(logic, next);
  }

  function updateCondition(id: string, key: keyof Condition, val: string) {
    const next = conditions.map((c) => (c.id === id ? { ...c, [key]: val } : c));
    setConditions(next);
    emitChange(logic, next);
  }

  function toggleLogic() {
    const next = logic === "AND" ? "OR" : "AND";
    setLogic(next);
    emitChange(next, conditions);
  }

  if (conditions.length === 0) {
    return (
      <div className="space-y-2">
        <p className="text-xs text-secondary-400">No conditions set</p>
        <button
          onClick={addCondition}
          className="flex items-center gap-1 rounded-md border border-dashed border-secondary-300 px-3 py-1.5 text-xs text-secondary-500 hover:border-primary-300 hover:text-primary-600"
        >
          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Condition
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-2 rounded-md border border-secondary-200 bg-secondary-50 p-2">
      {conditions.map((cond, index) => (
        <div key={cond.id}>
          {index > 0 && (
            <div className="mb-1 flex items-center gap-2">
              <button
                onClick={toggleLogic}
                className="rounded bg-secondary-200 px-2 py-0.5 text-[10px] font-semibold text-secondary-600 hover:bg-secondary-300"
              >
                {logic}
              </button>
              <div className="flex-1 border-t border-secondary-200" />
            </div>
          )}
          <div className="flex items-center gap-1">
            <input
              type="text"
              value={cond.field}
              onChange={(e) => updateCondition(cond.id, "field", e.target.value)}
              placeholder="field_name"
              className="w-20 rounded border border-secondary-300 px-1.5 py-1 text-[11px] focus:border-primary-500 focus:outline-none"
            />
            <select
              value={cond.operator}
              onChange={(e) => updateCondition(cond.id, "operator", e.target.value)}
              className="w-16 rounded border border-secondary-300 px-1 py-1 text-[11px] focus:border-primary-500 focus:outline-none"
            >
              {operators.map((op) => (
                <option key={op.value} value={op.value}>{op.label}</option>
              ))}
            </select>
            {cond.operator !== "empty" && cond.operator !== "not_empty" && (
              <input
                type="text"
                value={cond.value}
                onChange={(e) => updateCondition(cond.id, "value", e.target.value)}
                placeholder="value"
                className="w-20 rounded border border-secondary-300 px-1.5 py-1 text-[11px] focus:border-primary-500 focus:outline-none"
              />
            )}
            <button
              onClick={() => removeCondition(cond.id)}
              className="rounded p-0.5 text-secondary-400 hover:text-danger-500"
              aria-label="Remove condition"
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      ))}
      <button
        onClick={addCondition}
        className="flex items-center gap-1 rounded-md border border-dashed border-secondary-300 px-3 py-1.5 text-xs text-secondary-500 hover:border-primary-300 hover:text-primary-600"
      >
        <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
        Add Condition
      </button>
    </div>
  );
}
