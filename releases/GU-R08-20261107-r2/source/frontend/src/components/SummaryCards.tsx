import type { RunSnapshot } from "../types/api";

function formatUsd(value: number | null): string {
  if (value === null) return "unknown";
  return `$${value.toFixed(4)}`;
}

function formatStopReason(reason: string | null): string {
  if (!reason) return "—";
  return reason.replace(/_/g, " ");
}

interface Props {
  snapshot: RunSnapshot;
}

export function SummaryCards({ snapshot }: Props) {
  const { projection, usage, stopReason } = snapshot;
  const best = projection.bestVerified;
  const latest = projection.latestVerification;
  const verification = best?.status ?? latest?.status ?? null;
  const verificationColor =
    verification === "passed" ? "var(--verified)" : verification === "failed" ? "var(--failed)" : "inherit";

  return (
    <div className="summary-row">
      <div className="card">
        <h3>Best verified result</h3>
        {best ? (
          <div className="summary-value tabular">
            {best.interactions} interactions · {best.status}
          </div>
        ) : (
          <p className="summary-empty">No verified route yet</p>
        )}
      </div>
      <div className="card">
        <h3>Verification</h3>
        {verification ? (
          <div className="summary-value tabular" style={{ color: verificationColor }}>
            {verification}
          </div>
        ) : (
          <p className="summary-empty">Pending</p>
        )}
        {latest?.stale ? (
          <div style={{ color: "var(--deferred)", fontSize: "0.875rem" }}>Stale after a build change. Replay before trusting it.</div>
        ) : null}
      </div>
      <div className="card">
        <h3>Usage</h3>
        <div className="summary-value tabular">
          {usage.requests} req · {usage.browserActions} actions
        </div>
        <div className="tabular" style={{ color: "var(--secondary)", fontSize: "0.875rem" }}>
          {usage.elapsedMs} ms · spend {formatUsd(usage.spendingUSD)}
        </div>
      </div>
      <div className="card">
        <h3>Stop reason</h3>
        <div className="summary-value" style={{ fontSize: "1rem" }}>
          {formatStopReason(stopReason)}
        </div>
      </div>
    </div>
  );
}
