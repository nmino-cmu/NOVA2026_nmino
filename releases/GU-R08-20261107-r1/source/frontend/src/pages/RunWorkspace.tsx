import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { stopRun } from "../api/client";
import { Inspector } from "../components/Inspector";
import { InvestigationGraph } from "../components/InvestigationGraph";
import { SummaryCards } from "../components/SummaryCards";
import { useLiveRun } from "../hooks/useLiveRun";
import type { GraphNode } from "../types/api";

export function RunWorkspace() {
  const { id } = useParams<{ id: string }>();
  const { snapshot, loading, fetchError, reload } = useLiveRun(id);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [stopping, setStopping] = useState(false);

  const selectedNode: GraphNode | null = useMemo(() => {
    if (!snapshot || !selectedId) return null;
    return snapshot.projection.nodes.find((n) => n.id === selectedId) ?? null;
  }, [snapshot, selectedId]);

  const displayError = fetchError || snapshot?.error || null;
  const live =
    snapshot?.status === "queued" || snapshot?.status === "running";

  async function handleStop() {
    if (!id) return;
    setStopping(true);
    try {
      await stopRun(id);
      await reload();
    } finally {
      setStopping(false);
    }
  }

  function selectNode(nodeId: string) {
    setSelectedId(nodeId);
    setDrawerOpen(true);
  }

  if (!id) {
    return <div className="error-banner">Missing run id.</div>;
  }

  if (loading && !snapshot) {
    return (
      <div>
        <h1 style={{ marginTop: 0 }}>Investigation workspace</h1>
        <p style={{ color: "var(--secondary)" }}>Loading run…</p>
      </div>
    );
  }

  if (!snapshot) {
    return (
      <div>
        <h1 style={{ marginTop: 0 }}>Investigation workspace</h1>
        <div className="error-banner">{displayError ?? "Run not found."}</div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 8, marginBottom: 16 }}>
        <h1 style={{ margin: 0, flex: 1 }}>{snapshot.label || "Investigation workspace"}</h1>
        {live && (
          <button type="button" className="btn btn-danger" disabled={stopping} onClick={() => void handleStop()}>
            Stop
          </button>
        )}
      </div>

      {displayError && <div className="error-banner" role="alert">{displayError}</div>}

      <div className="meta-row">
        <span>Status: {snapshot.status}</span>
        <span>Build: {snapshot.buildId}</span>
        <span>Policy: {snapshot.policyId}</span>
        <span>
          Route budget: <span className="tabular">{snapshot.budget.routeActions}</span>
        </span>
      </div>

      <p style={{ color: "var(--secondary)", marginTop: 0 }}>
        {snapshot.task.objective || "No objective"} · {snapshot.task.task || "No task text"}
      </p>

      <SummaryCards snapshot={snapshot} />

      <div className="workspace-grid">
        <div>
          <InvestigationGraph
            nodes={snapshot.projection.nodes}
            edges={snapshot.projection.edges}
            selectedId={selectedId}
            onSelect={selectNode}
          />
          <section className="witness-mobile card" style={{ marginTop: 16 }}>
            <h2 style={{ marginTop: 0, fontSize: "1rem" }}>Witness list</h2>
            <ul className="witness-list">
              {snapshot.projection.witness.map((w) => {
                const node = snapshot.projection.nodes.find((n) => n.label === w.name);
                const active = node && node.id === selectedId;
                return (
                  <li key={w.index}>
                    <button
                      type="button"
                      className={active ? "selected" : ""}
                      onClick={() => node && selectNode(node.id)}
                    >
                      <span className="tabular">
                        {w.index}. {w.name}
                      </span>{" "}
                      <span style={{ color: "var(--secondary)" }}>{w.outcome}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </section>
          <button type="button" className="btn inspector-open-btn" onClick={() => setDrawerOpen(true)}>
            Open inspector
          </button>
        </div>
        <Inspector
          projection={snapshot.projection}
          selectedNode={selectedNode}
          className="desktop-inspector"
          onSelectStep={(name) => {
            const node = snapshot.projection.nodes.find((item) => item.label === name);
            if (node) selectNode(node.id);
          }}
        />
      </div>

      <div className={`inspector-drawer-backdrop ${drawerOpen ? "open" : ""}`} onClick={() => setDrawerOpen(false)} />
      <Inspector
        projection={snapshot.projection}
        selectedNode={selectedNode}
        className={`inspector-panel inspector-drawer ${drawerOpen ? "open" : ""}`}
        onSelectStep={(name) => {
          const node = snapshot.projection.nodes.find((item) => item.label === name);
          if (node) selectNode(node.id);
        }}
        onClose={() => setDrawerOpen(false)}
      />

    </div>
  );
}
