import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  createRun,
  createTask,
  createTaskDraft,
  newIdempotencyKey,
} from "../api/client";
import type { Budget, CheckEntry, TaskDraftResponse } from "../types/api";

const STEP_TITLES = [
  "Target",
  "Goal and starting conditions",
  "Allowed actions and budget",
  "Review and launch",
] as const;

const DEFAULT_BUDGET: Budget = {
  wallMs: 180000,
  requests: 12,
  totalTokens: 60000,
  browserActions: 180,
  resets: 12,
  routeActions: 12,
  spendingUSD: null,
};

export function SetupWizard() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [targetKind, setTargetKind] = useState<"supplied" | null>(null);
  const [policyId, setPolicyId] = useState("adaptive-v1");
  const [url, setUrl] = useState("");
  const [targetName, setTargetName] = useState("");
  const [restoration, setRestoration] = useState<"fresh_context" | "unknown">("fresh_context");

  const [draft, setDraft] = useState<TaskDraftResponse | null>(null);
  const [checks, setChecks] = useState<CheckEntry[]>([]);
  const [objective, setObjective] = useState("");
  const [task, setTask] = useState("");
  const [acceptableInteractions, setAcceptableInteractions] = useState(12);
  const [budget, setBudget] = useState<Budget>(DEFAULT_BUDGET);
  const [persona, setPersona] = useState("");
  const [queries, setQueries] = useState("");

  function applyDraft(res: TaskDraftResponse) {
    setDraft(res);
    const scopeChecks = (res.checks as CheckEntry[] | undefined) ?? [];
    setChecks(scopeChecks);
    setObjective(String(res.objective ?? ""));
    setTask(String(res.task ?? ""));
    setUrl(String(res.url ?? ""));
    if (typeof res.acceptableInteractions === "number") {
      setAcceptableInteractions(res.acceptableInteractions);
    }
    const b = res.budget as Partial<Budget> | undefined;
    if (b) {
      setBudget({ ...DEFAULT_BUDGET, ...b, spendingUSD: b.spendingUSD ?? null });
    }
  }

  async function submitSuppliedTarget() {
    if (!url.trim() || !objective.trim() || !targetName.trim()) {
      setError("URL, objective, and target name are required.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await createTaskDraft({
        mode: "supplied",
        url: url.trim(),
        objective: objective.trim(),
        targetName: targetName.trim(),
        restoration,
      });
      applyDraft(res);
      setTargetKind("supplied");
      setStep(1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Draft failed");
    } finally {
      setLoading(false);
    }
  }

  async function launch() {
    if (!draft && targetKind === null) return;
    setLoading(true);
    setError(null);
    try {
      const payload: TaskDraftResponse = {
        ...(draft ?? {}),
        objective,
        task,
        acceptableInteractions,
        budget,
        url: targetKind === "supplied" ? url : draft?.url,
        persona: persona || undefined,
        queries: queries.split("\n").map((item) => item.trim()).filter(Boolean).slice(0, 3),
      };
      const created = await createTask(payload);
      const run = await createRun({
        taskId: created.id,
        taskVersion: created.version,
        policyId: targetKind === "supplied" ? "ordinary-model-v1" : policyId,
        idempotencyKey: newIdempotencyKey(),
      });
      navigate(`/runs/${run.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Launch failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="setup-page">
      <header className="hero">
        <div>
          <div className="eyebrow">Browser investigations you can inspect and replay</div>
          <h1>See your product through <span>new eyes.</span></h1>
          <p>Enter the page you want investigated. The map records only states the run actually witnessed.</p>
        </div>
      </header>
      <div className="setup-layout">
      <div>
      <h1 style={{ marginTop: 0 }}>New investigation</h1>
      <div className="wizard-steps" role="tablist" aria-label="Setup steps">
        {STEP_TITLES.map((title, i) => (
          <span
            key={title}
            className={`wizard-step ${i === step ? "active" : ""}`}
            role="tab"
            aria-selected={i === step}
          >
            {title}
          </span>
        ))}
      </div>

      {error && <div className="error-banner" role="alert">{error}</div>}

      {step === 0 && (
        <section className="card">
          <h2 style={{ marginTop: 0, fontSize: "1.125rem" }}>{STEP_TITLES[0]}</h2>
          <p style={{ color: "var(--secondary)" }}>Supply the application URL to investigate.</p>
          <div className="field">
            <label htmlFor="url">URL</label>
            <input id="url" value={url} onChange={(e) => setUrl(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="suppliedObjective">Objective</label>
            <textarea
              id="suppliedObjective"
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="targetName">Target name</label>
            <input id="targetName" value={targetName} onChange={(e) => setTargetName(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="restoration">Restoration</label>
            <select
              id="restoration"
              value={restoration}
              onChange={(e) => setRestoration(e.target.value as "fresh_context" | "unknown")}
            >
              <option value="fresh_context">fresh_context</option>
              <option value="unknown">unknown</option>
            </select>
          </div>
          <button type="button" className="btn" disabled={loading} onClick={() => void submitSuppliedTarget()}>
            Continue with supplied URL
          </button>
        </section>
      )}

      {step === 1 && (
        <section className="card">
          <h2 style={{ marginTop: 0, fontSize: "1.125rem" }}>{STEP_TITLES[1]}</h2>
          {checks.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <h3 style={{ fontSize: "0.875rem", color: "var(--secondary)" }}>Accepted scope (checks)</h3>
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {checks.map((c) => (
                  <li key={c.id}>{c.name}</li>
                ))}
              </ul>
            </div>
          )}
          <div className="field">
            <label htmlFor="objective">Objective</label>
            <textarea id="objective" value={objective} onChange={(e) => setObjective(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="task">Task description</label>
            <textarea id="task" value={task} onChange={(e) => setTask(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="persona">Persona</label>
            <select id="persona" value={persona} onChange={(e) => setPersona(e.target.value)}>
              <option value="">None</option>
              <option value="price">Price</option>
              <option value="browse">Browse</option>
              <option value="search">Search</option>
              <option value="careful">Careful</option>
              <option value="hurried">Hurried</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="queries">Search queries, one per line, up to three</label>
            <textarea id="queries" value={queries} onChange={(e) => setQueries(e.target.value)} />
          </div>
          <div className="wizard-actions">
            <button type="button" className="btn" onClick={() => setStep(0)}>
              Back
            </button>
            <button type="button" className="btn btn-primary" onClick={() => setStep(2)}>
              Continue
            </button>
          </div>
        </section>
      )}

      {step === 2 && (
        <section className="card">
          <h2 style={{ marginTop: 0, fontSize: "1.125rem" }}>{STEP_TITLES[2]}</h2>
          <div className="field">
            <label htmlFor="acceptableInteractions">Acceptable interactions</label>
            <input
              id="acceptableInteractions"
              type="number"
              className="tabular"
              value={acceptableInteractions}
              onChange={(e) => setAcceptableInteractions(Number(e.target.value))}
            />
          </div>
          <div className="field">
            <label htmlFor="wallMs">Wall time (ms)</label>
            <input
              id="wallMs"
              type="number"
              className="tabular"
              value={budget.wallMs}
              onChange={(e) => setBudget({ ...budget, wallMs: Number(e.target.value) })}
            />
          </div>
          <div className="field">
            <label htmlFor="requests">Model requests</label>
            <input
              id="requests"
              type="number"
              className="tabular"
              value={budget.requests}
              onChange={(e) => setBudget({ ...budget, requests: Number(e.target.value) })}
            />
          </div>
          <div className="field">
            <label htmlFor="routeActions">Route actions</label>
            <input
              id="routeActions"
              type="number"
              className="tabular"
              value={budget.routeActions}
              onChange={(e) => setBudget({ ...budget, routeActions: Number(e.target.value) })}
            />
          </div>
          <div className="wizard-actions">
            <button type="button" className="btn" onClick={() => setStep(1)}>
              Back
            </button>
            <button type="button" className="btn btn-primary" onClick={() => setStep(3)}>
              Continue
            </button>
          </div>
        </section>
      )}

      {step === 3 && (
        <section className="card">
          <h2 style={{ marginTop: 0, fontSize: "1.125rem" }}>{STEP_TITLES[3]}</h2>
          <p style={{ color: "var(--secondary)" }}>
            Target: {url || "Supplied URL"}
          </p>
          <dl style={{ margin: 0 }}>
            <dt style={{ color: "var(--secondary)" }}>Objective</dt>
            <dd>{objective || "—"}</dd>
            <dt style={{ color: "var(--secondary)" }}>Acceptable interactions</dt>
            <dd className="tabular">{acceptableInteractions}</dd>
          </dl>
          {targetKind !== "supplied" && (
            <div className="field" style={{ marginTop: 16 }}>
              <label htmlFor="policy">Search</label>
              <select id="policy" value={policyId} onChange={(e) => setPolicyId(e.target.value)}>
                <option value="adaptive-v1">Look for a shorter verified route</option>
                <option value="ordinary-model-v1">One model-guided pass</option>
              </select>
            </div>
          )}
          <div className="wizard-actions">
            <button type="button" className="btn" onClick={() => setStep(2)}>
              Back
            </button>
            <button type="button" className="btn btn-primary" disabled={loading} onClick={() => void launch()}>
              Launch investigation
            </button>
          </div>
        </section>
      )}
      </div>
      <aside className="card setup-aside">
        <h2 style={{ marginTop: 0, fontSize: 18 }}>What this run checks</h2>
        <p style={{ color: "var(--secondary)" }}>{objective || "Choose a target to see the task."}</p>
        <ol>
          {checks.length > 0 ? checks.map((item) => <li key={item.id}>{item.name}</li>) : (
            <li>Checks appear after you describe the target and continue.</li>
          )}
        </ol>
        <p className="tabular" style={{ color: "var(--secondary)" }}>Route budget {budget.routeActions} · {budget.requests} model requests</p>
      </aside>
    </div>
    </div>
  );
}
