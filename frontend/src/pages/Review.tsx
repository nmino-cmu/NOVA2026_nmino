import { useState } from "react";

export function ReviewPage() {
  const [runId, setRunId] = useState("");
  const [recommendation, setRecommendation] = useState<Record<string, unknown> | null>(null);
  const [brief, setBrief] = useState("");
  const [retestId, setRetestId] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function recommend() {
    setError(null);
    const response = await fetch("/api/recommendations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ runId }),
    });
    if (!response.ok) {
      setError(await response.text());
      return;
    }
    setRecommendation(await response.json());
  }

  async function downloadBrief() {
    if (!recommendation) return;
    const response = await fetch("/api/briefs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ runId, recommendationId: recommendation.id }),
    });
    if (!response.ok) {
      setError(await response.text());
      return;
    }
    const body = await response.json();
    setBrief(body.markdown);
  }

  async function retest() {
    setError(null);
    const response = await fetch("/api/retests", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ build: "orbit-fixed-v1", beforeRunId: runId }),
    });
    if (!response.ok) {
      setError(await response.text());
      return;
    }
    const body = await response.json();
    setRetestId(body.id);
  }

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Review</h1>
      <p style={{ color: "var(--secondary)" }}>
        A recommendation describes the behavior change. It does not edit a repository.
      </p>
      {error && <div className="error-banner" role="alert">{error}</div>}
      <section className="card">
        <div className="field">
          <label htmlFor="review-run">Failed run</label>
          <input id="review-run" value={runId} onChange={(e) => setRunId(e.target.value)} placeholder="run_…" />
        </div>
        <div className="wizard-actions">
          <button type="button" className="btn btn-primary" onClick={() => void recommend()}>Record recommendation</button>
          <button type="button" className="btn" disabled={!recommendation} onClick={() => void downloadBrief()}>Export brief</button>
          <button type="button" className="btn" onClick={() => void retest()}>Retest Express on the fixed build</button>
        </div>
        {recommendation && <p>{String(recommendation.proposed ?? "")}</p>}
        {brief && <pre style={{ whiteSpace: "pre-wrap" }}>{brief}</pre>}
        {retestId && <p>Retest queued: {retestId}</p>}
      </section>
    </div>
  );
}
