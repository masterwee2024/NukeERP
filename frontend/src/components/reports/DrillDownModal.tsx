import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

interface DrillDownEntry {
  date: string;
  entry_number: string;
  description: string;
  debit: number;
  credit: number;
  balance: number;
}

interface DrillDownModalProps {
  open: boolean;
  onClose: () => void;
  reportCode: string;
  accountId: string;
  periodId: string;
}

export default function DrillDownModal({
  open,
  onClose,
  reportCode,
  accountId,
  periodId,
}: DrillDownModalProps) {
  const { data, isLoading } = useQuery<{ results: DrillDownEntry[] }>({
    queryKey: ["drill-down", reportCode, accountId, periodId],
    queryFn: () =>
      api
        .get(`/api/v1/financial/reports/${reportCode}/drill-down/`, {
          params: { account_id: accountId, period_id: periodId },
        })
        .then((r) => r.data),
    enabled: open && !!accountId && !!periodId,
  });

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={onClose}>
      <div
        className="max-h-[80vh] w-full max-w-3xl overflow-auto rounded-lg bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Drill-Down Detail</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-8">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-500 border-t-transparent" />
          </div>
        ) : !data?.results?.length ? (
          <p className="py-8 text-center text-gray-500">No transactions found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-gray-500">Date</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-gray-500">Entry #</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-gray-500">Description</th>
                  <th className="px-3 py-2 text-right text-xs font-semibold uppercase text-gray-500">Debit</th>
                  <th className="px-3 py-2 text-right text-xs font-semibold uppercase text-gray-500">Credit</th>
                  <th className="px-3 py-2 text-right text-xs font-semibold uppercase text-gray-500">Balance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {data.results.map((entry, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="whitespace-nowrap px-3 py-2 text-sm">{entry.date}</td>
                    <td className="whitespace-nowrap px-3 py-2 text-sm font-mono">{entry.entry_number}</td>
                    <td className="px-3 py-2 text-sm">{entry.description}</td>
                    <td className="whitespace-nowrap px-3 py-2 text-right font-mono text-sm">
                      {entry.debit.toLocaleString("en-MY", { minimumFractionDigits: 2 })}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-right font-mono text-sm">
                      {entry.credit.toLocaleString("en-MY", { minimumFractionDigits: 2 })}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-right font-mono text-sm">
                      {entry.balance.toLocaleString("en-MY", { minimumFractionDigits: 2 })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
