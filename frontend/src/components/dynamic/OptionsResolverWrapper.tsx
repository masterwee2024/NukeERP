import type { ReactNode } from "react";
import type { PageConfigField } from "@/hooks/usePageConfig";
import { useOptionsResolver } from "@/hooks/useOptionsResolver";

interface OptionsResolverWrapperProps {
  field: PageConfigField;
  children: (
    options: Array<{ label: string; value: string }>,
    loading: boolean
  ) => ReactNode;
}

export default function OptionsResolverWrapper({
  field,
  children,
}: OptionsResolverWrapperProps) {
  const { options, loading } = useOptionsResolver(field);
  return <>{children(options, loading)}</>;
}
