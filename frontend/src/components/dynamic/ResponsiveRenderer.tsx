import type { ReactNode } from "react";
import type { PageConfig } from "@/hooks/usePageConfig";
import { useViewport } from "@/hooks/useViewport";

interface ResponsiveRendererProps {
  config: PageConfig;
  children: ReactNode;
}

export default function ResponsiveRenderer({
  config,
  children,
}: ResponsiveRendererProps) {
  const { isMobile, isTablet } = useViewport();

  return (
    <div
      className={`py-4 ${isMobile ? "px-2" : isTablet ? "px-4" : "px-6"} max-w-full`}
    >
      {config.breadcrumbs && config.breadcrumbs.length > 0 && (
        <nav className="mb-4 flex items-center gap-2 text-sm text-secondary-400">
          {config.breadcrumbs.map((crumb, idx) => (
            <span key={idx} className="flex items-center gap-2">
              {idx > 0 && <span>/</span>}
              {crumb.href ? (
                <a href={crumb.href} className="hover:text-secondary-600">
                  {crumb.label}
                </a>
              ) : (
                <span className="text-secondary-800">{crumb.label}</span>
              )}
            </span>
          ))}
        </nav>
      )}
      {children}
    </div>
  );
}
