import {
  Background,
  Controls,
  ReactFlow,
  type Node,
  type Edge,
  useNodesState,
  useEdgesState,
  useReactFlow,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useCallback, useEffect, useMemo } from "react";
import type { GraphEdge, GraphNode, NodeStatus } from "../types/api";

function statusClass(status: NodeStatus): string {
  return `graph-node graph-node--${status}`;
}

function GraphNodeView({ data }: { data: { label: string; status: NodeStatus } }) {
  return <div className={statusClass(data.status)}>{data.label}</div>;
}

const nodeTypes = { investigation: GraphNodeView };

function FitView({ count }: { count: number }) {
  const { fitView } = useReactFlow();
  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      fitView({ padding: 0.2, duration: 0 });
    });
    return () => cancelAnimationFrame(frame);
  }, [count, fitView]);
  return null;
}

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function InvestigationGraph({ nodes: apiNodes, edges: apiEdges, selectedId, onSelect }: Props) {
  const mapped = useMemo(() => {
    const nodes: Node[] = apiNodes.map((n) => ({
      id: n.id,
      type: "investigation",
      position: { x: n.x, y: n.y },
      data: { label: n.label, status: n.status },
      selected: n.id === selectedId,
    }));
    const edges: Edge[] = apiEdges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.label,
      markerEnd: { type: MarkerType.ArrowClosed, color: "#2B3853" },
      style: { stroke: "#2B3853" },
      labelStyle: { fill: "#B5C2D8", fontSize: 11 },
    }));
    return { nodes, edges };
  }, [apiNodes, apiEdges, selectedId]);

  const [nodes, setNodes, onNodesChange] = useNodesState(mapped.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(mapped.edges);

  useEffect(() => {
    setNodes(mapped.nodes);
    setEdges(mapped.edges);
  }, [mapped, setNodes, setEdges]);

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      onSelect(node.id);
    },
    [onSelect],
  );

  return (
    <div className="graph-panel" style={{ height: 440 }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        nodeTypes={nodeTypes}
        fitView
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        nodesConnectable={false}
        panOnScroll
      >
        <FitView count={nodes.length} />
        <Background color="#2B3853" gap={16} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
