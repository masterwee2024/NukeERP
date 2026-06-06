import { useState, useCallback, useRef, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import {
  ReactFlow,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  MiniMap,
  type Node,
  type Edge,
  type Connection,
} from "reactflow";
import "reactflow/dist/style.css";
import NodePalette from "@/components/workflow/NodePalette";

const DOCUMENT_TYPE_OPTIONS = [
  { value: "", label: "-- Select document type --" },
  { value: "financial.JournalEntry", label: "Journal Entry" },
  { value: "scm.PurchaseOrder", label: "Purchase Order" },
  { value: "scm.SalesOrder", label: "Sales Order" },
  { value: "scm.GoodsReceiptNote", label: "Goods Receipt Note" },
  { value: "scm.DeliveryOrder", label: "Delivery Order" },
  { value: "crm.Quotation", label: "Quotation" },
  { value: "crm.CustomerInvoice", label: "Customer Invoice" },
  { value: "hrm.LeaveRequest", label: "Leave Request" },
  { value: "hrm.Claim", label: "Claim" },
  { value: "hrm.ExpenseReport", label: "Expense Report" },
  { value: "mrp.WorkOrder", label: "Work Order" },
  { value: "assets.AssetDisposal", label: "Asset Disposal" },
  { value: "treasury.Payment", label: "Payment" },
  { value: "treasury.Receipt", label: "Receipt" },
];

const initialNodes: Node[] = [
  {
    id: "start-1",
    type: "default",
    position: { x: 250, y: 50 },
    data: { label: "Start" },
    style: { background: "#22c55e", color: "#fff", border: "2px solid #16a34a", borderRadius: "50%", width: 60, height: 60, display: "flex", alignItems: "center", justifyContent: "center" },
  },
];

const initialEdges: Edge[] = [];

const nodeTypeStyles: Record<string, { bg: string; border: string; shape: string }> = {
  start: { bg: "#22c55e", border: "#16a34a", shape: "circle" },
  end: { bg: "#ef4444", border: "#dc2626", shape: "circle" },
  approve: { bg: "#3b82f6", border: "#2563eb", shape: "diamond" },
  condition: { bg: "#eab308", border: "#ca8a04", shape: "hexagon" },
  notify: { bg: "#a855f7", border: "#9333ea", shape: "triangle" },
  action: { bg: "#6b7280", border: "#4b5563", shape: "square" },
};

function createNode(nodeType: string, x: number, y: number): Node {
  const style = nodeTypeStyles[nodeType] || nodeTypeStyles.action;
  return {
    id: `${nodeType}-${Date.now()}`,
    type: "default",
    position: { x, y },
    data: { label: nodeType.charAt(0).toUpperCase() + nodeType.slice(1) },
    style: {
      background: style.bg,
      color: "#fff",
      border: `2px solid ${style.border}`,
      borderRadius: "8px",
      padding: "10px 20px",
      minWidth: 120,
    },
  };
}

const nodeTypes = {};

export default function WorkflowDesignerPage() {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [name, setName] = useState("New Workflow");
  const [module, setModule] = useState("");
  const [docType, setDocType] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [workflowId, setWorkflowId] = useState<string | null>(null);

  const selectedNode = selectedNodeId ? nodes.find((n) => n.id === selectedNodeId) ?? null : null;

  const { data: workflows } = useQuery<{ count: number; results: Array<{ id: string; name: string; document_type: string }> }>({
    queryKey: ["workflows"],
    queryFn: () => api.get("/core/admin/workflows/").then((r) => r.data),
    staleTime: 30_000,
  });

  const { data: workflowDetail } = useQuery({
    queryKey: ["workflow-detail", workflowId],
    queryFn: () => api.get(`/core/admin/workflows/${workflowId}/`).then((r) => r.data),
    enabled: !!workflowId,
  });

  // Load workflow detail into canvas when fetched
  useEffect(() => {
    if (!workflowDetail) return;
    setName(workflowDetail.name);
    setModule(workflowDetail.module);
    setDocType(workflowDetail.document_type);
    setNodes(
      workflowDetail.nodes.map((n: { node_id: string; node_type: string; label: string; position_x: number; position_y: number; config: Record<string, unknown> }) => {
        const style = nodeTypeStyles[n.node_type] || nodeTypeStyles.action;
        return {
          id: n.node_id,
          type: "default",
          position: { x: n.position_x, y: n.position_y },
          data: { label: n.label, config: n.config },
          style: {
            background: style.bg,
            color: "#fff",
            border: `2px solid ${style.border}`,
            borderRadius: "8px",
            padding: "10px 20px",
            minWidth: 120,
          },
        } as Node;
      })
    );
    setEdges(
      workflowDetail.edges.map((e: { source_node_id: string; target_node_id: string; label?: string; condition?: Record<string, unknown> }) => ({
        id: `${e.source_node_id}-${e.target_node_id}`,
        source: e.source_node_id,
        target: e.target_node_id,
        label: e.label || "",
      }))
    );
  }, [workflowDetail, setNodes, setEdges]);

  // Delete selected node on Delete/Backspace key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.key === "Delete" || e.key === "Backspace") && selectedNodeId) {
        setNodes((nds) => nds.filter((n) => n.id !== selectedNodeId));
        setEdges((eds) => eds.filter((ed) => ed.source !== selectedNodeId && ed.target !== selectedNodeId));
        setSelectedNodeId(null);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [selectedNodeId, setNodes, setEdges]);

  const loadWorkflow = (id: string) => {
    if (!id) return;
    setWorkflowId(id);
    setSelectedNodeId(null);
  };

  const newWorkflow = () => {
    setWorkflowId(null);
    setName("New Workflow");
    setModule("");
    setDocType("");
    setNodes([{ ...initialNodes[0], id: "start-1", position: { x: 250, y: 50 }, data: { label: "Start" } }]);
    setEdges([]);
    setSelectedNodeId(null);
    setMessage("");
  };

  const deleteSelectedNode = () => {
    if (!selectedNodeId) return;
    setNodes((nds) => nds.filter((n) => n.id !== selectedNodeId));
    setEdges((eds) => eds.filter((ed) => ed.source !== selectedNodeId && ed.target !== selectedNodeId));
    setSelectedNodeId(null);
  };

  const { data: roles } = useQuery<Array<{ id: string; name: string }>>({
    queryKey: ["roles"],
    queryFn: () => api.get("/core/admin/roles/").then((r) => r.data),
    staleTime: 60_000,
  });

  const { data: users } = useQuery<Array<{ id: string; email: string; full_name: string }>>({
    queryKey: ["users"],
    queryFn: () => api.get("/core/admin/users/").then((r) => r.data),
    staleTime: 60_000,
  });

  const updateNodeConfig = (nodeId: string, patch: Record<string, unknown>) => {
    setNodes((nds) =>
      nds.map((n) =>
        n.id === nodeId
          ? { ...n, data: { ...n.data, config: { ...((n.data as Record<string, unknown>).config as Record<string, unknown> || {}), ...patch } } }
          : n
      )
    );
  };

  const addApprover = (nodeId: string) => {
    const node = nodes.find((n) => n.id === nodeId);
    if (!node) return;
    const config = ((node.data as Record<string, unknown>).config as Record<string, unknown> || {}) as Record<string, unknown>;
    const approvers: Array<{ type: string; id: string }> = (config.approvers as Array<{ type: string; id: string }>) || [];
    updateNodeConfig(nodeId, { approvers: [...approvers, { type: "role", id: "" }] });
  };

  const removeApprover = (nodeId: string, idx: number) => {
    const node = nodes.find((n) => n.id === nodeId);
    if (!node) return;
    const config = ((node.data as Record<string, unknown>).config as Record<string, unknown> || {}) as Record<string, unknown>;
    const approvers: Array<{ type: string; id: string }> = (config.approvers as Array<{ type: string; id: string }>) || [];
    updateNodeConfig(nodeId, { approvers: approvers.filter((_, i) => i !== idx) });
  };

  const updateApprover = (nodeId: string, idx: number, field: string, value: string) => {
    const node = nodes.find((n) => n.id === nodeId);
    if (!node) return;
    const config = ((node.data as Record<string, unknown>).config as Record<string, unknown> || {}) as Record<string, unknown>;
    const approvers: Array<{ type: string; id: string }> = (config.approvers as Array<{ type: string; id: string }>) || [];
    const updated = approvers.map((a, i) => (i === idx ? { ...a, [field]: value } : a));
    updateNodeConfig(nodeId, { approvers: updated });
  };

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges],
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const nodeType = event.dataTransfer.getData("application/reactflow");
      if (!nodeType || !reactFlowWrapper.current) return;

      const bounds = reactFlowWrapper.current.getBoundingClientRect();
      const position = {
        x: event.clientX - bounds.left - 60,
        y: event.clientY - bounds.top - 20,
      };

      const newNode = createNode(nodeType, position.x, position.y);
      setNodes((nds) => nds.concat(newNode));
    },
    [setNodes],
  );

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNodeId(node.id);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
  }, []);

  const handleSave = async () => {
    if (!name.trim() || !module || !docType) {
      setMessage("Name, Module, and Document Type are required");
      return;
    }
    setSaving(true);
    setMessage("");

    try {
      const body = {
        name,
        module,
        document_type: docType,
        flow_data: { nodes, edges },
        nodes: nodes.map((n) => ({
          node_id: n.id,
          node_type: n.id.split("-")[0],
          label: (n.data as Record<string, unknown>).label as string,
          position_x: n.position.x,
          position_y: n.position.y,
          config: ((n.data as Record<string, unknown>).config as Record<string, unknown>) || {},
        })),
        edges: edges.map((e) => ({
          source_node_id: e.source,
          target_node_id: e.target,
          label: (e as Record<string, unknown>).label as string || "",
          condition: {},
        })),
      };

      if (workflowId) {
        await api.put(`/core/admin/workflows/${workflowId}/`, body);
        setMessage("Workflow updated");
      } else {
        const { data } = await api.post("/core/admin/workflows/", body);
        setWorkflowId(data.id);
        setMessage(`Saved! ID: ${data.id?.slice(0, 8)}`);
      }
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setMessage(typeof detail === "string" ? detail : JSON.stringify(err?.response?.data || err.message));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      <NodePalette />

      <div className="flex flex-1 flex-col">
        {/* Toolbar */}
        <div className="flex items-center gap-3 border-b border-secondary-200 bg-white px-4 py-2">
          <select
            value={workflowId || ""}
            onChange={(e) => e.target.value ? loadWorkflow(e.target.value) : newWorkflow()}
            className="rounded border border-secondary-300 px-2 py-1 text-sm min-w-[160px]"
          >
            <option value="">-- New workflow --</option>
            {workflows?.results.map((w) => (
              <option key={w.id} value={w.id}>{w.name}</option>
            ))}
          </select>
          <div className="w-px h-6 bg-secondary-300" />
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="rounded border border-secondary-300 px-2 py-1 text-sm focus:border-primary-500 focus:outline-none"
            placeholder="Workflow name"
          />
          <select
            value={module}
            onChange={(e) => setModule(e.target.value)}
            className="rounded border border-secondary-300 px-2 py-1 text-sm"
          >
            <option value="">Module</option>
            <option value="financial">Financial</option>
            <option value="scm">Supply Chain</option>
            <option value="crm">CRM</option>
            <option value="mrp">MRP</option>
            <option value="hrm">HRM</option>
          </select>
          <select
            value={docType}
            onChange={(e) => setDocType(e.target.value)}
            className="rounded border border-secondary-300 px-2 py-1 text-sm"
          >
            {DOCUMENT_TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded bg-primary-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save"}
          </button>
          {message && (
            <span className={`text-xs ${message.includes("Saved") ? "text-green-600" : "text-red-600"}`}>
              {message}
            </span>
          )}
        </div>

        {/* React Flow Canvas */}
        <div ref={reactFlowWrapper} className="flex-1">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            nodeTypes={nodeTypes}
            fitView
          >
            <Controls />
            <Background />
            <MiniMap />
          </ReactFlow>
        </div>
      </div>

      {/* Properties Panel */}
      {selectedNode && (
        <div className="w-72 border-l border-secondary-200 bg-white p-4 overflow-y-auto">
          <h3 className="mb-3 text-sm font-semibold text-secondary-800">Properties</h3>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-secondary-500">Node ID</label>
              <p className="text-sm text-secondary-700">{selectedNode.id}</p>
            </div>
            <div>
              <label className="block text-xs font-medium text-secondary-500">Type</label>
              <p className="text-sm text-secondary-700">{selectedNode.id.split("-")[0]}</p>
            </div>
            <div>
              <label className="block text-xs font-medium text-secondary-500">Label</label>
              <input
                value={selectedNode.data.label as string}
                onChange={(e) => {
                  setNodes((nds) =>
                    nds.map((n) => (n.id === selectedNode.id ? { ...n, data: { ...n.data, label: e.target.value } } : n)),
                  );
                }}
                className="mt-1 w-full rounded border border-secondary-300 px-2 py-1 text-sm"
              />
            </div>

            {/* Approve node: approver config */}
            {selectedNode.id.startsWith("approve-") && (
              <div className="border-t border-secondary-200 pt-3">
                <label className="block text-xs font-medium text-secondary-500 mb-2">Approvers</label>
                {(() => {
                  const config = ((selectedNode.data as Record<string, unknown>).config as Record<string, unknown> || {}) as Record<string, unknown>;
                  const approvers: Array<{ type: string; id: string }> = (config.approvers as Array<{ type: string; id: string }>) || [];
                  return (
                    <>
                      {approvers.map((a, idx) => (
                        <div key={idx} className="mb-2 flex items-start gap-2">
                          <div className="flex-1">
                            <select
                              value={a.type}
                              onChange={(e) => updateApprover(selectedNode.id, idx, "type", e.target.value)}
                              className="w-full rounded border border-secondary-300 px-2 py-1 text-xs mb-1"
                            >
                              <option value="role">Role</option>
                              <option value="user">User</option>
                            </select>
                            <select
                              value={a.id}
                              onChange={(e) => updateApprover(selectedNode.id, idx, "id", e.target.value)}
                              className="w-full rounded border border-secondary-300 px-2 py-1 text-xs"
                            >
                              <option value="">-- Select --</option>
                              {a.type === "role"
                                ? roles?.map((r) => (
                                    <option key={r.id} value={r.id}>{r.name}</option>
                                  ))
                                : users?.map((u) => (
                                    <option key={u.id} value={u.id}>{u.full_name || u.email}</option>
                                  ))}
                            </select>
                          </div>
                          <button
                            onClick={() => removeApprover(selectedNode.id, idx)}
                            className="text-danger-500 hover:text-danger-700 text-sm leading-none mt-1"
                          >
                            ✕
                          </button>
                        </div>
                      ))}
                      <button
                        onClick={() => addApprover(selectedNode.id)}
                        className="text-xs text-primary-600 hover:text-primary-800"
                      >
                        + Add approver
                      </button>
                    </>
                  );
                })()}
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-secondary-500">X</label>
              <input
                type="number"
                value={Math.round(selectedNode.position.x)}
                onChange={(e) => {
                  const x = Number(e.target.value);
                  setNodes((nds) =>
                    nds.map((n) => (n.id === selectedNode.id ? { ...n, position: { ...n.position, x } } : n)),
                  );
                }}
                className="mt-1 w-full rounded border border-secondary-300 px-2 py-1 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-secondary-500">Y</label>
              <input
                type="number"
                value={Math.round(selectedNode.position.y)}
                onChange={(e) => {
                  const y = Number(e.target.value);
                  setNodes((nds) =>
                    nds.map((n) => (n.id === selectedNode.id ? { ...n, position: { ...n.position, y } } : n)),
                  );
                }}
                className="mt-1 w-full rounded border border-secondary-300 px-2 py-1 text-sm"
              />
            </div>
            <div className="border-t border-secondary-200 pt-3">
              <button
                onClick={deleteSelectedNode}
                className="w-full rounded border border-danger-300 bg-white px-3 py-1.5 text-sm text-danger-600 hover:bg-danger-50"
              >
                Delete node
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
