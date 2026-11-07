import { useMemo, useRef, useState } from "react";
import { evidenceUrl } from "../api/client";
import type { GraphEdge, GraphNode, NodeStatus } from "../types/api";

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
  live?: boolean;
  onSelect?: (id: string) => void;
}

interface Placed extends GraphNode {
  left: number;
  top: number;
  delay: number;
}

function place(nodes: GraphNode[]): Placed[] {
  return [...nodes]
    .sort((a, b) => a.x - b.x || a.y - b.y || a.seq - b.seq)
    .map((node, index) => ({ ...node, left: node.x, top: node.y, delay: index * 40 }));
}

function tone(status: NodeStatus): string {
  if (status === "failed") return "issue";
  if (status === "current") return "active";
  if (status === "verified") return "verified";
  return "";
}

function curve(from: Placed, to: Placed): string {
  const dir = Math.sign(to.left - from.left) || 1;
  const bend = Math.max(48, Math.abs(to.left - from.left) * 0.42);
  return `M${from.left + dir * 36},${from.top} C${from.left + dir * bend},${from.top} ${to.left - dir * bend},${to.top} ${to.left - dir * 36},${to.top}`;
}

function NodeIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true">
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  );
}

export function InvestigationGraph({ nodes: apiNodes, edges: apiEdges, live = false, onSelect }: Props) {
  const placed = useMemo(() => place(apiNodes), [apiNodes]);
  const byId = useMemo(() => new Map(placed.map((node) => [node.id, node])), [placed]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const stageRef = useRef<HTMLDivElement>(null);
  const width = Math.max(640, ...placed.map((node) => node.left + 230));
  const height = Math.max(360, ...placed.map((node) => node.top + 90));
  function choose(id: string) {
    setSelectedId(id);
    onSelect?.(id);
  }
  const selected = placed.find((node) => node.id === selectedId) ?? placed.find((node) => node.status === "current") ?? placed.at(-1) ?? null;
  const liveEdgeId = live
    ? apiEdges.find((edge) => byId.get(edge.target)?.status === "current")?.id ?? apiEdges.at(-1)?.id
    : null;

  return (
    <section className="graph-card" aria-label="Exploration map">
      <div className="graph-toolbar">
        <div>
          <div className="eyebrow">
            <span className={live ? "live-dot" : "status-dot"} />
            State graph{live ? " · Live" : ""}
          </div>
          <h2>Exploration map</h2>
        </div>
        <div className="graph-tools">
          <button type="button" className="btn" onClick={() => setZoom(1)}>100%</button>
          <button type="button" className="btn" onClick={() => setZoom((value) => Math.min(1.6, value + 0.2))}>Zoom in</button>
          <button type="button" className="btn" onClick={() => setZoom((value) => Math.max(0.6, value - 0.2))}>Zoom out</button>
          <button type="button" className="btn" onClick={() => setZoom(Math.min(1, ((stageRef.current?.clientWidth || 860) - 24) / width))}>Fit</button>
          <span className="tool-label">{placed.length} states</span>
        </div>
      </div>
      <div className="graph-stage" ref={stageRef}>
        <div className="graph-grid" />
        {placed.length === 0 ? (
          <p className="graph-empty">The map fills in as states are witnessed.</p>
        ) : (
          <>
            <div style={{ width: width * zoom, height: height * zoom }}>
            <div className="graph-canvas" style={{ width, height, transform: `scale(${zoom})`, transformOrigin: "top left" }}>
            <svg className="connections" viewBox={`0 0 ${width} ${height}`} style={{ width, height }} aria-hidden="true">
              <defs>
                <linearGradient id="edgeGlow" x1="0" x2="1">
                  <stop offset="0" stopColor="#7772ff" stopOpacity="0.18" />
                  <stop offset="0.5" stopColor="#918cff" stopOpacity="0.8" />
                  <stop offset="1" stopColor="#7772ff" stopOpacity="0.16" />
                </linearGradient>
              </defs>
              {apiEdges.map((edge) => {
                const from = byId.get(edge.source);
                const to = byId.get(edge.target);
                if (!from || !to) return null;
                return (
                  <path
                    key={edge.id}
                    d={curve(from, to)}
                    className={edge.id === liveEdgeId ? "edge active-edge" : "edge"}
                  />
                );
              })}
            </svg>
            {placed.map((node) => (
              <button
                key={node.id}
                type="button"
                className={`graph-node anchored ${tone(node.status)} ${selected?.id === node.id ? "selected" : ""} ${node.status === "current" ? "discovering" : ""}`}
                style={{ left: node.left, top: node.top, "--delay": `${node.delay}ms` } as React.CSSProperties}
                onClick={() => choose(node.id)}
              >
                <span className="node-icon"><NodeIcon /></span>
                <span className="node-copy">
                  <b>{node.label}</b>
                  <small>{node.freshness === "stale" ? "stale" : node.status}</small>
                </span>
                {node.status === "failed" && <i>!</i>}
              </button>
            ))}
            </div>
            </div>
          </>
        )}
        <ol className="route-inspection">
          {apiEdges.map((edge, index) => (
            <li key={edge.id}>
              <button type="button" onClick={() => choose(edge.target)}>
                {index + 1}. {edge.label || "transition"}
              </button>
            </li>
          ))}
        </ol>
        <div className="graph-legend">
          <span><i className="verified-swatch" />Verified</span>
          <span><i className="active-swatch" />Exploring</span>
          <span><i className="issue-swatch" />Issue</span>
        </div>
        {selected && (
          <aside className="node-detail">
            <div className="detail-top">
              <span>{selected.status}</span>
              <button type="button" aria-label="Close details" onClick={() => setSelectedId(null)}>×</button>
            </div>
            <h3>{selected.label}</h3>
            {selected.action ? <p>Action: {selected.action}</p> : null}
            <p>
              {selected.reason
                || (selected.outcome === "blocked"
                  ? "This action was blocked."
                  : selected.status === "current"
                    ? "The investigation is on this state now."
                    : "A witnessed state from the runner.")}
            </p>
            {selected.url ? <p><a href={selected.url}>{selected.url}</a></p> : null}
            {selected.check ? <p>Check: {selected.checkOk ? "passed" : "failed"}. {selected.check}</p> : null}
            {selected.screenshotId ? (
              <figure>
                <a href={evidenceUrl(selected.screenshotId)}>
                  <img src={evidenceUrl(selected.screenshotId)} alt={`Screenshot after ${selected.label}`} />
                </a>
                <figcaption>{selected.outcome || selected.status}</figcaption>
              </figure>
            ) : null}
            <div className="detail-row">
              <span>Order</span>
              <b>{selected.seq || "—"}</b>
            </div>
          </aside>
        )}
      </div>
    </section>
  );
}
