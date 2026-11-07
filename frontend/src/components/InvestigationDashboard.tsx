import { useEffect, useState } from "react";
import { evidenceUrl } from "../api/client";
import { InvestigationGraph } from "./InvestigationGraph";
import type { GraphEdge, GraphNode } from "../types/api";

type Attempt = { ok?: boolean; detail?: string; url?: string; cartText?: string; priceCeiling?: number | string | null };
type Coverage = { planned?: string[]; visited?: string[]; unvisited?: string[] };
type ActionRow = { seq?: number; summary?: string; reason?: string; outcome?: string; url?: string };
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
  actions?: ActionRow[];
  checks?: CheckRow[];
  goalAttempts?: Attempt[];
  coverage?: Coverage;
};
type Evidence = { id: string; label: string };
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
  tradeoff?: string;
  acceptance: string;
  retest: string;
  severity: string;
  confidence: string;
  priority: string;
  kind: string;
  supported?: boolean;
  evidenceNote?: string;
  evidence?: Evidence[];
  evidenceIds: string[];
};
type Report = {
  ok: boolean;
  error?: string;
  summary?: string;
  checkAlignment?: string;
  findings?: Finding[];
  comparison?: Record<string, string>;
  recorded?: { name: string; runId: string; status: string; stopReason?: string; goal?: string; actionCount?: number; blockedCount?: number; backtracks?: number; requests?: number; elapsedMs?: number }[];
  screenshotCount?: number;
  note?: string;
  personas?: { name: string; completed: boolean; conditions: string; difficulties: string; findings: string }[];
};
type Plan = {
  kind?: string;
  dashboard?: { widgets?: string[]; unavailable?: string[] };
  tasks?: { id: string; name: string; check: string }[];
  outputs?: string[];
};
type Site = { ok?: boolean; title?: string; headings?: string[]; links?: { name: string; href: string }[]; detail?: string };

const COMPARISON: [string, string][] = [
  ["completed", "Who finished"],
  ["pathDifferences", "Where paths differed"],
  ["commonFriction", "Common friction"],
  ["personaSpecific", "Persona-specific difficulties"],
  ["counts", "Counts"],
  ["evidence", "Evidence for the comparison"],
  ["priorities", "Highest-priority changes"],
  ["tradeoffs", "Tradeoffs"],
  ["gaps", "Coverage gaps"],
];

function stateLabel(state: string) {
  return state === "queued" ? "waiting" : state;
}

function clock(ms?: number) {
  const total = Math.max(0, Math.round((ms || 0) / 1000));
  return `${Math.floor(total / 60)}:${(total % 60).toString().padStart(2, "0")}`;
}

function taskOf(label: string) {
  const parts = label.split(" · ");
  return parts.length > 1 ? parts.slice(1).join(" · ") : "";
}

export function InvestigationDashboard({
  plan,
  agents,
  agent,
  site,
  report,
  reportStatus,
  onSelect,
  onStop,
  onSaveFinding,
  onEditFinding,
  onExport,
}: {
  plan: Plan | null;
  agents: Agent[];
  agent?: Agent;
  site?: Site | null;
  report: Report | null;
  reportStatus?: string | null;
  onSelect: (id: string) => void;
  onStop: (id: string) => void;
  onSaveFinding: (finding: Finding, patch: Partial<Finding> & { status?: string }) => void;
  onEditFinding: (id: string, patch: Partial<Finding>) => void;
  onExport: () => void;
}) {
  const kind = plan?.kind || "workflow";
  const defaultWidgets =
    kind === "focused"
      ? ["journey", "roster", "screenshots", "search", "recommendations", "evidence"]
      : kind === "review"
        ? ["journey", "roster", "screenshots", "coverage", "recommendations", "evidence"]
        : ["journey", "roster", "screenshots", "milestones", "funnel", "personas", "recommendations", "evidence"];
  const widgetList = plan?.dashboard?.widgets?.length ? plan.dashboard.widgets : agents.length ? defaultWidgets : ["roster", "screenshots"];
  const widgets = new Set(widgetList);
  const widgetKey = widgetList.join(",");
  const [task, setTask] = useState("");
  const [graph, setGraph] = useState<{ nodes: GraphNode[]; edges: GraphEdge[] }>({ nodes: [], edges: [] });
  const tasks = [...new Set(agents.map((item) => taskOf(item.label)).filter(Boolean))];
  const visible = agents.filter((item) => !task || taskOf(item.label) === task);
  const shown = visible.find((item) => item.id === agent?.id) || visible[0];

  useEffect(() => {
    if (!shown?.id || !widgetKey.split(",").includes("journey")) return;
    let stop = false;
    const load = () => {
      void fetch(`/api/runs/${shown.id}`)
        .then((response) => (response.ok ? response.json() : null))
        .then((body) => {
          if (stop || !body) return;
          setGraph({ nodes: body.projection?.nodes || [], edges: body.projection?.edges || [] });
        })
        .catch(() => undefined);
    };
    load();
    const handle = window.setInterval(load, 2000);
    return () => {
      stop = true;
      window.clearInterval(handle);
    };
  }, [shown?.id, widgetKey]);

  if (!plan) return null;
  const live = shown?.state === "running" || shown?.state === "verifying" || shown?.state === "queued";

  return (
    <aside className="dashboard-column" aria-label="Investigation dashboard">
      <header className="dashboard-intro">
        <p className="kicker">{plan.kind === "review" ? "UI review" : plan.kind || "investigation"}</p>
        <h2>Live dashboard</h2>
        <p className="check-note">Screenshots, journeys, and recommendations update as each agent runs.</p>
        {site?.ok ? (
          <p className="check-note">
            Starting page: {site.title || "Untitled"}
            {(site.headings || []).length ? ` · ${(site.headings || []).slice(0, 3).join(" · ")}` : ""}
          </p>
        ) : null}
      </header>

      {widgets.has("roster") ? (
        <section className="dashboard-card" aria-label="Agent roster">
          <h3>Agents</h3>
          {tasks.length > 1 ? (
            <label className="field">
              <span>Task</span>
              <select value={task} onChange={(event) => setTask(event.target.value)}>
                <option value="">All tasks</option>
                {tasks.map((item) => <option key={item} value={item}>{item}</option>)}
              </select>
            </label>
          ) : null}
          <ul className="roster">
            {visible.map((item) => (
              <li key={item.id}>
                <button type="button" className={item.id === shown?.id ? "selected" : ""} aria-pressed={item.id === shown?.id} onClick={() => onSelect(item.id)}>
                  <strong>{item.label}</strong>
                  <em className={`state state-${item.state}`} title={`Runner status: ${item.state}`}>{stateLabel(item.state)}</em>
                  <span>{item.currentAction || item.explanation}</span>
                  <span>{clock(item.elapsedMs)} · {item.browserActions || 0}/{item.browserBudget || "—"} page actions</span>
                </button>
              </li>
            ))}
          </ul>
          {!visible.length ? <p>No investigation has been launched for this dashboard.</p> : null}
        </section>
      ) : null}

      {widgets.has("journey") ? (
        <InvestigationGraph nodes={graph.nodes} edges={graph.edges} live={live} />
      ) : null}

      {widgets.has("screenshots") ? (
        <section className="dashboard-card">
          <h3>Browser</h3>
          {shown?.screenshotId ? (
            <figure>
              <a href={evidenceUrl(shown.screenshotId)}>
                <img src={evidenceUrl(shown.screenshotId)} alt={shown.screenshotLabel || "Latest capture"} />
              </a>
              <figcaption>
                {shown.screenshotLabel || "Latest capture"}
                {shown.screenshotAt ? ` · ${shown.screenshotAt}` : ""}
              </figcaption>
            </figure>
          ) : <p>No screenshot yet.</p>}
          {shown?.reason ? <p><b>Latest decision.</b> {shown.reason}</p> : null}
          {shown ? <p>{shown.explanation}</p> : null}
          {shown ? (
            <button className="btn" type="button" disabled={!["queued", "running", "verifying"].includes(shown.state)} onClick={() => onStop(shown.id)}>
              Stop
            </button>
          ) : null}
        </section>
      ) : null}

      {widgets.has("milestones") && shown ? (
        <section className="dashboard-card">
          <h3>Checks</h3>
          <ul>
            {(shown.checks || []).map((check) => (
              <li key={check.id || check.name}><b>{check.name}</b> {check.status}{check.detail ? ` — ${check.detail}` : ""}</li>
            ))}
          </ul>
          {(shown.goalAttempts || []).length ? (
            <ol className="action-log">
              {shown.goalAttempts?.map((attempt, index) => (
                <li key={`${attempt.url}-${index}`}>
                  <span>{attempt.ok ? "Passed" : "Failed"} · {attempt.detail}</span>
                  {attempt.url ? <small>{attempt.url}</small> : null}
                  {attempt.priceCeiling != null && attempt.priceCeiling !== "" ? <small>Price ceiling {String(attempt.priceCeiling)}</small> : null}
                </li>
              ))}
            </ol>
          ) : <p className="check-note">No goal result has been recorded yet.</p>}
        </section>
      ) : null}

      {widgets.has("coverage") && shown ? (
        <section className="dashboard-card">
          <h3>Coverage</h3>
          <p>Visited: {(shown.coverage?.visited || []).join(", ") || "none yet"}.</p>
          <p>Planned and not visited: {(shown.coverage?.unvisited || []).join(", ") || "none listed"}.</p>
          <p className="check-note">Unvisited means those paths were not opened in this run. It does not mean the rest of the site was reviewed.</p>
        </section>
      ) : null}

      {widgets.has("search") && shown ? (
        <section className="dashboard-card">
          <h3>Search and navigation</h3>
          <ol className="action-log">
            {(shown.actions || []).filter((action) => /search|catalog|nav|filter|fill|menu/i.test(`${action.summary} ${action.url}`)).map((action, index) => (
              <li key={`${action.seq ?? index}`}><span>{action.summary}</span>{action.url ? <small>{action.url}</small> : null}</li>
            ))}
          </ol>
          {(shown.actions || []).some((action) => /search|catalog|nav|filter|fill|menu/i.test(`${action.summary} ${action.url}`))
            ? null
            : <p>This run has no recorded search or navigation action yet.</p>}
        </section>
      ) : null}

      {widgets.has("funnel") && shown ? (
        <section className="dashboard-card">
          <h3>Steps</h3>
          <ol className="action-log">
            {(shown.actions || []).map((action, index) => (
              <li key={`${action.seq ?? index}`}>
                <span>{action.summary}</span>
                {action.outcome ? <em>{action.outcome}</em> : null}
                {action.url ? <small>{action.url}</small> : null}
              </li>
            ))}
          </ol>
        </section>
      ) : null}

      {widgets.has("personas") && agents.length ? (
        <section className="dashboard-card">
          <h3>Persona comparison</h3>
          <table className="recorded">
            <thead><tr><th>Agent</th><th>State</th><th>Actions</th><th>Requests</th><th>Elapsed</th></tr></thead>
            <tbody>
              {agents.map((item) => (
                <tr key={item.id}>
                  <td>{item.label}</td>
                  <td>{stateLabel(item.state)}</td>
                  <td>{item.browserActions || 0}</td>
                  <td>{item.requests || 0}</td>
                  <td>{clock(item.elapsedMs)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="check-note">These counts are this launch. Elapsed time includes model latency. One run is not a population.</p>
        </section>
      ) : null}

      {widgets.has("recommendations") ? (
        <section className="report" aria-label="Investigation report">
          <header>
            <h3>Recommendations</h3>
            <button className="btn" type="button" onClick={onExport}>Export brief</button>
          </header>
          {reportStatus === "writing" ? <p>Writing the report from the recorded actions and screenshots.</p> : null}
          {report?.checkAlignment ? <p><b>Recorded check.</b> {report.checkAlignment}</p> : null}
          {report ? (
            <>
              <p>{report.summary}</p>
              {report.ok ? (
                <p className="check-note">
                  The reasoning model wrote this from the recorded actions
                  {report.screenshotCount ? ` and ${report.screenshotCount} screenshots taken across the run` : ""}.
                  Stated severity, confidence, and priority are the model's words.
                  {report.note ? ` ${report.note}` : ""}
                </p>
              ) : <p>{report.error}</p>}
              {(report.recorded || []).length ? (
                <table className="recorded">
                  <thead><tr><th>Persona</th><th>Status</th><th>Goal check</th><th>Actions</th><th>Blocked</th><th>Elapsed</th></tr></thead>
                  <tbody>
                    {report.recorded?.map((row) => (
                      <tr key={row.runId}>
                        <td>{row.name}</td>
                        <td>{row.status}</td>
                        <td>{row.goal || "—"}</td>
                        <td>{row.actionCount ?? "—"}</td>
                        <td>{row.blockedCount ?? "—"}</td>
                        <td>{clock(row.elapsedMs)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : null}
              {(report.personas || []).map((persona) => (
                <article key={persona.name}>
                  <h3>{persona.name}</h3>
                  <p>{persona.completed ? "The acceptance check passed." : "The acceptance check did not pass. That is separate from whether a product problem is supported."}</p>
                  {persona.conditions ? <p>{persona.conditions}</p> : null}
                  {persona.difficulties ? <p><b>Difficulties.</b> {persona.difficulties}</p> : null}
                </article>
              ))}
              {COMPARISON.filter(([key]) => report.comparison?.[key]).map(([key, label]) => (
                <p key={key}><b>{label}.</b> {report.comparison?.[key]}</p>
              ))}
              {(report.findings || []).map((finding) => (
                <article key={finding.id} className="finding">
                  <header>
                    <h3>{finding.title || "Finding"}</h3>
                    <em>{finding.kind}</em>
                    <em>{finding.status}</em>
                    {finding.supported === false ? <em>unsupported</em> : null}
                  </header>
                  <p><b>Where.</b> {finding.where}</p>
                  <p><b>Observed.</b> {finding.observed}</p>
                  <p><b>Personas.</b> {finding.personas}</p>
                  <p><b>Goal.</b> {finding.goal}</p>
                  <p><b>Impact.</b> {finding.impact}</p>
                  <p><b>Why this change.</b> {finding.why}</p>
                  {finding.tradeoff ? <p><b>Tradeoff.</b> {finding.tradeoff}</p> : null}
                  <p><b>Retest.</b> {finding.retest}</p>
                  <p>Stated severity {finding.severity || "—"}. Stated confidence {finding.confidence || "—"}. Stated priority {finding.priority || "—"}.</p>
                  {finding.evidenceNote ? <p className="check-note">{finding.evidenceNote}</p> : null}
                  {(finding.evidence || []).map((item) => (
                    <figure key={item.id}>
                      <a href={evidenceUrl(item.id)}>
                        <img src={evidenceUrl(item.id)} alt={item.label || "Evidence screenshot"} />
                      </a>
                      <figcaption>{item.label || "Screenshot"}</figcaption>
                    </figure>
                  ))}
                  <label className="field">
                    <span>Proposed change</span>
                    <textarea rows={3} value={finding.change} onChange={(event) => onEditFinding(finding.id, { change: event.target.value })} />
                  </label>
                  <label className="field">
                    <span>Acceptance</span>
                    <textarea rows={2} value={finding.acceptance} onChange={(event) => onEditFinding(finding.id, { acceptance: event.target.value })} />
                  </label>
                  <div className="finding-actions">
                    <button className="btn" type="button" onClick={() => onSaveFinding(finding, { status: "edited", change: finding.change, acceptance: finding.acceptance })}>Save edit</button>
                    <button className="btn" type="button" onClick={() => onSaveFinding(finding, { status: "accepted" })}>Accept</button>
                    <button className="btn" type="button" onClick={() => onSaveFinding(finding, { status: "rejected" })}>Reject</button>
                  </div>
                </article>
              ))}
            </>
          ) : <p>Recommendations appear after the investigations finish.</p>}
        </section>
      ) : null}

      {widgets.has("evidence") && shown ? (
        <section className="dashboard-card">
          <h3>Evidence</h3>
          <ol className="action-log">
            {(shown.actions || []).slice(-12).map((action, index) => (
              <li key={`${action.seq ?? index}`}>
                <span>{action.summary}</span>
                {action.reason ? <small>{action.reason}</small> : null}
              </li>
            ))}
          </ol>
          {shown.screenshotId ? (
            <p><a href={evidenceUrl(shown.screenshotId)}>{shown.screenshotLabel || "Open the latest screenshot"}</a></p>
          ) : null}
        </section>
      ) : null}
    </aside>
  );
}
