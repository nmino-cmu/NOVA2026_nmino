import { useEffect, useState } from "react";

interface Selection {
  kind: string;
  baseUrl: string;
  model: string;
  label?: string;
  honest?: string;
  fixture?: string;
}

export function ProviderPage() {
  const [kind, setKind] = useState("openrouter");
  const [baseUrl, setBaseUrl] = useState("https://openrouter.ai/api/v1");
  const [model, setModel] = useState("anthropic/claude-sonnet-4.6");
  const [saved, setSaved] = useState<Selection | null>(null);
  const [result, setResult] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetch("/api/provider")
      .then((response) => response.json())
      .then((body: Selection) => {
        setSaved(body);
        setKind(body.fixture === "echo-local" ? "echo-fixture" : body.kind);
        setBaseUrl(body.baseUrl);
        setModel(body.model);
      })
      .catch(() => setError("Could not load the saved provider."));
  }, []);

  function applyKind(next: string) {
    setKind(next);
    if (next === "openrouter") {
      setBaseUrl("https://openrouter.ai/api/v1");
      if (model === "echo-local") setModel("anthropic/claude-sonnet-4.6");
    }
    if (next === "echo-fixture") {
      setBaseUrl("http://127.0.0.1:8791/v1");
      setModel("echo-local");
    }
    if (next === "compatible" && model === "echo-local") {
      setBaseUrl("http://127.0.0.1:8791/v1");
      setModel("");
    }
  }

  async function save() {
    setError(null);
    const response = await fetch("/api/provider", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind, baseUrl, model }),
    });
    const body = await response.json();
    if (!response.ok) {
      setError(body.detail || "Could not save the provider.");
      return;
    }
    setSaved(body);
    setResult(`Saved ${body.label}. Investigations use this selection.`);
  }

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
    const honest = body.honest ? ` ${body.honest}` : "";
    setResult(`Observed ${body.modelObserved || body.label || model}. Models: ${(body.models || []).join(", ") || "not listed"}.${honest}`);
  }

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Provider</h1>
      <p style={{ color: "var(--secondary)" }}>
        OpenRouter uses the server-side key. A loopback endpoint is called without that key. The echo fixture is a deterministic stand-in, not a general model.
      </p>
      {error && <div className="error-banner" role="alert">{error}</div>}
      <section className="card">
        <div className="field">
          <label htmlFor="kind">Selection</label>
          <select id="kind" value={kind} onChange={(e) => applyKind(e.target.value)}>
            <option value="openrouter">OpenRouter</option>
            <option value="compatible">Loopback endpoint</option>
            <option value="echo-fixture">Deterministic echo fixture</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="base">Endpoint</label>
          <input id="base" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="model">Model</label>
          <input id="model" value={model} onChange={(e) => setModel(e.target.value)} />
        </div>
        <div className="wizard-actions">
          <button type="button" className="btn" onClick={() => void test()}>Test endpoint</button>
          <button type="button" className="btn btn-primary" onClick={() => void save()}>Save and use</button>
        </div>
        {kind === "echo-fixture" && <p>Deterministic echo fixture. It picks an id from the candidate list it is shown. It is not a general model.</p>}
        {saved && <p>Current selection: {saved.label} · {saved.model}</p>}
        {saved?.honest && <p style={{ color: "var(--secondary)" }}>{saved.honest}</p>}
        {result && <p>{result}</p>}
      </section>
    </div>
  );
}
