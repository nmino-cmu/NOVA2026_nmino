import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { InvestigationDashboard } from "../components/InvestigationDashboard";

type Persona = {
  id: string;
  name: string;
  profile: string;
  priorities: string;
  known: boolean;
  canTest: string;
  uncertain: string;
};

type TaskPlan = {
  id: string;
  name: string;
  url: string;
  intent: string;
  check: string;
  heading: string;
  queries: string[];
  paths: string[];
};

type Plan = {
  url: string;
  kind?: string;
  task: string;
  objective: string;
  assumptions?: string[];
  audience?: string;
  purpose?: string;
  scope?: string;
  tasks?: TaskPlan[];
  personas: Persona[];
  startingConditions: string;
  constraints: string[];
  successCriteria: string[];
  visibleOutcome: string;
  queries: string[];
  budget: { requests: number; browserActions: number; wallMs: number };
  dashboard?: { widgets: string[]; unavailable?: string[] };
  outputs?: string[];
  testable: string[];
  uncertain: string[];
  automatedCheck: string;
};

type ActionRow = { seq?: number; summary?: string; reason?: string; outcome?: string };

type CheckRow = { id?: string; name?: string; status?: string; detail?: string };

type Agent = {
  id: string;
  label: string;
  state: string;
  explanation: string;
  currentAction?: string;
  reason?: string;
  elapsedMs?: number;
  browserActions?: number;
  browserBudget?: number;
  requests?: number;
  requestBudget?: number;
  screenshotId?: string | null;
  screenshotLabel?: string;
  screenshotAt?: string | null;
  goalAttempts?: { ok?: boolean; detail?: string; url?: string; priceCeiling?: number | string | null; cartText?: string }[];
  coverage?: { planned?: string[]; visited?: string[]; unvisited?: string[] };
  actions?: ActionRow[];
  checks?: CheckRow[];
};

type Finding = {
  id: string;
  status: string;
  title: string;
  where: string;
  observed: string;
  personas: string;
  goal: string;
  impact: string;
  change: string;
  why: string;
  acceptance: string;
  retest: string;
  severity: string;
  confidence: string;
  priority: string;
  kind: string;
  tradeoff?: string;
  supported?: boolean;
  evidenceNote?: string;
  evidence?: { id: string; label: string }[];
  evidenceIds: string[];
};

type Report = {
  ok: boolean;
  error?: string;
  summary?: string;
  checkAlignment?: string;
  personas?: { name: string; completed: boolean; conditions: string; difficulties: string; findings: string }[];
  findings?: Finding[];
  comparison?: Record<string, string>;
  recorded?: { name: string; runId: string; status: string; stopReason?: string; goal?: string; actionCount?: number; blockedCount?: number; elapsedMs?: number }[];
  screenshotCount?: number;
  note?: string;
};

type Conversation = {
  id: string;
  messages: { id: string; role: string; text: string; kind?: string }[];
  plan: Plan | null;
  planSource?: string | null;
  planModel?: string | null;
  report: Report | null;
  reportStatus?: string | null;
  agents?: Agent[];
  previous?: { report?: Report | null } | null;
  profiles?: Persona[];
  site?: { ok?: boolean; title?: string; headings?: string[]; links?: { name: string; href: string }[]; detail?: string } | null;
};

const STATIC_DEMO = import.meta.env.VITE_STATIC_DEMO === "1";

const FOLLOWUPS = [
  "Which improvement should I make first?",
  "What did the checks actually record?",
  "Change the dashboard to show coverage and the journey.",
  "Add a task for a page this investigation did not open.",
];

const QUICK_GOALS = [
  {
    label: "UI scan",
    text: "Scan the site and give general UI feedback: layout, visual hierarchy, clarity, and friction on the first screens each persona opens.",
  },
  {
    label: "First visit",
    text: "Walk the site as a first-time visitor. Note what is clear, what is confusing, and what is missing on the paths you actually open.",
  },
  {
    label: "Mobile feel",
    text: "Review navigation and readability as if on a phone. Note cramped controls, buried links, and steps that feel unnecessarily long.",
  },
];

function normalizeUrl(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) return "";
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  return `https://${trimmed}`;
}

async function readError(response: Response) {
  const body = await response.json().catch(() => ({}));
  return typeof body.detail === "string" ? body.detail : response.statusText || "The request failed.";
}

export function ConversationPage() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const fresh = params.get("new") === "1";
  const navigate = useNavigate();
  const [url, setUrl] = useState("");
  const [text, setText] = useState("");
  const [doc, setDoc] = useState<Conversation | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [follow, setFollow] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [profileToAdd, setProfileToAdd] = useState("executive");
  const dirty = useRef(false);
  const planRef = useRef<Plan | null>(null);
  planRef.current = plan;

  useEffect(() => {
    if (id || fresh) return;
    const saved = localStorage.getItem("ghost-conversation");
    if (saved) navigate(`/c/${saved}`, { replace: true });
  }, [id, fresh, navigate]);

  useEffect(() => {
    if (!fresh || id) return;
    localStorage.removeItem("ghost-conversation");
    dirty.current = false;
    setDoc(null);
    setPlan(null);
    setUrl("");
    setText("");
    setError("");
    setSelected(null);
  }, [fresh, id]);

  useEffect(() => {
    if (!id || STATIC_DEMO) return;
    localStorage.setItem("ghost-conversation", id);
  }, [id]);

  async function pull(conversationId: string) {
    const response = await fetch(`/api/conversations/${conversationId}`);
    if (response.status === 404) {
      localStorage.removeItem("ghost-conversation");
      setDoc(null);
      setPlan(null);
      navigate("/?new=1", { replace: true });
      return;
    }
    if (!response.ok) {
      setError(await readError(response));
      return;
    }
    const next = (await response.json()) as Conversation;
    setDoc(next);
    if (!dirty.current) {
      setPlan(next.plan);
      if (next.plan?.url) setUrl(next.plan.url);
    }
    setSelected((current) => {
      if (current && next.agents?.some((agent) => agent.id === current)) return current;
      return next.agents?.[0]?.id ?? current;
    });
  }

  useEffect(() => {
    if (!id) return;
    void pull(id);
    // The conversation id is the only input. pull reads the latest dirty flag.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    if (!id || !plan || !dirty.current) return;
    const sent = plan;
    const handle = window.setTimeout(async () => {
      const response = await fetch(`/api/conversations/${id}/plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan: sent }),
      });
      if (!response.ok || planRef.current !== sent) return;
      const next = (await response.json()) as Conversation;
      dirty.current = false;
      setDoc(next);
      setPlan(next.plan);
    }, 700);
    return () => window.clearTimeout(handle);
  }, [id, plan]);

  const live = (doc?.agents || []).some((agent) => ["queued", "running", "verifying"].includes(agent.state));
  const waitingReport = Boolean(doc?.agents?.length) && !doc?.report && doc?.reportStatus !== "failed";

  useEffect(() => {
    if (!id || (!live && !waitingReport)) return;
    const handle = window.setInterval(() => void pull(id), 2000);
    return () => window.clearInterval(handle);
    // pull is recreated each render; the interval only needs the conversation id and live flags.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, live, waitingReport]);

  function editPlan(next: Plan) {
    dirty.current = true;
    setPlan(next);
  }

  async function send() {
    const target = normalizeUrl(url);
    if (!target) {
      setError("Enter a website URL.");
      return;
    }
    if (!text.trim()) {
      setError("Describe what you want the agents to investigate.");
      return;
    }
    setBusy(true);
    setError("");
    const response = await fetch("/api/conversations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: target, text: text.trim(), conversationId: id }),
    });
    setBusy(false);
    if (!response.ok) {
      setError(await readError(response));
      return;
    }
    const next = (await response.json()) as Conversation;
    dirty.current = false;
    setDoc(next);
    setPlan(next.plan);
    setUrl(target);
    setText("");
    if (next.id !== id) navigate(`/c/${next.id}`);
  }

  async function launch() {
    if (!id || !plan) return;
    setBusy(true);
    setError("");
    const response = await fetch(`/api/conversations/${id}/launch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan }),
    });
    setBusy(false);
    if (!response.ok) {
      setError(await readError(response));
      return;
    }
    const next = (await response.json()) as Conversation;
    dirty.current = false;
    setDoc(next);
    setPlan(next.plan);
    setSelected(next.agents?.[0]?.id ?? null);
  }

  async function ask(question: string) {
    if (!id || !question.trim()) return;
    setBusy(true);
    setError("");
    const response = await fetch(`/api/conversations/${id}/followup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: question }),
    });
    setBusy(false);
    if (!response.ok) {
      setError(await readError(response));
      return;
    }
    setFollow("");
    setDoc((await response.json()) as Conversation);
  }

  async function stopAgent(agentId: string) {
    await fetch(`/api/runs/${agentId}/stop`, { method: "POST" });
    if (id) await pull(id);
  }

  async function saveFinding(finding: Finding, patch: Partial<Finding> & { status?: string }) {
    if (!id) return;
    const response = await fetch(`/api/conversations/${id}/findings/${finding.id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!response.ok) {
      setError(await readError(response));
      return;
    }
    setDoc((await response.json()) as Conversation);
  }

  async function downloadBrief() {
    if (!id) return;
    const response = await fetch(`/api/conversations/${id}/brief`);
    const blob = new Blob([await response.text()], { type: "text/markdown" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "ghost-users-brief.md";
    link.click();
    URL.revokeObjectURL(link.href);
  }

  function startFresh() {
    localStorage.removeItem("ghost-conversation");
    dirty.current = false;
    setDoc(null);
    setPlan(null);
    setText("");
    setError("");
    navigate("/?new=1");
  }

  const agent = doc?.agents?.find((item) => item.id === selected) || doc?.agents?.[0];
  const running = live;
  const hasLaunch = Boolean(doc?.agents?.length);
  const showCompactInvestigate = STATIC_DEMO && hasLaunch;
  const dashboard = (
    <InvestigationDashboard
      plan={plan}
      agents={doc?.agents || []}
      agent={agent}
      site={doc?.site}
      report={doc?.report || null}
      reportStatus={doc?.reportStatus}
      onSelect={setSelected}
      onStop={(agentId) => void stopAgent(agentId)}
      onExport={() => void downloadBrief()}
      onSaveFinding={(finding, patch) => void saveFinding(finding, patch)}
      onEditFinding={(findingId, patch) => {
        setDoc((current) => current && current.report ? {
          ...current,
          report: {
            ...current.report,
            findings: current.report.findings?.map((item) => item.id === findingId ? { ...item, ...patch } : item),
          },
        } : current);
      }}
    />
  );

  return (
    <div className={`investigation-workspace${showCompactInvestigate ? " recorded-demo" : ""}`}>
    {showCompactInvestigate ? dashboard : null}
    <div className="conversation">
      <header className="conversation-intro">
        <div>
          <h1>What should these agents investigate?</h1>
          <p>
            Paste any public URL and describe what you want to learn. Ghost Users launches one browser per agent profile,
            records screenshots and routes, and keeps the evidence on the dashboard.
          </p>
        </div>
        <button className="btn" type="button" onClick={startFresh}>New investigation</button>
      </header>

      {showCompactInvestigate && plan ? (
        <section className="plan-summary" aria-label="Investigation summary">
          <p className="kicker">Investigation</p>
          <h2>{plan.url.replace(/^https?:\/\//, "")}</h2>
          <p>{plan.objective || plan.task}</p>
          <p className="check-note">
            {doc?.agents?.length ?? 0} agent{(doc?.agents?.length ?? 0) === 1 ? "" : "s"} in separate browsers.
            Select an agent on the dashboard to inspect screenshots, the journey, and the recorded checks.
          </p>
        </section>
      ) : null}

      {!showCompactInvestigate ? (
      <form
        className="composer"
        onSubmit={(event) => {
          event.preventDefault();
          void send();
        }}
      >
        <label className="field">
          <span>Website URL</span>
          <input
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            placeholder="example.com"
            inputMode="url"
            autoComplete="url"
          />
        </label>
        <label className="field">
          <span>Goal</span>
          <textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            rows={4}
            placeholder="Scan the site and give general UI feedback."
          />
        </label>
        <div className="quick-goals" role="group" aria-label="Example goals">
          {QUICK_GOALS.map((item) => (
            <button
              key={item.label}
              type="button"
              className="btn quick-goal"
              disabled={busy}
              onClick={() => setText(item.text)}
            >
              {item.label}
            </button>
          ))}
        </div>
        <button className="btn btn-primary" type="submit" disabled={busy || !url.trim() || !text.trim()}>
          {plan ? "Update plan" : "Build plan"}
        </button>
      </form>
      ) : null}

      {doc?.site && !showCompactInvestigate ? (
        <section className="site-preview" aria-label="Page inspection">
          <p className="kicker">Inspected page</p>
          <p>
            <strong>{doc.site.title || plan?.url || url}</strong>
            {doc.site.ok
              ? ` · ${(doc.site.headings || []).slice(0, 3).join(" · ") || "No headings listed"}`
              : ` · ${doc.site.detail || "Could not inspect this URL."}`}
          </p>
        </section>
      ) : null}

      {error ? <p className="conversation-error" role="alert">{error}</p> : null}

      {!showCompactInvestigate ? (
      <ol className="thread">
        {(doc?.messages || []).map((message) => (
          <li key={message.id} className={message.role === "user" ? "from-user" : "from-agent"}>
            <b>{message.role === "user" ? "You" : "Ghost Users"}</b>
            <p>{message.text}</p>
          </li>
        ))}
      </ol>
      ) : null}

      {plan && !showCompactInvestigate ? (
        <section className="plan-editor" aria-label="Investigation plan">
          <header>
            <h2>Ready to launch</h2>
            <p className="check-note">
              {doc?.planSource === "draft"
                ? "Filled-in draft — review personas and goal before launch."
                : `${plan.personas.length} agent${plan.personas.length === 1 ? "" : "s"} will browse ${plan.url.replace(/^https?:\/\//, "")} in separate browsers.`}
            </p>
          </header>
          <label className="field">
            <span>Goal</span>
            <textarea value={plan.objective || plan.task} rows={3} onChange={(event) => editPlan({ ...plan, objective: event.target.value, task: event.target.value })} />
          </label>
          <h3>Agent profiles</h3>
          <p className="check-note">Each profile is an agent with its own browser, screenshots, and journey. They browse the URL you supplied—not a preset site.</p>
          <div className="persona-editor">
            {plan.personas.map((persona) => (
              <article key={persona.id} className="persona-card">
                <header>
                  <input
                    aria-label={`${persona.name} name`}
                    value={persona.name}
                    onChange={(event) => editPlan({
                      ...plan,
                      personas: plan.personas.map((item) => item.id === persona.id ? { ...item, name: event.target.value } : item),
                    })}
                  />
                  <button className="btn" type="button" onClick={() => editPlan({ ...plan, personas: plan.personas.filter((item) => item.id !== persona.id) })}>
                    Remove
                  </button>
                </header>
                <label className="field">
                  <span>How they browse</span>
                  <textarea
                    rows={5}
                    value={persona.profile}
                    onChange={(event) => editPlan({
                      ...plan,
                      personas: plan.personas.map((item) => item.id === persona.id ? { ...item, profile: event.target.value } : item),
                    })}
                  />
                </label>
                <label className="field">
                  <span>What they prioritize</span>
                  <textarea
                    rows={2}
                    value={persona.priorities}
                    onChange={(event) => editPlan({
                      ...plan,
                      personas: plan.personas.map((item) => item.id === persona.id ? { ...item, priorities: event.target.value } : item),
                    })}
                  />
                </label>
              </article>
            ))}
          </div>
          <div className="add-persona">
            <label>
              <span>Add profile</span>
              <select value={profileToAdd} onChange={(event) => setProfileToAdd(event.target.value)}>
                {(doc?.profiles || []).map((profile) => (
                  <option key={profile.id} value={profile.id}>{profile.name}</option>
                ))}
                <option value="custom">Custom persona</option>
              </select>
            </label>
            <button
              className="btn"
              type="button"
              onClick={() => {
                const source = (doc?.profiles || []).find((item) => item.id === profileToAdd);
                const persona: Persona = source
                  ? { ...source, known: true }
                  : {
                      id: `custom${plan.personas.length + 1}`,
                      name: "Custom persona",
                      profile: "",
                      priorities: "",
                      known: false,
                      canTest: "Which visible controls this profile chooses, and whether the shared acceptance check passes.",
                      uncertain: "Whether a real person matching this description would behave the same way.",
                    };
                if (plan.personas.some((item) => item.id === persona.id)) return;
                editPlan({ ...plan, personas: [...plan.personas, persona] });
              }}
            >
              Add persona
            </button>
          </div>
          <div className="launch-row">
            <button className="btn btn-primary" type="button" disabled={busy || running || plan.personas.length === 0} onClick={() => void launch()}>
              {doc?.report ? "Run again" : `Launch ${plan.personas.length} agent${plan.personas.length === 1 ? "" : "s"}`}
            </button>
            <span className="check-note">
              Up to {plan.budget.browserActions} page actions · {plan.budget.requests} model calls each
            </span>
          </div>
          <details className="plan-advanced">
            <summary>Advanced plan settings</summary>
            <label className="field">
              <span>URL</span>
              <input value={plan.url} onChange={(event) => editPlan({ ...plan, url: event.target.value })} />
            </label>
            <label className="field">
              <span>Constraints, one per line</span>
              <textarea value={plan.constraints.join("\n")} rows={3} onChange={(event) => editPlan({ ...plan, constraints: event.target.value.split("\n") })} />
            </label>
            <div className="budget-row">
              <label className="field">
                <span>Model requests</span>
                <input type="number" min={1} max={20} value={plan.budget.requests} onChange={(event) => editPlan({ ...plan, budget: { ...plan.budget, requests: Number(event.target.value) } })} />
              </label>
              <label className="field">
                <span>Browser actions</span>
                <input type="number" min={1} max={180} value={plan.budget.browserActions} onChange={(event) => editPlan({ ...plan, budget: { ...plan.budget, browserActions: Number(event.target.value) } })} />
              </label>
            </div>
            <p className="check-note">{plan.automatedCheck}</p>
            {(plan.tasks || []).map((task) => (
              <p key={task.id} className="check-note">
                {task.name}: {(task.paths || []).join(", ") || task.url}
              </p>
            ))}
          </details>
        </section>
      ) : null}

      {doc && !showCompactInvestigate ? (
        <form
          className="followup"
          onSubmit={(event) => {
            event.preventDefault();
            void ask(follow);
          }}
        >
          <h2>Ask about this investigation</h2>
          <label className="field">
            <span>Follow-up</span>
            <textarea value={follow} rows={3} onChange={(event) => setFollow(event.target.value)} />
          </label>
          <button className="btn btn-primary" type="submit" disabled={busy || !follow.trim()}>Ask</button>
          <div className="followup-prompts">
            {FOLLOWUPS.map((question) => (
              <button key={question} className="btn" type="button" disabled={busy} onClick={() => void ask(question)}>{question}</button>
            ))}
          </div>
        </form>
      ) : null}
    </div>
    {!showCompactInvestigate ? dashboard : null}
    </div>
  );
}
