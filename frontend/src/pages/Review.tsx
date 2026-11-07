import { useState } from "react";

export function ReviewPage() {
  const [runId, setRunId] = useState("");
  const [recommendation, setRecommendation] = useState<Record<string, unknown> | null>(null);
  const [claim, setClaim] = useState("");
  const [proposed, setProposed] = useState("");
  const [acceptance, setAcceptance] = useState("");
  const [brief, setBrief] = useState("");
  const [retestId, setRetestId] = useState("");
  const [relation, setRelation] = useState("");
  const [error, setError] = useState<string | null>(null);

  function remember(body: Record<string, unknown>) {
    setRecommendation(body);
    setClaim(String(body.claim ?? ""));
    setProposed(String(body.proposed ?? ""));
    setAcceptance(Array.isArray(body.acceptance) ? body.acceptance.join("\n") : "");
  }

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
    remember(await response.json());
  }

  async function save(status: "edited" | "rejected" | "accepted") {
    if (!recommendation) return;
    setError(null);
    const response = await fetch(`/api/recommendations/${recommendation.id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status,
        claim,
        proposed,
        acceptance: acceptance.split("\n").map((item) => item.trim()).filter(Boolean),
      }),
    });
    if (!response.ok) {
      setError(await response.text());
      return;
    }
    remember(await response.json());
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
    const file = new Blob([body.markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(file);
    const link = document.createElement("a");
    link.href = url;
    link.download = "ghost-users-brief.md";
    link.click();
    URL.revokeObjectURL(url);
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
    window.setTimeout(async () => {
      const follow = await fetch(`/api/runs/${body.id}`);
      if (!follow.ok) return;
      const run = await follow.json();
      setRelation(String(run.projection?.latestVerification?.detail || run.status));
    }, 1500);
  }

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Review</h1>
      <p style={{ color: "var(--secondary)" }}>
        A recommendation describes the witnessed failure. Exporting a brief does not edit a repository.
      </p>
      {error && <div className="error-banner" role="alert">{error}</div>}
      <section className="card">
        <div className="field">
          <label htmlFor="review-run">Failed run</label>
          <input id="review-run" value={runId} onChange={(e) => setRunId(e.target.value)} placeholder="run_…" />
        </div>
        <div className="wizard-actions">
          <button type="button" className="btn btn-primary" onClick={() => void recommend()}>Record recommendation</button>
        </div>
        {recommendation && (
          <>
            <p>Observation: {String(recommendation.observation ?? "")}</p>
            <p>Impact: {String(recommendation.impact ?? "")}</p>
            <p>Unknowns: {Array.isArray(recommendation.unknowns) && recommendation.unknowns.length ? recommendation.unknowns.join("; ") : "None recorded."}</p>
            <p>Evidence: {Array.isArray(recommendation.evidenceIds) ? recommendation.evidenceIds.join(", ") : "none"}</p>
            <div className="field">
              <label htmlFor="claim">Claim</label>
              <textarea id="claim" value={claim} onChange={(e) => setClaim(e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="proposed">Recommendation</label>
              <textarea id="proposed" value={proposed} onChange={(e) => setProposed(e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="acceptance">Acceptance, one check per line</label>
              <textarea id="acceptance" value={acceptance} onChange={(e) => setAcceptance(e.target.value)} />
            </div>
            <p>Status: {String(recommendation.status ?? "")}</p>
            <div className="wizard-actions">
              <button type="button" className="btn" onClick={() => void save("edited")}>Save edit</button>
              <button type="button" className="btn" onClick={() => void save("rejected")}>Reject</button>
              <button type="button" className="btn" onClick={() => void save("accepted")}>Accept for export</button>
              <button type="button" className="btn" onClick={() => void downloadBrief()}>Download brief</button>
              <button type="button" className="btn" onClick={() => void retest()}>Retest stored actions on orbit-fixed-v1</button>
            </div>
          </>
        )}
        {brief && <pre style={{ whiteSpace: "pre-wrap" }}>{brief}</pre>}
        {retestId && <p>Retest queued: {retestId}. {relation}</p>}
      </section>
    </div>
  );
}
