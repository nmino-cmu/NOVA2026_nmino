import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listRuns } from "../api/client";
import type { RunListItem } from "../types/api";

export function RunLibrary() {
  const [runs, setRuns] = useState<RunListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    void listRuns()
      .then(setRuns)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load runs"));
  }, []);

  return (
    <div className="library-page">
      <h1 style={{ marginTop: 0 }}>Run library</h1>
      {error && <div className="error-banner" role="alert">{error}</div>}

      {runs === null && !error && <p style={{ color: "var(--secondary)" }}>Loading runs…</p>}

      {runs && runs.length === 0 && (
        <div className="card library-empty">
          <p>No investigations yet.</p>
          <Link to="/?new=1" className="btn btn-primary" style={{ display: "inline-flex", marginTop: 16 }}>
            Start a new investigation
          </Link>
        </div>
      )}

      {runs && runs.length > 0 && (
        <div className="field">
          <label htmlFor="run-search">Search runs</label>
          <input id="run-search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Run id, label, or status" />
        </div>
      )}

      {runs && runs.length > 0 && (
        <ul className="run-list">
          {runs.filter((run) => `${run.label ?? ""} ${run.id} ${run.status ?? ""}`.toLowerCase().includes(query.toLowerCase())).map((run) => (
            <li key={run.id}>
              <Link to={`/runs/${run.id}`}>
                <div style={{ fontWeight: 500 }}>{run.label ?? run.id}</div>
                <div style={{ color: "var(--secondary)", fontSize: "0.875rem" }}>
                  {run.status ?? "unknown"} · {run.id}
                </div>
              </Link>
              <Link to={`/playback/${run.id}`}>Recorded playback</Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
