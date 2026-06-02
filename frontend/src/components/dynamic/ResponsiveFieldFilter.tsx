import type { PageConfigField } from "@/hooks/usePageConfig";
import { useViewport } from "@/hooks/useViewport";

interface ResponsiveFieldFilterProps {
  fields: PageConfigField[];
  visibilityMap: Record<string, boolean>;
  children: (visibleFields: PageConfigField[]) => React.ReactNode;
}

export default function ResponsiveFieldFilter({
  fields,
  visibilityMap,
  children,
}: ResponsiveFieldFilterProps) {
  const { isDesktop } = useViewport();

  const visibleFields = fields.filter((f) => {
    const isVisible = visibilityMap[f.field_name] !== false;
    const showOnCurrent = isDesktop ? f.show_on_desktop : f.show_on_mobile;
    return isVisible && showOnCurrent && !f.hidden;
  });

  return <>{children(visibleFields)}</>;
}
