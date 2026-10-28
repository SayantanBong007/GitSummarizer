import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import dagre from "@dagrejs/dagre";
import { Loader2 } from "lucide-react";
import { getRepoGraph } from "@/api/client";
import type { GraphEdge, GraphNode } from "@/types";

interface Props {
  repositoryId: string;
  // Fallback in-memory data used when Neo4j has nothing yet
  fallbackNodes?: GraphNode[];
  fallbackEdges?: GraphEdge[];
}

const TYPE_COLORS: Record<string, string> = {
  File:        "#6366f1",
  Module:      "#8b5cf6",
  Function:    "#06b6d4",
  Class:       "#f59e0b",
  APIEndpoint: "#10b981",
  DBTable:     "#ef4444",
  Service:     "#f97316",
};

const NODE_WIDTH = 180;
const NODE_HEIGHT = 34;

// Real graph layout, driven by actual edges (dagre), not just node type.
// Any node dagre can't place (fully isolated, no edges at all) is stacked in
// a column off to the side instead of left at the default (0, 0).
function computePositions(
  nodes: GraphNode[],
  edges: GraphEdge[]
): Map<string, { x: number; y: number }> {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: "LR", nodesep: 28, ranksep: 110, marginx: 20, marginy: 20 });
  g.setDefaultEdgeLabel(() => ({}));

  for (const n of nodes) {
    g.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  }
  for (const e of edges) {
    g.setEdge(e.source_id, e.target_id);
  }

  dagre.layout(g);

  const result = new Map<string, { x: number; y: number }>();
  let unplacedRow = 0;
  for (const n of nodes) {
    const pos = g.node(n.id);
    if (pos) {
      // dagre positions are node centers; ReactFlow wants top-left corners.
      result.set(n.id, { x: pos.x - NODE_WIDTH / 2, y: pos.y - NODE_HEIGHT / 2 });
    } else {
      // Isolated node with no edges -- dagre won't place it. Stack these off
      // to the side instead of leaving them at (0, 0) on top of everything else.
      result.set(n.id, { x: -260, y: unplacedRow * (NODE_HEIGHT + 12) });
      unplacedRow += 1;
    }
  }
  return result;
}

// Cap total nodes to keep ReactFlow performant
const MAX_NODES = 150;
const MAX_EDGES = 400;

export default function GraphViewer({ repositoryId, fallbackNodes = [], fallbackEdges = [] }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ["repo-graph", repositoryId],
    queryFn:  () => getRepoGraph(repositoryId),
    staleTime: 5 * 60 * 1000,
  });

  const rawNodes: GraphNode[] = (data?.nodes?.length ? data.nodes : fallbackNodes);
  const rawEdges: GraphEdge[] = (data?.edges?.length ? data.edges : fallbackEdges);

  // Prioritise structural nodes (Module, Class, APIEndpoint, DBTable) over leaf nodes
  const TYPE_PRIORITY: Record<string, number> = {
    Module: 0, Class: 1, APIEndpoint: 2, DBTable: 3, Service: 4, File: 5, Function: 6,
  };
  const nodes = [...rawNodes]
    .sort((a, b) => (TYPE_PRIORITY[a.type] ?? 9) - (TYPE_PRIORITY[b.type] ?? 9))
    .slice(0, MAX_NODES);

  const nodeIds = new Set(nodes.map((n) => n.id));
  // Only include edges where both endpoints are visible
  const edges = rawEdges
    .filter((e) => nodeIds.has(e.source_id) && nodeIds.has(e.target_id))
    .slice(0, MAX_EDGES);

  const positions = useMemo(() => computePositions(nodes, edges), [nodes, edges]);

  const flowNodes: Node[] = useMemo(
    () =>
      nodes.map((n) => ({
        id: n.id,
        data: { label: n.name },
        position: positions.get(n.id) ?? { x: 0, y: 0 },
        style: {
          background: TYPE_COLORS[n.type] ?? "#94a3b8",
          color: "#fff",
          border: "none",
          borderRadius: 8,
          fontSize: 11,
          padding: "6px 10px",
          maxWidth: 180,
          whiteSpace: "nowrap" as const,
          overflow: "hidden",
          textOverflow: "ellipsis",
        },
      })),
    [nodes, positions]
  );

  const flowEdges: Edge[] = useMemo(
    () =>
      edges.map((e, i) => ({
        id: `e-${i}`,
        source: e.source_id,
        target: e.target_id,
        label: e.relationship,
        style: { stroke: "#cbd5e1", strokeWidth: 1.5 },
        labelStyle: { fontSize: 9, fill: "#94a3b8" },
        animated: e.relationship === "CALLS",
      })),
    [edges]
  );

  if (isLoading) {
    return (
      <div className="h-[560px] flex items-center justify-center bg-slate-50 rounded-xl border border-slate-200">
        <div className="flex flex-col items-center gap-2 text-slate-400">
          <Loader2 size={24} className="animate-spin" />
          <span className="text-sm">Loading knowledge graph…</span>
        </div>
      </div>
    );
  }

  if (nodes.length === 0) {
    return (
      <div className="h-96 flex flex-col items-center justify-center gap-2 text-slate-400 text-sm bg-slate-50 rounded-xl border border-slate-200">
        <span>Knowledge graph not yet available.</span>
        <span className="text-xs text-slate-300">Run a re-analysis to populate the graph.</span>
      </div>
    );
  }

  const source = data?.nodes?.length ? "Neo4j" : "local";
  const truncated = rawNodes.length > MAX_NODES;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs text-slate-400 px-1">
        <span>
          {nodes.length} nodes · {edges.length} edges
          {truncated && <span className="ml-1 text-slate-300">(showing {MAX_NODES} of {rawNodes.length})</span>}
        </span>
        <span className={source === "Neo4j" ? "text-indigo-500 font-medium" : "text-slate-300"}>
          {source === "Neo4j" ? "Live Neo4j graph" : "In-memory (re-analyze to populate Neo4j)"}
        </span>
      </div>
      <div className="h-[560px] border border-slate-200 rounded-xl overflow-hidden">
        <ReactFlow nodes={flowNodes} edges={flowEdges} fitView>
          <Background />
          <Controls />
          <MiniMap nodeColor={(n) => (n.style?.background as string) ?? "#94a3b8"} />
        </ReactFlow>
      </div>
    </div>
  );
}
