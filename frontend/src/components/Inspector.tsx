import type { Budget, GraphNode, Projection, Usage } from "../types/api";
import { evidenceUrl } from "../api/client";

function checkClass(status: string): string {
  const s = status.toLowerCase();
  if (s.includes("pass") || s === "verified") return "check-tag check-passed";
  if (s.includes("fail")) return "check-tag check-failed";
  return "check-tag check-pending";
}

interface Props {
  projection: Projection;
  budget?: Budget;
  usage?: Usage;
  stopReason?: string | null;
  selectedNode: GraphNode | null;
  onSelectStep?: (name: string) => void;
  onClose?: () => void;
  className?: string;
}

export function Inspector({ projection, budget, usage, stopReason, selectedNode, onSelectStep, onClose, className = "" }: Props) {
  const { currentAction, checks, evidence, activity, witness, decisions = [] } = projection;

  const nodeEvidence = (selectedNode
    ? evidence.filter((e) => e.label === selectedNode.label)
    : evidence.slice(0, 4)
  ).filter((item) => item.mediaType.startsWith("image/") || item.kind === "trace");

  return (
    <aside className={`inspector-panel ${className}`} aria-label="Inspector">
      {onClose && (
        <button type="button" className="btn" style={{ marginBottom: 8 }} onClick={onClose}>
          Close
        </button>
      )}
      <h2 style={{ margin: "0 0 8px", fontSize: "1rem" }}>Evidence</h2>
      {projection.identity && (
        <section style={{ marginBottom: 16 }}>
          <h3 style={{ margin: "0 0 8px", fontSize: "0.875rem", color: "var(--secondary)" }}>Identity</h3>
          <p>{projection.identity.goal}</p>
          <p style={{ color: "var(--secondary)" }}>
            {projection.identity.policyId} · build {projection.identity.buildId || "—"} · model {projection.identity.model || "—"} · prompt {projection.identity.promptSet || "—"}
          </p>
          {projection.identity.persona && <p>Persona {projection.identity.persona}</p>}
          {(projection.identity.queries || []).length > 0 && <p>Searches: {projection.identity.queries?.join(", ")}</p>}
        </section>
      )}
      {(budget || usage) && (
        <section style={{ marginBottom: 16 }}>
          <h3 style={{ margin: "0 0 8px", fontSize: "0.875rem", color: "var(--secondary)" }}>Budget</h3>
          <p>
            {usage?.browserActions ?? 0} / {budget?.browserActions ?? "—"} browser actions · {usage?.requests ?? 0} / {budget?.requests ?? "—"} requests · {usage?.resets ?? 0} resets · {usage?.elapsedMs ?? 0} ms
          </p>
          <p style={{ color: "var(--secondary)" }}>Stop: {stopReason || "—"} · tokens {usage?.tokenAccounting || "unknown"} · spend {usage?.spendingAccounting || "unknown"}</p>
          {projection.limitations.map((item) => <p key={item} style={{ color: "var(--secondary)" }}>{item}</p>)}
        </section>
      )}
      {projection.routes && (
        <section style={{ marginBottom: 16 }}>
          <h3 style={{ margin: "0 0 8px", fontSize: "0.875rem", color: "var(--secondary)" }}>Routes</h3>
          <p>Best verified: {projection.routes.best ? `${projection.routes.best.interactions} interactions, ${projection.routes.best.status}` : "none"}</p>
          <p>Failed attempts: {projection.routes.failed?.length ?? 0}. Historical: {projection.routes.historical?.length ?? 0}. Other candidates: {projection.routes.candidates?.length ?? 0}.</p>
          {(projection.routes.failed || []).map((item) => (
            <p key={item.verificationId} style={{ color: "var(--secondary)" }}>{item.detail}</p>
          ))}
          {(projection.routes.historical || []).map((item) => (
            <p key={item.verificationId}>Older {item.buildId || "build"} result, {item.interactions} interactions. Not the current result.</p>
          ))}
        </section>
      )}
      {selectedNode ? (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontWeight: 600 }}>{selectedNode.label}</div>
          <div style={{ color: "var(--secondary)", fontSize: "0.875rem" }}>
            Status: {selectedNode.status}
          </div>
        </div>
      ) : (
        <p style={{ color: "var(--secondary)" }}>Select a node or witness entry.</p>
      )}

      {currentAction && (
        <section style={{ marginBottom: 16 }}>
          <h3 style={{ margin: "0 0 8px", fontSize: "0.875rem", color: "var(--secondary)" }}>
            Current action
          </h3>
          <div style={{ fontWeight: 500 }}>{currentAction.name}</div>
          {currentAction.reason && (
            <p style={{ margin: "8px 0 0", color: "var(--secondary)", fontSize: "0.875rem" }}>
              {currentAction.reason}
            </p>
          )}
        </section>
      )}

      <section style={{ marginBottom: 16 }}>
        <h3 style={{ margin: "0 0 8px", fontSize: "0.875rem", color: "var(--secondary)" }}>Checks</h3>
        <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
          {checks.map((c) => (
            <li key={c.id} style={{ marginBottom: 8 }}>
              <span className={checkClass(c.status)}>{c.status}</span>
              {c.name}
              {c.detail ? (
                <div style={{ fontSize: "0.8125rem", color: "var(--secondary)" }}>{c.detail}</div>
              ) : null}
            </li>
          ))}
        </ul>
      </section>

      <section style={{ marginBottom: 16 }}>
        <h3 style={{ margin: "0 0 8px", fontSize: "0.875rem", color: "var(--secondary)" }}>
          Evidence
        </h3>
        {nodeEvidence.length === 0 ? (
          <p style={{ color: "var(--secondary)", fontSize: "0.875rem" }}>No images for selection.</p>
        ) : (
          nodeEvidence.map((ev) => (
            <figure key={ev.id}>
              <figcaption style={{ fontSize: "0.875rem", color: "var(--secondary)" }}>
                {ev.label}
              </figcaption>
              {ev.mediaType.startsWith("image/") ? (
                <img className="evidence-img" src={evidenceUrl(ev.id)} alt={ev.label} />
              ) : (
                <a href={evidenceUrl(ev.id)}>{ev.label} trace</a>
              )}
            </figure>
          ))
        )}
      </section>

      <section style={{ marginBottom: 16 }}>
        <h3 style={{ margin: "0 0 8px", fontSize: "0.875rem", color: "var(--secondary)" }}>Scheduler</h3>
        {decisions.length === 0 ? (
          <p style={{ color: "var(--secondary)", fontSize: "0.875rem" }}>No scheduler decisions on this run.</p>
        ) : (
          <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
            {decisions.map((item) => (
              <li key={item.id} style={{ marginBottom: 8 }}>
                <span className="check-tag">{item.kind}</span>
                <div style={{ fontSize: "0.8125rem", color: "var(--secondary)" }}>{item.reason}</div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section style={{ marginBottom: 16 }}>
        <h3 style={{ margin: "0 0 8px", fontSize: "0.875rem", color: "var(--secondary)" }}>
          Routes (witness)
        </h3>
        <ul className="route-list" role="list">
          {witness.map((w) => (
            <li key={w.index}>
              <button
                type="button"
                aria-label={`Route step ${w.index}: ${w.name}`}
                onClick={() => onSelectStep?.(w.name)}
              >
                <span className="tabular">
                  {w.index}. {w.name}
                </span>{" "}
                <span style={{ color: "var(--secondary)" }}>({w.outcome})</span>
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h3 style={{ margin: "0 0 8px", fontSize: "0.875rem", color: "var(--secondary)" }}>
          Activity
        </h3>
        <ul className="activity-list">
          {[...activity].reverse().slice(0, 20).map((a) => (
            <li key={a.seq}>
              <span className="tabular" style={{ color: "var(--secondary)", marginRight: 8 }}>
                #{a.seq}
              </span>
              {a.summary}
            </li>
          ))}
        </ul>
      </section>
    </aside>
  );
}
