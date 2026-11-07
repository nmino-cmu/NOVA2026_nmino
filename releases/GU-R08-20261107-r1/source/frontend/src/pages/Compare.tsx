import { useState } from "react";

export function ComparePage() {
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

  const harbor = (result?.harbor ?? null) as { interactions?: number; status?: string; detail?: string } | null;

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Comparison</h1>
      <p style={{ color: "var(--secondary)" }}>
        Orbit Supply’s quick order is 3 interactions. Harbor Goods uses its own catalog route. Both are controlled demos.
      </p>
      {error && <div className="error-banner" role="alert">{error}</div>}
      <section className="card">
        <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void run()}>
          Run Harbor Goods
        </button>
        {harbor && (
          <p>
            Harbor: {harbor.status} · {harbor.interactions ?? "—"} interactions. Orbit shortcut: 3. {String(result?.reason ?? "")}
          </p>
        )}
      </section>
    </div>
  );
}
