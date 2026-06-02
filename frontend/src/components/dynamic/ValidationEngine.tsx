import { useEffect } from "react";
import type { PageConfigField } from "@/hooks/usePageConfig";
import { validateField } from "@/hooks/useFieldValidation";

interface ValidationEngineProps {
  fields: PageConfigField[];
  values: Record<string, unknown>;
  onError: (fieldName: string, error: string | undefined) => void;
  submitAttempted: boolean;
  children: React.ReactNode;
}

export default function ValidationEngine({
  fields,
  values,
  onError,
  submitAttempted,
  children,
}: ValidationEngineProps) {
  useEffect(() => {
    if (!submitAttempted) return;
    for (const field of fields) {
      if (field.hidden || field.readonly) continue;
      const error = validateField(field, values[field.field_name]);
      onError(field.field_name, error);
    }
  }, [submitAttempted, fields, values, onError]);

  return <>{children}</>;
}
