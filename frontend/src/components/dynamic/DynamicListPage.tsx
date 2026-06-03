import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import type { PageConfig } from "@/hooks/usePageConfig";
import { useDebounce } from "@/hooks/useDebounce";
import { useViewport } from "@/hooks/useViewport";
import CardView from "./CardView";

interface DynamicListPageProps {
  config: PageConfig;
}

interface SortConfig {
  key: string;
  direction: "asc" | "desc";
}

export default function DynamicListPage({ config }: DynamicListPageProps) {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<SortConfig>({
    key: config.sort_default || "",
    direction: (config.sort_direction as "asc" | "desc") || "asc",
  });
  const debouncedSearch = useDebounce(search, 300);
  const { isMobile } = useViewport();

  const queryParams = useMemo(() => {
    const params = new URLSearchParams();
    params.set("page", String(page));
    params.set("page_size", String(config.page_size || 25));
    if (debouncedSearch) params.set("search", debouncedSearch);
    if (sort.key) {
      params.set("ordering", sort.direction === "desc" ? `-${sort.key}` : sort.key);
    }
    return params.toString();
  }, [page, config.page_size, debouncedSearch, sort]);

  const { data, isLoading } = useQuery({
    queryKey: [config.api_endpoint, queryParams],
    queryFn: async () => {
      const { data } = await api.get(`/${config.api_endpoint}/?${queryParams}`);
      return data as { count: number; results: Record<string, unknown>[] };
    },
  });

  const columns = config.fields
    .filter((f) => f.is_column)
    .sort((a, b) => a.column_order - b.column_order);
  const totalPages = data ? Math.ceil(data.count / (config.page_size || 25)) : 1;

  if (isMobile && config.list_mobile_view === "card") {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-secondary-900">
            {config.page_title}
          </h2>
        </div>
        <SearchBar value={search} onChange={setSearch} />
        <CardView records={data?.results || []} config={config} isLoading={isLoading} />
        <Pagination page={page} totalPages={totalPages} onChange={setPage} />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-secondary-900">
          {config.page_title}
        </h2>
        <div className="flex gap-2">
          {config.actions
            .filter(
              (a) =>
                a.label.toLowerCase() === "create" || a.label.toLowerCase() === "add"
            )
            .map((action) => (
              <button
                key={action.label}
                type="button"
                onClick={() => navigate(`/app/${config.module}/${config.page_key}/new`)}
                className="rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
              >
                {action.label}
              </button>
            ))}
        </div>
      </div>

      <SearchBar value={search} onChange={setSearch} />

      <div className="overflow-x-auto rounded-md border border-secondary-200">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-secondary-50">
              {columns.map((col) => (
                <th
                  key={col.field_name}
                  className={`px-4 py-3 ${alignClass(col.column_align)} font-medium text-secondary-600 ${
                    col.sortable
                      ? "cursor-pointer select-none hover:text-secondary-800"
                      : ""
                  }`}
                  style={col.column_width ? { width: col.column_width } : undefined}
                  onClick={() => {
                    if (!col.sortable) return;
                    setSort((prev) => ({
                      key: col.field_name,
                      direction:
                        prev.key === col.field_name && prev.direction === "asc"
                          ? "desc"
                          : "asc",
                    }));
                  }}
                >
                  <span className="inline-flex items-center gap-1">
                    {col.label}
                    {col.sortable && sort.key === col.field_name && (
                      <span className="text-xs">
                        {sort.direction === "asc" ? "↑" : "↓"}
                      </span>
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-4 py-8 text-center text-secondary-400"
                >
                  Loading...
                </td>
              </tr>
            )}
            {!isLoading && (!data?.results || data.results.length === 0) && (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-4 py-8 text-center text-secondary-400"
                >
                  No records found
                </td>
              </tr>
            )}
            {!isLoading &&
              data?.results.map((record, idx) => (
                <tr
                  key={(record.id as string) || idx}
                  className="border-t border-secondary-100 hover:bg-secondary-50"
                >
                  {columns.map((col) => (
                    <td
                      key={col.field_name}
                      className={`px-4 py-3 ${alignClass(col.column_align)} text-secondary-700`}
                    >
                      {formatCellValue(record[col.field_name], col.field_type)}
                    </td>
                  ))}
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      <Pagination page={page} totalPages={totalPages} onChange={setPage} />
    </div>
  );
}

function SearchBar({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="relative">
      <svg
        className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-secondary-400"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
        />
      </svg>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Search..."
        className="w-full rounded-md border border-secondary-300 bg-white py-2 pl-10 pr-3 text-sm outline-none focus:border-primary-500"
      />
    </div>
  );
}

function Pagination({
  page,
  totalPages,
  onChange,
}: {
  page: number;
  totalPages: number;
  onChange: (p: number) => void;
}) {
  return (
    <div className="flex items-center justify-between text-sm text-secondary-600">
      <span>
        Page {page} of {totalPages}
      </span>
      <div className="flex gap-2">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
          className="rounded-md border border-secondary-300 px-3 py-1.5 hover:bg-secondary-50 disabled:opacity-50"
        >
          Previous
        </button>
        <button
          type="button"
          disabled={page >= totalPages}
          onClick={() => onChange(page + 1)}
          className="rounded-md border border-secondary-300 px-3 py-1.5 hover:bg-secondary-50 disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
  );
}

const alignMap: Record<string, string> = {
  left: "text-left",
  center: "text-center",
  right: "text-right",
};

function alignClass(align?: string): string {
  return alignMap[align || "left"] || "text-left";
}

function formatCellValue(value: unknown, fieldType: string): string {
  if (value === null || value === undefined) return "—";
  if (fieldType === "currency") {
    const num = Number(value);
    return isNaN(num) ? String(value) : `RM ${num.toFixed(2)}`;
  }
  return String(value);
}
