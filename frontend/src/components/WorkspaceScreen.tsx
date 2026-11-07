import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listRuns, stopRun } from "../api/client";
import { useLiveRun } from "../hooks/useLiveRun";
import type { RunSnapshot } from "../types/api";
import { InvestigationGraph } from "./InvestigationGraph";
import { Inspector } from "./Inspector";

function GhostMark({ small = false }: { small?: boolean }) {
  return (
    <span className={`ghost-mark ${small ? "small" : ""}`} aria-hidden="true">
      <svg viewBox="0 0 32 32">
        <path d="M7 25.5V14.2C7 8.7 10.7 5 16 5s9 3.7 9 9.2v11.3l-4-2.7-5 3.2-5-3.2-4 2.7Z" fill="currentColor" />
        <circle cx="12.5" cy="14" r="1.5" fill="#0d0d10" />
        <circle cx="19.5" cy="14" r="1.5" fill="#0d0d10" />
      </svg>
    </span>
  );
}

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

function elapsed(ms: number): string {
  const total = Math.max(0, Math.round(ms / 1000));
  return `${Math.floor(total / 60)}m ${String(total % 60).padStart(2, "0")}s`;
}

function hostOf(url: string): string {
  try {
    return new URL(url).host;
  } catch {
    return url || "Local target";
  }
}

function titleOf(snapshot: RunSnapshot): string {
  return hostOf(snapshot.task.url || "");
}

function statusLabel(status: string): string {
  if (status === "queued" || status === "running") return "Running";
  if (status === "passed") return "Passed";
  if (status === "failed") return "Failed";
  if (status === "stopped") return "Stopped";
  return status;
}

export function WorkspaceScreen({ runId }: { runId?: string }) {
  const [resolvedId, setResolvedId] = useState<string | undefined>(runId);
  const [listError, setListError] = useState<string | null>(null);
  const [stopping, setStopping] = useState(false);
  const { snapshot, loading, fetchError, reload } = useLiveRun(resolvedId);

  useEffect(() => {
    if (runId) {
      setResolvedId(runId);
      return;
    }
    void listRuns()
      .then((runs) => {
        const preferred =
          runs.find((run) => run.status === "running" || run.status === "queued") ??
          runs.find((run) => run.status === "passed") ??
          runs[0];
        setResolvedId(preferred?.id);
      })
      .catch((error: unknown) => setListError(error instanceof Error ? error.message : "Could not load runs"));
  }, [runId]);

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const live = snapshot?.status === "queued" || snapshot?.status === "running";
  const issues = snapshot?.projection.checks.filter((check) => check.status === "failed").length ?? 0;
  const best = snapshot?.projection.bestVerified?.status === "passed" ? snapshot.projection.bestVerified : null;
  const verified = best ? best.interactions : null;
  const selectedNode = snapshot?.projection.nodes.find((node) => node.id === selectedNodeId) ?? null;
  const activity = (snapshot?.projection.activity ?? []).filter((item) => item.summary && item.summary !== "Recorded browser work").slice(-4).reverse();
  const displayError = listError || fetchError || snapshot?.error || null;

  async function handleStop() {
    if (!snapshot) return;
    setStopping(true);
    try {
      await stopRun(snapshot.id);
      await reload();
    } finally {
      setStopping(false);
    }
  }

  return (
    <div className="figma-workspace">
      <section className="hero">
        <div className="hero-copy">
          <div className="kicker">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="m12 3 1.2 4.1a5 5 0 0 0 3.5 3.5L21 12l-4.3 1.4a5 5 0 0 0-3.5 3.5L12 21l-1.2-4.1a5 5 0 0 0-3.5-3.5L3 12l4.3-1.4a5 5 0 0 0 3.5-3.5L12 3Z" /></svg>
            Autonomous product intelligence
          </div>
          <h1>See your product through <span>new eyes.</span></h1>
          <p>Paste a URL, launch multiple personas, and watch them browse, screenshot pages, and record what they witnessed.</p>
        </div>
        <Link className="new-run" to="/?new=1">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
          New exploration
        </Link>
      </section>

      <section className="run-overview">
        <div className="run-main">
          <div className="site-icon" aria-hidden="true">
            <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" /></svg>
          </div>
          <div className="site-info">
            <div className="site-line">
              <h3>{snapshot ? titleOf(snapshot) : "No investigation yet"}</h3>
              {snapshot && <span className={`running-pill ${snapshot.status}`}><i />{statusLabel(snapshot.status)}</span>}
            </div>
            <p>
              {snapshot ? hostOf(snapshot.task.url) : "Start a new exploration with any URL you want investigated."}
              {snapshot?.task.objective ? <><span>·</span>{snapshot.task.objective}</> : null}
            </p>
          </div>
        </div>
        <div className="run-meta">
          <span><b>{snapshot ? snapshot.usage.browserActions : "—"}</b> / {snapshot?.budget.browserActions ?? "—"} browser actions</span>
          <span><b>{snapshot ? statusLabel(snapshot.status) : "—"}</b></span>
          <span><b>{snapshot ? elapsed(snapshot.usage.elapsedMs) : "0m 00s"}</b> elapsed</span>
        </div>
        {live ? (
          <button type="button" className="run-toggle" disabled={stopping} onClick={() => void handleStop()}>
            <span className="pause-icon" />
            Stop
          </button>
        ) : (
          <Link className="run-toggle" to="/runs">{snapshot ? "All runs" : "Runs"}</Link>
        )}
      </section>

      {displayError && <div className="error-banner" role="alert">{displayError}</div>}
      {loading && !snapshot && resolvedId && <p className="workspace-note">Loading the investigation…</p>}

      {snapshot && (
        <div className="run-links">
          <Link to={`/playback/${snapshot.id}`}>Recorded playback</Link>
          {snapshot.projection.bestVerified?.routeId && (
            <button
              type="button"
              className="btn"
              onClick={() => {
                const routeId = snapshot.projection.bestVerified?.routeId;
                if (!routeId) return;
                void fetch(`/api/routes/${routeId}/verify`, { method: "POST" }).then(() => reload());
              }}
            >
              New independent verification
            </button>
          )}
          <span>Playback reads this run. A new verification is a separate replay.</span>
        </div>
      )}

      <div className="workspace-grid">
        <InvestigationGraph nodes={snapshot?.projection.nodes ?? []} edges={snapshot?.projection.edges ?? []} live={live} onSelect={setSelectedNodeId} />
        <div className="witness-fallback">
          <h2>Witnessed steps</h2>
          {(snapshot?.projection.witness.length ? snapshot.projection.witness : snapshot?.projection.attempt ?? []).map((step) => (
            <p key={`${step.index}-${step.name}`}>{step.index}. {step.name} · {step.kind} · {step.interactions} interaction</p>
          ))}
          {!snapshot?.projection.witness.length && !snapshot?.projection.attempt?.length && <p>No witnessed steps yet.</p>}
        </div>
        <aside className="side-panel">
          <section className="metrics-card">
            <div className="section-title"><span>Live metrics</span></div>
            <div className="metrics-grid">
              <div><strong>{pad(snapshot?.projection.nodes.length ?? 0)}</strong><span>States found</span><small>{live ? "Updating" : "Witnessed"}</small></div>
              <div><strong>{pad(snapshot?.projection.edges.length ?? 0)}</strong><span>Transitions</span><small>{verified != null ? `${verified} verified` : "None verified"}</small></div>
              <div><strong>{pad(issues)}</strong><span>{issues === 1 ? "Issue" : "Issues"}</span><small className={issues ? "warn" : ""}>{issues ? "Needs review" : "None open"}</small></div>
              <div><strong>{verified ?? "—"}</strong><span>Verified steps</span><small className={snapshot?.status === "failed" ? "warn" : ""}>{best ? "passed" : snapshot?.projection.latestVerification?.status ?? snapshot?.status ?? "Waiting"}</small></div>
            </div>
          </section>
          <section className="activity-card">
            <div className="section-title">
              <span>Agent activity</span>
              {snapshot && <Link to={`/runs/${snapshot.id}`}>Open run</Link>}
            </div>
            <div className="agent-head">
              <div className="agent-orb"><GhostMark small /></div>
              <div>
                <b>{snapshot?.policyId || "Explorer"}</b>
                <span>{live ? snapshot?.projection.currentAction?.name || "Exploring" : snapshot ? statusLabel(snapshot.status) : "Idle"}</span>
              </div>
              <i className={live ? "pulse" : ""} />
            </div>
            <div className="timeline">
              {activity.length === 0 && <p className="workspace-note">Activity appears as the run witnesses states.</p>}
              {activity.map((item, index) => {
                const issue = /fail|left the allowed|error|issue/i.test(item.summary);
                return (
                  <div key={item.seq} className={`timeline-item ${index === 0 && live ? "current" : ""} ${issue ? "issue-event" : ""}`}>
                    <i>{issue ? "!" : ""}</i>
                    <div><b>{item.summary.replaceAll("_", " ")}</b></div>
                    <time>{item.seq}</time>
                  </div>
                );
              })}
            </div>
          </section>
        </aside>
      </div>
      {snapshot && (
        <Inspector
          projection={snapshot.projection}
          budget={snapshot.budget}
          usage={snapshot.usage}
          stopReason={snapshot.stopReason}
          selectedNode={selectedNode}
          onSelectStep={(name) => {
            const match = snapshot.projection.nodes.find((node) => node.label === name);
            setSelectedNodeId(match?.id ?? null);
          }}
        />
      )}
    </div>
  );
}
