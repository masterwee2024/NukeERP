import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { useConfirm } from "@/components/ui/ConfirmDialog";
import type { PageConfig } from "@/hooks/usePageConfig";

const moduleOptions = [
  { value: "", label: "All Modules" },
  { value: "core", label: "Core" },
  { value: "financial", label: "Financial" },
  { value: "assets", label: "Assets" },
  { value: "treasury", label: "Treasury" },
  { value: "scm", label: "SCM" },
  { value: "crm", label: "CRM" },
  { value: "mrp", label: "MRP" },
  { value: "hrm", label: "HRM" },
  { value: "admin", label: "Admin" },
];

export default function PageList() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { confirm } = useConfirm();
  const [search, setSearch] = useState("");
  const [moduleFilter, setModuleFilter] = useState("");

  const { data: configs, isLoading } = useQuery({
    queryKey: ["pageConfigs", moduleFilter, search],
    queryFn: async (): Promise<PageConfig[]> => {
      const params = new URLSearchParams();
      if (moduleFilter) params.set("module", moduleFilter);
      if (search) params.set("search", search);
      const { data } = await api.get(`/core/page-configs/?${params.toString()}`);
      // The API may return paginated results or array
      if (Array.isArray(data)) return data;
      if (data.results) return data.results;
      return data?.data || [];
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (pageKey: string) => {
      await api.delete(`/core/page-configs/${pageKey}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pageConfigs"] });
    },
  });

  const cloneMutation = useMutation({
    mutationFn: async (config: PageConfig) => {
      const { data } = await api.post("/core/page-configs/", {
        ...config,
        page_key: `${config.page_key}_clone`,
        page_title: `${config.page_title} (Clone)`,
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pageConfigs"] });
    },
  });

  const handleDelete = async (config: PageConfig) => {
    const ok = await confirm({
      title: "Delete Page Config",
      message: `Are you sure you want to delete "${config.page_title}"? This action cannot be undone.`,
      variant: "danger",
      confirmText: "Delete",
    });
    if (ok) {
      deleteMutation.mutate(config.page_key);
    }
  };

  const handleClone = async (config: PageConfig) => {
    const ok = await confirm({
      title: "Clone Page Config",
      message: `Clone "${config.page_title}" as a new configuration?`,
      variant: "info",
      confirmText: "Clone",
    });
    if (ok) {
      cloneMutation.mutate(config);
    }
  };

  const handleExport = (config: PageConfig) => {
    const blob = new Blob([JSON.stringify(config, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${config.page_key}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-4 md:p-6">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-xl font-bold text-secondary-900 md:text-2xl">
          Page Builder
        </h1>
        <button
          onClick={() => navigate("/app/admin/page-builder/new")}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
        >
          + New Page Config
        </button>
      </div>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Search by key or title..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
        />
        <select
          value={moduleFilter}
          onChange={(e) => setModuleFilter(e.target.value)}
          className="rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
        >
          {moduleOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="py-8 text-center text-sm text-secondary-400">
          Loading...
        </div>
      )}

      {/* Mobile: card layout */}
      {!isLoading && (
        <div className="space-y-3 md:hidden">
          {configs?.length === 0 ? (
            <div className="py-8 text-center text-sm text-secondary-400">
              No page configs found
            </div>
          ) : (
            configs?.map((config) => (
              <div
                key={config.page_key}
                className="rounded-lg border border-secondary-200 bg-white p-4 shadow-sm"
              >
                <div className="mb-1 flex items-start justify-between">
                  <div>
                    <div className="font-medium text-secondary-900">
                      {config.page_title}
                    </div>
                    <div className="text-xs text-secondary-500">
                      {config.page_key}
                    </div>
                  </div>
                  <span className="shrink-0 rounded-full bg-primary-100 px-2 py-0.5 text-xs text-primary-700">
                    {config.module}
                  </span>
                </div>
                <div className="mt-3 flex flex-wrap gap-1">
                  <span className="rounded bg-secondary-100 px-1.5 py-0.5 text-[10px] text-secondary-600">
                    {config.page_type}
                  </span>
                  <span className="rounded bg-secondary-100 px-1.5 py-0.5 text-[10px] text-secondary-600">
                    {config.fields?.length || 0} fields
                  </span>
                </div>
                <div className="mt-3 flex gap-3 border-t border-secondary-100 pt-3 text-sm">
                  <button
                    onClick={() =>
                      navigate(`/app/admin/page-builder/${config.page_key}`)
                    }
                    className="font-medium text-primary-600 hover:text-primary-800"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleClone(config)}
                    className="font-medium text-secondary-600 hover:text-secondary-800"
                  >
                    Clone
                  </button>
                  <button
                    onClick={() => handleExport(config)}
                    className="font-medium text-secondary-600 hover:text-secondary-800"
                  >
                    Export
                  </button>
                  <button
                    onClick={() => handleDelete(config)}
                    className="font-medium text-danger-600 hover:text-danger-800"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Desktop: table layout */}
      {!isLoading && (
        <div className="hidden overflow-x-auto rounded-lg border border-secondary-200 md:block">
          <table className="min-w-full divide-y divide-secondary-200">
            <thead className="bg-secondary-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-secondary-500">
                  Title
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-secondary-500">
                  Key
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-secondary-500">
                  Module
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-secondary-500">
                  Type
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-secondary-500">
                  Fields
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-secondary-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-secondary-200">
              {configs?.length === 0 ? (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-8 text-center text-secondary-400"
                  >
                    No page configs found
                  </td>
                </tr>
              ) : (
                configs?.map((config) => (
                  <tr key={config.page_key} className="hover:bg-secondary-50">
                    <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-secondary-900">
                      {config.page_title}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm font-mono text-secondary-600">
                      {config.page_key}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm">
                      <span className="rounded-full bg-primary-100 px-2 py-0.5 text-xs text-primary-700">
                        {config.module}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm text-secondary-600">
                      {config.page_type}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm text-secondary-600">
                      {config.fields?.length || 0}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() =>
                            navigate(
                              `/app/admin/page-builder/${config.page_key}`
                            )
                          }
                          className="text-primary-600 hover:text-primary-800"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleClone(config)}
                          className="text-secondary-600 hover:text-secondary-800"
                        >
                          Clone
                        </button>
                        <button
                          onClick={() => handleExport(config)}
                          className="text-secondary-600 hover:text-secondary-800"
                        >
                          Export
                        </button>
                        <button
                          onClick={() => handleDelete(config)}
                          className="text-danger-600 hover:text-danger-800"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
