import type { ReactNode } from "react";
import type { PageConfigField } from "@/hooks/usePageConfig";
import {
  useConditionalDisplay,
  type VisibilityMap,
} from "@/hooks/useConditionalDisplay";
import { useWatch, type Control, type FieldValues } from "react-hook-form";

interface ConditionalEngineProps {
  fields: PageConfigField[];
  control: Control<FieldValues>;
  children: (visibility: VisibilityMap) => ReactNode;
}

export default function ConditionalEngine({
  fields,
  control,
  children,
}: ConditionalEngineProps) {
  const formValues = useWatch({ control }) as Record<string, unknown>;
  const visibility = useConditionalDisplay(fields, formValues || {});
  return <>{children(visibility)}</>;
}
