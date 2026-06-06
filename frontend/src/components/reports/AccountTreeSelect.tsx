import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

interface AccountNode {
  id: string;
  code: string;
  name: string;
  account_type: string;
  level: number;
  children: AccountNode[];
}

interface AccountTreeSelectProps {
  label: string;
  values: string[];
  onChange: (ids: string[]) => void;
}

export default function AccountTreeSelect({ label, values, onChange }: AccountTreeSelectProps) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [open, setOpen] = useState(false);

  const { data: tree = [] } = useQuery<AccountNode[]>({
    queryKey: ["accounts-tree"],
    queryFn: () => api.get("/api/v1/financial/accounts/").then((r) => r.data.results || r.data),
  });

  const selected = new Set(values);

  const toggleExpand = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelect = (id: string) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onChange(Array.from(next));
  };

  const renderNode = (node: AccountNode, depth: number) => (
    <div key={node.id}>
      <div
        className="flex items-center gap-2 py-1 text-sm"
        style={{ paddingLeft: `${depth * 16}px` }}
      >
        {node.children?.length > 0 && (
          <button onClick={() => toggleExpand(node.id)} className="text-gray-400">
            <svg
              className={`h-3 w-3 transition-transform ${expanded.has(node.id) ? "rotate-90" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        )}
        <input
          type="checkbox"
          checked={selected.has(node.id)}
          onChange={() => toggleSelect(node.id)}
          className="rounded border-gray-300"
        />
        <span className="font-mono text-xs text-gray-500">{node.code}</span>
        <span>{node.name}</span>
      </div>
      {node.children?.length > 0 && expanded.has(node.id) && (
        <div>{node.children.map((c) => renderNode(c, depth + 1))}</div>
      )}
    </div>
  );

  return (
    <div className="space-y-1">
      <label className="text-sm font-medium text-gray-700">{label}</label>
      <div className="relative">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="flex w-full items-center justify-between rounded-md border border-gray-300 px-3 py-2 text-sm"
        >
          <span>{selected.size > 0 ? `${selected.size} selected` : "Select accounts..."}</span>
          <svg className={`h-4 w-4 transition-transform ${open ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        {open && (
          <div className="absolute z-10 mt-1 max-h-60 w-full overflow-y-auto rounded-md border bg-white shadow-lg">
            <div className="p-2">
              <button
                onClick={() => {
                  const allIds = getAllIds(tree);
                  onChange(allIds);
                }}
                className="mr-2 text-xs text-primary-600 hover:underline"
              >
                Select All
              </button>
              <button
                onClick={() => onChange([])}
                className="text-xs text-gray-500 hover:underline"
              >
                Clear
              </button>
            </div>
            <div className="border-t px-2 pb-2">{tree.map((n) => renderNode(n, 0))}</div>
          </div>
        )}
      </div>
    </div>
  );
}

function getAllIds(nodes: AccountNode[]): string[] {
  const ids: string[] = [];
  for (const n of nodes) {
    ids.push(n.id);
    if (n.children) ids.push(...getAllIds(n.children));
  }
  return ids;
}
