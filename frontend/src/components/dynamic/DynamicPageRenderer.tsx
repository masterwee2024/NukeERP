import { usePageConfig } from "@/hooks/usePageConfig";
import DynamicFormPage from "./DynamicFormPage";
import DynamicListPage from "./DynamicListPage";
import DynamicDetailPage from "./DynamicDetailPage";
import DynamicDashboardPage from "./DynamicDashboardPage";
import ResponsiveRenderer from "./ResponsiveRenderer";

interface DynamicPageRendererProps {
  pageKey: string;
  recordId?: string;
}

export default function DynamicPageRenderer({
  pageKey,
  recordId,
}: DynamicPageRendererProps) {
  const { data: config, isLoading, error } = usePageConfig(pageKey);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-secondary-200 border-t-primary-600" />
      </div>
    );
  }

  if (error || !config) {
    return (
      <div className="rounded-md border border-danger-200 bg-danger-50 p-4 text-sm text-danger-700">
        Failed to load page configuration:{" "}
        {error instanceof Error ? error.message : "Unknown error"}
      </div>
    );
  }

  return (
    <ResponsiveRenderer config={config}>
      {(() => {
        switch (config.page_type) {
          case "form":
            return <DynamicFormPage config={config} recordId={recordId} />;
          case "list":
            return <DynamicListPage config={config} />;
          case "detail":
            return <DynamicDetailPage config={config} recordId={recordId} />;
          case "dashboard":
            return <DynamicDashboardPage config={config} />;
          default:
            return (
              <div className="text-sm text-secondary-500">
                Unknown page type: {config.page_type}
              </div>
            );
        }
      })()}
    </ResponsiveRenderer>
  );
}
