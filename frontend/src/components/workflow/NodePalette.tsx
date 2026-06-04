const NODE_TYPES = [
  { type: "start", label: "Start", color: "bg-green-500", description: "Entry point" },
  { type: "end", label: "End", color: "bg-red-500", description: "Terminal node" },
  { type: "approve", label: "Approve", color: "bg-blue-500", description: "Approval step" },
  { type: "condition", label: "Condition", color: "bg-yellow-500", description: "Branch logic" },
  { type: "notify", label: "Notify", color: "bg-purple-500", description: "Send notification" },
  { type: "action", label: "Action", color: "bg-gray-500", description: "Update document" },
];

export default function NodePalette() {
  const onDragStart = (event: React.DragEvent, nodeType: string) => {
    event.dataTransfer.setData("application/reactflow", nodeType);
    event.dataTransfer.effectAllowed = "move";
  };

  return (
    <div className="w-48 border-r border-secondary-200 bg-secondary-50 p-3">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-secondary-500">Nodes</h3>
      <div className="space-y-2">
        {NODE_TYPES.map((node) => (
          <div
            key={node.type}
            draggable
            onDragStart={(e) => onDragStart(e, node.type)}
            className="flex cursor-grab items-center gap-2 rounded-md border border-secondary-200 bg-white px-3 py-2 text-sm hover:shadow-md active:cursor-grabbing"
          >
            <span className={`h-3 w-3 rounded-full ${node.color}`} />
            <div>
              <p className="text-xs font-medium text-secondary-800">{node.label}</p>
              <p className="text-[10px] text-secondary-400">{node.description}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
