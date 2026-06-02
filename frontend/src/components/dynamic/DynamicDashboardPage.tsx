import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { PageConfig } from "@/hooks/usePageConfig";

interface DynamicDashboardPageProps {
  config: PageConfig;
}

export default function DynamicDashboardPage({ config }: DynamicDashboardPageProps) {
  const { data, isLoading } = useQuery({
    queryKey: [config.api_endpoint, "dashboard"],
    queryFn: async () => {
      const { data } = await api.get(`/${config.api_endpoint}/dashboard/`);
      return data as {
        kpis?: Array<{
          label: string;
          value: number;
          prefix?: string;
          format?: string;
        }>;
        charts?: Array<{ title: string; type: string; data: unknown }>;
        tables?: Array<{ title: string; columns: string[]; rows: unknown[][] }>;
      };
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-secondary-200 border-t-primary-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold text-secondary-900">{config.page_title}</h2>

      {data?.kpis && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {data.kpis.map((kpi, idx) => (
            <KPICard
              key={idx}
              label={kpi.label}
              value={kpi.value}
              prefix={kpi.prefix}
            />
          ))}
        </div>
      )}

      {data?.tables?.map((table, idx) => (
        <div key={idx} className="rounded-md border border-secondary-200 bg-white">
          <div className="border-b border-secondary-100 px-4 py-3">
            <h3 className="text-sm font-semibold text-secondary-800">{table.title}</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-secondary-50">
                  {table.columns.map((col, ci) => (
                    <th
                      key={ci}
                      className="px-4 py-2.5 text-left font-medium text-secondary-600"
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {table.rows.map((row, ri) => (
                  <tr key={ri} className="border-t border-secondary-100">
                    {row.map((cell, ci) => (
                      <td key={ci} className="px-4 py-2.5 text-secondary-700">
                        {String(cell ?? "")}
                      </td>
                    ))}
                  </tr>
                ))}
                {table.rows.length === 0 && (
                  <tr>
                    <td
                      colSpan={table.columns.length}
                      className="px-4 py-6 text-center text-secondary-400"
                    >
                      No data
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      ))}

      {(!data || (!data.kpis && !data.charts && !data.tables)) && (
        <div className="rounded-md border border-secondary-200 bg-white p-12 text-center text-sm text-secondary-400">
          No dashboard data available
        </div>
      )}
    </div>
  );
}

function KPICard({
  label,
  value,
  prefix,
}: {
  label: string;
  value: number;
  prefix?: string;
}) {
  const formatted = prefix
    ? `${prefix} ${value.toLocaleString()}`
    : value.toLocaleString();

  return (
    <div className="rounded-md border border-secondary-200 bg-white p-4">
      <p className="text-xs font-medium text-secondary-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-secondary-900">{formatted}</p>
    </div>
  );
}
