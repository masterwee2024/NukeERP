import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

interface Period {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  is_open: boolean;
}

interface PeriodRangeSelectProps {
  label: string;
  value?: string;
  onChange: (id: string) => void;
}

export default function PeriodRangeSelect({ label, value, onChange }: PeriodRangeSelectProps) {
  const { data: periods = [] } = useQuery<Period[]>({
    queryKey: ["periods"],
    queryFn: () => api.get("/financial/periods/").then((r) => r.data),
  });

  return (
    <div className="space-y-1">
      <label className="text-sm font-medium text-gray-700">{label}</label>
      <select
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
      >
        <option value="">Select {label}...</option>
        {periods.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name} ({p.start_date} - {p.end_date})
          </option>
        ))}
      </select>
    </div>
  );
}
