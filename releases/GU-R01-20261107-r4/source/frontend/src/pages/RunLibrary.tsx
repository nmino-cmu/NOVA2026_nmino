import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { listRuns, newIdempotencyKey, postFixtureCheck } from "../api/client";
import type { RunListItem } from "../types/api";

export function RunLibrary() {
  const navigate = useNavigate();
  const [runs, setRuns] = useState<RunListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fixtureMsg, setFixtureMsg] = useState<string | null>(null);
  const [fixtureLoading, setFixtureLoading] = useState(false);

  useEffect(() => {
    void listRuns()
      .then(setRuns)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load runs"));
  }, []);

  async function runFixture(kind: "ordinary" | "shortcut" | "express") {
    setFixtureLoading(true);
    setFixtureMsg(null);
    try {
      const created = (await postFixtureCheck({ kind, idempotencyKey: newIdempotencyKey() })) as {
        id: string;
      };
      navigate(`/runs/${created.id}`);
    } catch (e) {
      setFixtureMsg(e instanceof Error ? e.message : "Fixture check failed");
    } finally {
      setFixtureLoading(false);
    }
  }

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Run library</h1>
      {error && <div className="error-banner" role="alert">{error}</div>}

      {runs === null && !error && <p style={{ color: "var(--secondary)" }}>Loading runs…</p>}

      {runs && runs.length === 0 && (
        <div className="card library-empty">
          <p>No investigations yet.</p>
          <Link to="/" className="btn btn-primary" style={{ display: "inline-flex", marginTop: 16 }}>
            Start a new investigation
          </Link>
        </div>
      )}

      {runs && runs.length > 0 && (
        <ul className="run-list">
          {runs.map((run) => (
            <li key={run.id}>
              <Link to={`/runs/${run.id}`}>
                <div style={{ fontWeight: 500 }}>{run.label ?? run.id}</div>
                <div style={{ color: "var(--secondary)", fontSize: "0.875rem" }}>
                  {run.status ?? "unknown"} · {run.id}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}

      <section className="fixture-section card">
        <h2 style={{ marginTop: 0, fontSize: "1rem" }}>Controlled fixture checks</h2>
        <p>
          These are fixture regression checks against the Orbit controller — not routes the investigator
          discovered during a run.
        </p>
        <p style={{ fontStyle: "italic" }}>
          Express is expected to fail the checkout check.
        </p>
        {fixtureMsg && <p role="status">{fixtureMsg}</p>}
        <div className="fixture-buttons">
          <button
            type="button"
            className="btn"
            disabled={fixtureLoading}
            onClick={() => void runFixture("ordinary")}
          >
            Ordinary
          </button>
          <button
            type="button"
            className="btn"
            disabled={fixtureLoading}
            onClick={() => void runFixture("shortcut")}
          >
            Shortcut
          </button>
          <button
            type="button"
            className="btn"
            disabled={fixtureLoading}
            onClick={() => void runFixture("express")}
          >
            Express
          </button>
        </div>
      </section>
    </div>
  );
}
