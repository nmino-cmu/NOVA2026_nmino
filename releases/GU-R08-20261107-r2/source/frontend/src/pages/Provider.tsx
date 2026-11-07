import { useState } from "react";

export function ProviderPage() {
  const [baseUrl, setBaseUrl] = useState("http://127.0.0.1:8791/v1");
  const [model, setModel] = useState("echo-local");
  const [result, setResult] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function test() {
    setError(null);
    const response = await fetch("/api/provider/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ baseUrl, model }),
    });
    const body = await response.json();
    if (!response.ok || body.ok === false) {
      setError(body.detail || "The endpoint test failed.");
      setResult("");
      return;
    }
    setResult(`Observed ${body.modelObserved}. Models: ${(body.models || []).join(", ") || "not listed"}.`);
  }

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Provider</h1>
      <p style={{ color: "var(--secondary)" }}>
        Loopback endpoints are tested without a key. OpenRouter is the only remote host this release will call.
      </p>
      {error && <div className="error-banner" role="alert">{error}</div>}
      <section className="card">
        <div className="field">
          <label htmlFor="base">Endpoint</label>
          <input id="base" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="model">Model</label>
          <input id="model" value={model} onChange={(e) => setModel(e.target.value)} />
        </div>
        <button type="button" className="btn btn-primary" onClick={() => void test()}>Test endpoint</button>
        {result && <p>{result}</p>}
      </section>
    </div>
  );
}
