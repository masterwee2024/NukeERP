import type { PageConfigField } from "@/hooks/usePageConfig";

export interface DynamicFieldProps {
  field: PageConfigField;
  value: unknown;
  onChange: (name: string, value: unknown) => void;
  error?: string;
  disabled?: boolean;
}
