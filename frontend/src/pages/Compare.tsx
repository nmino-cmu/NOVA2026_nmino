import { useState } from "react";
import { Link } from "react-router-dom";

function LinkLike({ id }: { id: string }) {
  return <Link to={`/runs/${id}`}> Open {id}</Link>;
}

export function ComparePage() {
  const liveDemo = import.meta.env.VITE_LIVE_DEMO === "1";
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch("/api/comparisons", { method: "POST" });
      if (!response.ok) throw new Error(await response.text());
      setResult(await response.json());
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Comparison failed");
    } finally {
      setBusy(false);
    }
  }

  const harbor = (result?.harbor ?? null) as { interactions?: number; status?: string; detail?: string; runId?: string } | null;
  const orbit = (result?.orbit ?? null) as { interactions?: number; status?: string; detail?: string; runId?: string } | null;
  const checks = (result?.checks ?? []) as { name: string; ok: boolean; detail: string }[];

  if (liveDemo) {
    return (
      <div>
        <h1 style={{ marginTop: 0 }}>Comparison</h1>
        <p style={{ color: "var(--secondary)" }}>Start two investigations from links you choose, then open them from the run library.</p>
      </div>
    );
  }

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Comparison</h1>
      <p style={{ color: "var(--secondary)" }}>
        Each storefront is measured in this comparison using the same checkout goal.
      </p>
      {error && <div className="error-banner" role="alert">{error}</div>}
      <section className="card">
        <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void run()}>
          Measure both routes
        </button>
        {harbor && orbit && (
          <div>
            <p>{String(result?.reason ?? "")}</p>
            <p>Comparable: {String(result?.comparable)}</p>
            <ul>
              {checks.map((item) => (
                <li key={item.name}>{item.ok ? "Holds" : "Does not hold"} — {item.name}: {item.detail}</li>
              ))}
            </ul>
            <p>
              Harbor: {harbor.status} · {harbor.interactions ?? "—"} interactions.
              {harbor.runId && <LinkLike id={harbor.runId} />}
            </p>
            <p>
              Orbit: {orbit.status} · {orbit.interactions ?? "—"} interactions.
              {orbit.runId && <LinkLike id={orbit.runId} />}
            </p>
          </div>
        )}
      </section>
    </div>
  );
}
