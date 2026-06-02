import { useMemo } from "react";
import type { PageConfigField } from "@/hooks/usePageConfig";

export interface VisibilityMap {
  [fieldName: string]: boolean;
}

function evaluateCondition(
  condition: unknown,
  formValues: Record<string, unknown>
): boolean {
  if (!condition || typeof condition !== "object") return true;

  const cond = condition as Record<string, unknown>;

  if ("eq" in cond) {
    const eq = cond as { field: string; eq: unknown };
    return formValues[eq.field] === eq.eq;
  }

  if ("neq" in cond) {
    const neq = cond as { field: string; neq: unknown };
    return formValues[neq.field] !== neq.neq;
  }

  if ("gt" in cond) {
    const gt = cond as { field: string; gt: number };
    return Number(formValues[gt.field]) > gt.gt;
  }

  if ("lt" in cond) {
    const lt = cond as { field: string; lt: number };
    return Number(formValues[lt.field]) < lt.lt;
  }

  if ("in" in cond) {
    const c = cond as { field: string; in: unknown[] };
    return c.in.includes(formValues[c.field]);
  }

  if ("not_in" in cond) {
    const c = cond as { field: string; not_in: unknown[] };
    return !c.not_in.includes(formValues[c.field]);
  }

  if ("and" in cond) {
    const c = cond as { and: unknown[] };
    return c.and.every((sub) => evaluateCondition(sub, formValues));
  }

  if ("or" in cond) {
    const c = cond as { or: unknown[] };
    return c.or.some((sub) => evaluateCondition(sub, formValues));
  }

  if ("not" in cond) {
    const c = cond as { not: unknown };
    return !evaluateCondition(c.not, formValues);
  }

  if ("blank" in cond) {
    const c = cond as { field: string; blank: boolean };
    const val = formValues[c.field];
    const isEmpty = val === undefined || val === null || val === "";
    return c.blank ? isEmpty : !isEmpty;
  }

  return true;
}

export function useConditionalDisplay(
  fields: PageConfigField[],
  formValues: Record<string, unknown>
): VisibilityMap {
  return useMemo(() => {
    const visibility: VisibilityMap = {};
    for (const field of fields) {
      if (!field.show_when || Object.keys(field.show_when).length === 0) {
        visibility[field.field_name] = true;
      } else {
        visibility[field.field_name] = evaluateCondition(field.show_when, formValues);
      }
    }
    return visibility;
  }, [fields, formValues]);
}
