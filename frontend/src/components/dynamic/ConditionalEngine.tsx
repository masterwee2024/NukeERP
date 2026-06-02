import type { ReactNode } from "react";
import type { PageConfigField } from "@/hooks/usePageConfig";
import {
  useConditionalDisplay,
  type VisibilityMap,
} from "@/hooks/useConditionalDisplay";

interface ConditionalEngineProps {
  fields: PageConfigField[];
  formValues: Record<string, unknown>;
  children: (visibility: VisibilityMap) => ReactNode;
}

export default function ConditionalEngine({
  fields,
  formValues,
  children,
}: ConditionalEngineProps) {
  const visibility = useConditionalDisplay(fields, formValues);
  return <>{children(visibility)}</>;
}
