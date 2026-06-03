import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { PageConfig, PageConfigField } from "@/hooks/usePageConfig";
import { useBuilderStore } from "./builderStore";
import ComponentPalette from "./ComponentPalette";
import Canvas from "./Canvas";
import PropertyEditor from "./PropertyEditor";
import ConfigActions from "./ConfigActions";

const defaultConfig: Partial<PageConfig> = {
  page_key: "",
  page_title: "",
  page_type: "form",
  module: "core",
  entity_model: "",
  api_endpoint: "",
  layout: "single",
  desktop_layout: "single",
  mobile_layout: "single",
  list_mobile_view: "card",
  mobile_group_by: "",
  actions: [],
  breadcrumbs: [],
  page_size: 25,
  sort_default: "",
  sort_direction: "asc",
};

export default function PageBuilderLayout() {
  const { pageKey } = useParams<{ pageKey: string }>();
  const navigate = useNavigate();
  const isNew = pageKey === "new" || !pageKey;

  const reset = useBuilderStore((s) => s.reset);
  const config = useBuilderStore((s) => s.config);
  const fields = useBuilderStore((s) => s.fields);
  const setConfig = useBuilderStore((s) => s.setConfig);
  const setFields = useBuilderStore((s) => s.setFields);
  const markClean = useBuilderStore((s) => s.markClean);

  const [paletteOpen, setPaletteOpen] = useState(false);
  const [propertyEditorOpen, setPropertyEditorOpen] = useState(false);

  // Load existing config
  const { data: existingConfig, isLoading } = useQuery({
    queryKey: ["pageConfig", pageKey],
    queryFn: async () => {
      if (isNew) return null;
      const { data } = await api.get(`/core/page-configs/${pageKey}/`);
      return data as PageConfig;
    },
    enabled: !isNew,
  });

  // Populate store when config loads
  useEffect(() => {
    if (isNew) {
      reset();
      setConfig({ ...defaultConfig, page_key: `new_${Date.now()}` });
      return;
    }
    if (existingConfig) {
      const { fields: existingFields, ...rest } = existingConfig;
      setConfig(rest);
      setFields(existingFields || []);
    }
  }, [existingConfig, isNew, reset, setConfig, setFields]);

  const handleSave = useCallback(async () => {
    const payload = {
      ...config,
      fields: fields.map((f) => ({
        ...f,
        // Remove transient id
        id: undefined,
      })),
    };

    if (isNew) {
      const { data } = await api.post("/core/page-configs/", payload);
      markClean();
      navigate(`/app/admin/page-builder/${data.page_key}`, { replace: true });
    } else {
      await api.put(`/core/page-configs/${pageKey}/`, payload);
      markClean();
    }
  }, [config, fields, isNew, pageKey, markClean, navigate]);

  const handlePublish = useCallback(async () => {
    if (isNew) {
      await handleSave();
    }
    const payload = {
      ...config,
      fields: fields.map((f) => {
        const { id, ...rest } = f;
        return rest;
      }),
      is_active: true,
    };
    await api.put(`/core/page-configs/${pageKey}/`, payload);
    markClean();
  }, [config, fields, isNew, pageKey, handleSave, markClean]);

  const handleExport = useCallback(() => {
    const payload = {
      ...config,
      fields,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${config.page_key || "page-config"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [config, fields]);

  const handleImport = useCallback(
    (jsonStr: string) => {
      try {
        const data = JSON.parse(jsonStr);
        const { fields: importedFields, ...configData } = data;
        setConfig({ ...defaultConfig, ...configData });
        setFields(
          (importedFields || []).map((f: PageConfigField) => ({
            ...f,
            id: f.id || `imported_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`,
          }))
        );
      } catch {
        // handled by caller
      }
    },
    [setConfig, setFields]
  );

  const handleClone = useCallback(async () => {
    const payload = {
      ...config,
      page_key: `${config.page_key || "new"}_clone`,
      page_title: `${config.page_title || "Untitled"} (Clone)`,
      fields: fields.map((f) => {
        const { id, ...rest } = f;
        return rest;
      }),
    };
    const { data } = await api.post("/core/page-configs/", payload);
    navigate(`/app/admin/page-builder/${data.page_key}`);
    markClean();
  }, [config, fields, navigate, markClean]);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-secondary-200 border-t-primary-600" />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Config title */}
      <div className="flex items-center gap-3 border-b border-secondary-200 bg-white px-4 py-3">
        <button
          onClick={() => setPaletteOpen(true)}
          className="rounded-md border border-secondary-300 px-3 py-1.5 text-xs font-medium text-secondary-600 hover:bg-secondary-50 md:hidden"
        >
          Palette
        </button>
        <div className="flex-1">
          <input
            type="text"
            value={config.page_title || ""}
            onChange={(e) => setConfig({ ...config, page_title: e.target.value })}
            placeholder="Page Title"
            className="w-full text-lg font-semibold text-secondary-900 focus:outline-none"
          />
        </div>
        <button
          onClick={() => setPropertyEditorOpen(true)}
          className="rounded-md border border-secondary-300 px-3 py-1.5 text-xs font-medium text-secondary-600 hover:bg-secondary-50 md:hidden"
        >
          Properties
        </button>
      </div>

      {/* Action bar */}
      <ConfigActions
        onSave={handleSave}
        onPublish={handlePublish}
        onExport={handleExport}
        onImport={handleImport}
        onClone={handleClone}
      />

      {/* Three-panel layout */}
      <div className="flex flex-1 overflow-hidden">
        <ComponentPalette
          open={paletteOpen}
          onClose={() => setPaletteOpen(false)}
        />

        <main className="flex-1 overflow-hidden bg-secondary-50/50">
          <Canvas />
        </main>

        <PropertyEditor
          open={propertyEditorOpen}
          onClose={() => setPropertyEditorOpen(false)}
        />
      </div>
    </div>
  );
}
