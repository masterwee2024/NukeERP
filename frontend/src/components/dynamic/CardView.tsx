import type { PageConfig } from "@/hooks/usePageConfig";

interface CardViewProps {
  records: Record<string, unknown>[];
  config: PageConfig;
  isLoading: boolean;
}

export default function CardView({ records, config, isLoading }: CardViewProps) {
  const columns = config.fields
    .filter((f) => f.is_column)
    .sort((a, b) => a.column_order - b.column_order);
  const groupByField = config.mobile_group_by;

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="animate-pulse rounded-md border border-secondary-200 bg-white p-4"
          >
            <div className="mb-2 h-4 w-1/3 rounded bg-secondary-200" />
            <div className="h-3 w-2/3 rounded bg-secondary-100" />
          </div>
        ))}
      </div>
    );
  }

  if (records.length === 0) {
    return (
      <div className="rounded-md border border-secondary-200 bg-white p-8 text-center text-sm text-secondary-400">
        No records found
      </div>
    );
  }

  if (groupByField) {
    const groups = groupRecords(records, groupByField);
    return (
      <div className="space-y-4">
        {Object.entries(groups).map(([groupValue, groupRecords]) => (
          <div key={groupValue}>
            <h4 className="mb-2 text-sm font-semibold text-secondary-600">
              {groupValue}
            </h4>
            <div className="space-y-2">
              {groupRecords.map((record, idx) => (
                <Card
                  key={(record.id as string) || idx}
                  record={record}
                  columns={columns}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {records.map((record, idx) => (
        <Card key={(record.id as string) || idx} record={record} columns={columns} />
      ))}
    </div>
  );
}

function Card({
  record,
  columns,
}: {
  record: Record<string, unknown>;
  columns: { field_name: string; label: string; field_type: string }[];
}) {
  const primaryField = columns[0];
  const secondaryFields = columns.slice(1, 4);

  return (
    <div className="rounded-md border border-secondary-200 bg-white p-4 hover:shadow-sm">
      {primaryField && (
        <p className="font-medium text-secondary-900">
          {String(record[primaryField.field_name] ?? "") || "—"}
        </p>
      )}
      {secondaryFields.length > 0 && (
        <div className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-secondary-500">
          {secondaryFields.map((col) => (
            <span key={col.field_name}>
              {col.label}: {formatCardValue(record[col.field_name], col.field_type)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function formatCardValue(value: unknown, fieldType: string): string {
  if (value === null || value === undefined) return "—";
  if (fieldType === "currency") {
    const num = Number(value);
    return isNaN(num) ? String(value) : `RM ${num.toFixed(2)}`;
  }
  return String(value);
}

function groupRecords(
  records: Record<string, unknown>[],
  field: string
): Record<string, Record<string, unknown>[]> {
  const groups: Record<string, Record<string, unknown>[]> = {};
  for (const record of records) {
    const key = String(record[field] ?? "Other");
    if (!groups[key]) groups[key] = [];
    groups[key].push(record);
  }
  return groups;
}
