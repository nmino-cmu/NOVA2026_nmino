# NOVA / Ghost Users — consolidated project plan

Prepared November 7, 2026. This document synthesizes the accessible NOVA conversations, the original algorithm request, the supplied Astra design, and the current repository. It is a recommended implementation plan, not a claim that the proposed features already work.

## 1. Project definition

**Ghost Users is a self-hostable browser investigation workspace. A developer supplies an application, a workflow goal, and constraints; the system executes bounded investigations, verifies its results, and exposes the evidence in an interactive dashboard.**

The full product loop is:

1. Describe the application and desired outcome.
2. Turn that request into an editable task with starting conditions, allowed actions, success checks, metrics, and budgets.
3. Investigate the application through a local browser.
4. Show observed workflows, reproduced problems, unresolved questions, and supporting evidence.
5. Let the developer review and select proposed improvements.
6. Export a bounded implementation brief; dispatch to a coding agent only when authorized.
7. Rerun the same acceptance checks after the application changes.

Competitor comparison and model portability extend this loop. They do not need independent testing engines.

The first engine mode is narrower:

> Find a verified feasible workflow with low logical interaction cost under a fixed investigation budget. Report the best verified workflow found, its conditions, and what remains unexplored.

This preserves the broader product vision while giving the six-hour submission an implementable center.

## 2. Evidence reviewed and limits

The app inventory exposed four chats in the NOVA ChatGPT project. I reviewed their returned message histories, four related chats, and both attached algorithm documents. Active and archived listings were checked; no archived ChatGPT chats were returned. Shared branch messages were treated as shared history rather than independent agreement.

| Source | Contribution |
| --- | --- |
| [AI Beta Testing Idea](https://chatgpt.com/c/6aef3ee1-9488-83e9-8ef7-c60818deb904) | Product goals, guided setup, dashboard, graph visualization, competitor comparison, cloud/local inference, event-key restriction |
| [Branch · AI Beta Testing Idea](https://chatgpt.com/c/6aef4697-c594-83ea-9bdd-3b182af37b4d) | Full feature inventory, critical assessment, evidence-to-improvement loop, request for a rigorous algorithm design |
| [Branch · Branch · AI Beta Testing Idea](https://chatgpt.com/c/6aef4ddc-449c-83ea-a3a9-84ed170f8398) | Explicit preference for local graph computation with cloud semantic reasoning; later correction of overconfident product claims |
| [CMU Figma AI Access](https://chatgpt.com/c/6aef4a82-8dd8-83ea-858a-d84a76b47252) | Design-tool discussion; does not establish a runtime Figma dependency |
| [Brainstorm NOVA Ideas](https://chatgpt.com/c/6aef41a0-2cf0-83e9-b8bc-bf175b756b87) | Alternative-idea exploration; does not replace the subsequent Ghost Users plan |
| [Speculative Decoding Models](https://chatgpt.com/c/6aef5015-9034-83ea-8c16-8a00652fe5b3) | Adjacent local-inference discussion; does not make speculative decoding part of the browser-search algorithm |
| Develop NOVA hackathon project ideas — 01a1b698-c807-70d0-872d-1bf5fca6eaf6 | Event research and alternative concepts. Local session metadata identifies GPT-6.1 Terra, xhigh |
| Develop Graph Algorithm From File — 01a1b6cd-c403-73a0-ac6b-832131e8215f | Detailed algorithm and adversarial review. Local session metadata confirms GPT-6 Astra, ultra |

The chat reader returned recent message histories with no older cursor for the ChatGPT sources. Therefore this is a synthesis of all identified relevant chats and their exposed content, not a guarantee that every historical message was retrievable. Model identities were not exposed for the ChatGPT messages, so those are not inferred.

Primary supplied documents:

- [Original algorithm request](</Users/nicholasmino/.codex/attachments/51547ece-58e5-4fbc-a547-5c77bb96e406/Pasted text.txt>)
- [Supplied Astra design](</Users/nicholasmino/.codex/attachments/af1ced1e-552c-463b-a1ca-957473c20e60/Pasted text.txt>)

The later Astra design should guide the algorithm because it resolves concrete correctness problems in earlier proposals. A model label alone does not validate a design.

## 3. Decisions to retain and proposals to replace

| Earlier discussion | Consolidated decision |
| --- | --- |
| Crawl everything cheaply, then optimize | Interleave bounded control inspection with goal-directed execution. An arbitrary application cannot be exhaustively mapped |
| Use a large shared application graph | Keep an evidence graph, plus exact witnessed histories for search and verification |
| Optimize clicks, time, dollars, and uncertainty together | First obtain a verified route; then reduce logical interactions within separate resource limits |
| CAGE reward/information-gain divided by combined cost | Retain CAGE only as an optional project label. The MVP uses a specified lexicographic scheduler |
| Shortest path through discovered states | Return the best completely replayed route. Similar-looking states may make a graph path impossible to execute |
| Fade or prune irrelevant nodes | Defer heuristically; exclude only exact prefixes justified by a cost bound. Preserve observations |
| Many agents sharing one graph | Start with one browser worker. Parallel development workstreams are separate from runtime worker count |
| Simulate demographic usability | Start with measurable constraints such as keyboard-only actions; broader human-usability claims need other evidence |
| Local model is required for local graph work | Graph operations are ordinary local code. Local inference is a later interchangeable backend |
| Three dashboards and numerous metrics immediately | One polished workflow dashboard first; add objective-specific presets after the shared loop works |

Earlier prize predictions, numerical concept scores, illustrative graph counts, and hypothetical savings are not project results.

## 4. Scope by release

### A. Minimum working system

- One resettable browser fixture and one task.
- Structured task definition with executable initial, goal, and invariant checks.
- A bounded action grammar and finite supplied form values.
- Browser execution, observations, exact action history, screenshots/traces, and usage records.
- A competent baseline policy.
- Fresh full-route replay with passed, failed, or inconclusive verification.
- Persisted results that can be reopened.
- Basic findings and evidence inspection.

**Exit condition:** start from declared conditions, complete a real route, reset, replay the frozen sequence, and prove the specific goal with trusted checks.

### B. NOVA core demonstration

Add:

- Guided setup that produces a visible editable task specification.
- One stable dashboard layout: graph, current activity, best verified route, evidence panel, findings, and actual usage.
- Bounded candidate generation, graph-based prioritization, fairness selection, and safe prefix exclusion.
- Checked reuse of known navigation and exact-investigation deduplication.
- A visible improvement from an initial verified route to a shorter verified route, if the run discovers one.
- Budget and stopping reasons; unexplored regions remain explicit.
- A reproducible baseline comparison.

**Exit condition:** the entire setup-to-result loop runs through real events, and each highlighted verified route opens its replay evidence.

### C. Next cumulative features

Implement in this order when the core is stable:

1. Equivalent task comparison across a second supplied application.
2. Evidence-linked recommendations, with keep/edit/reject and implementation-brief export.
3. Rerun against a changed application using the same acceptance checks.
4. Custom compatible model endpoint and one demonstrated local-model workflow.
5. More objective presets and regression-test export.

Recommendation export may move earlier if the engine finishes promptly; it is cheaper than autonomous coding-agent dispatch.

### D. Later roadmap

- Broader bug discovery and systematic input exploration.
- Mechanically defined keyboard/accessibility policies.
- Controlled browser-performance experiments.
- More competitor workflows, milestone-aligned replay, and observed feature inventories.
- Persistent task dependencies and selective revalidation across builds.
- Stronger/smaller model routing when measured routing benefits justify it.
- Ambiguity probes and richer state refinement.
- Multiple isolated workers, ownership leases, and global request scheduling.
- Pause/checkpoint/resume, resource throttling, and background execution.
- Authorized coding-agent integration and post-change verification.

Automatic competitor discovery, arbitrary server snapshots, native mobile/desktop automation, model training, a general agent framework, speculative-decoding integration, and a dynamic widget-layout engine are outside the first build.

## 5. Architecture and ownership

The browser, controller, candidate scheduling, graph operations, metrics, persistence, verification, and dashboard run locally. Cloud models receive bounded observations when interpretation is necessary and return constrained structured decisions. A local model can later replace that inference service.

The cloud model does not need direct network access to localhost: the local controller observes the page, sends selected evidence, validates the response, and executes allowed actions.

Suggested module boundaries:

| Module | Owns |
| --- | --- |
| Task/evaluator registry | Versioned task, allowed actions, initial/goal/invariant checks |
| Browser runner | Reset, reach a witnessed prefix, execute one validated action |
| Observer | Structured controls, visible values, relevant events, screenshots and traces |
| Policy | Select an investigation from the current candidate set |
| Verifier | Frozen full replay and trusted checks |
| Evidence store | Immutable observations, transitions, histories, findings, decisions and events |
| Usage ledger | Request reservations, actual usage, resets, actions and timing |
| Dashboard | Derived projections and evidence inspection |

A practical starting point is the existing Python adapter plus Python browser execution. SQLite and an event stream are sufficient for the first persistent local system. A separate frontend can consume the same versioned event records. These are implementation recommendations, not an assertion that the conversations settled every framework choice.

Use an interchangeable policy interface so the baseline and proposed search share the runner, observer, verifier, store, and budgets. Neither policy receives an unrestricted browser handle.

Freeze these minimum record contracts before independent implementation:

| Record | Required relationships |
| --- | --- |
| TaskSpec | URL/origins, versions, trusted checks, action/data limits, reset adapter, model configuration, budgets |
| Observation | Witness prefix, context, document generation, settled status, structured/raw evidence and limitations |
| StateGroup / Transition | Member observations and grouping status / actual before-after observations, action, outcome and witness |
| Prefix / RouteWitness | Parent and transition, root observation, cumulative cost / continuous transition list and sequence hash |
| Candidate / Decision | Prefix, action or inspection purpose, revision, status, dedupe key, priority estimates / heuristic, bound or stop justification |
| Verification | Frozen route, reset evidence, initial/invariant/terminal check results, passed/failed/inconclusive, repaired=false |
| Usage / EvidenceRef | Operation, phase, resources, accounting status / persisted location, content hash, capture time and type |
| Checkpoint | Committed event sequence, frontier, incumbent, policy state, reservations and actual restoration capability |

All records carry stable IDs, run/task ownership, timestamps, relevant versions, and evidence links where applicable. Trusted checks resolve through an evaluator registry; model responses do not supply executable predicate code.

## 6. Algorithms to implement

### 6.1 Observation and bounded candidate generation

At a materially new observation:

1. Extract control roles, names, enabled state, relevant values, labels, and local text.
2. Enumerate only permitted actions.
3. Associate supplied data with clearly identified fields.
4. Track repeated controls as bounded families, retaining which instances were tested.
5. Record unscanned, disabled, and inaccessible regions.
6. Request semantic interpretation only for a specific unresolved question.

The Astra proposal suggests initial limits of 64 descriptors per scan chunk, two interpretation calls per unresolved observation revision, and 20 consumer actions per route. These are configurable starting settings to validate, not established optimal values.

Scanning discovers candidates. Only execution creates an observed transition. Do not draw an unexecuted candidate as an established edge.

### 6.2 Witness tree plus evidence multigraph

Maintain two structures:

- **Witness tree:** every history node has a parent, an actual transition, observations, context, and cumulative workflow cost. It answers exactly how that state was reached.
- **Evidence multigraph:** groups observations into approximate application-state summaries and records witnessed transitions. It supports retrieval, explanation, and visualization.

A URL, DOM hash, or screenshot similarity can suggest grouping, but does not establish behavioral equivalence. Cart contents, authentication, permissions, pending work, and server data can change what happens next.

The MVP does not discard one history merely because its final screen resembles another. Conflicts split a group when a distinguishing fact is known; otherwise the histories remain separate and the ambiguity stays explicit.

The witness tree supplies executable routes. A path assembled across graph groups is only a candidate until independently replayed.

### 6.3 Budgeted best-first investigation

First prioritize a newly witnessed, potentially improving route that needs verification.

For other eligible candidates q, choose the smallest lexicographic tuple:

    (relevance_class,
     prefix_interactions + candidate_interactions,
     estimated_restoration_actions,
     estimated_model_tokens,
     creation_order)

Relevance classes:

- 0: explicit task match or known prerequisite.
- 1: relevance unknown.
- 2: apparently unrelated.

Every fifth non-verification selection instead takes the oldest eligible candidate. Heuristically deferred candidates can participate. Invalid or unaffordable candidates cannot.

Recompute candidate priorities after new evidence, an improved incumbent, a context refinement, or a version change.

This is a heuristic bounded best-first search over action histories. It is not a claim to implement optimal A*, a solved POMDP, MCTS, or a calibrated information-gain optimizer. The fairness step can reveal a shortcut behind an initially unpromising menu; finite budgets can still miss it.

### 6.4 Branch-and-bound exclusion on exact prefixes

Let:

- g(p): known workflow interaction cost of a specific feasible prefix p.
- U: cost of an applicable verified incumbent.
- h_lower(p): justified lower bound on every completion of p.

When seeking a strictly shorter workflow, exclude extensions of that prefix if:

    g(p) + h_lower(p) >= U

For the MVP use:

    h_lower(p) = 0

This requires fixed applicable task/environment conditions, deterministic replay assumptions, and nonnegative additive interaction costs. It does not justify deleting the prefix's final abstract node. Another history may reach the same group more cheaply.

An LLM relevance estimate is not an admissible lower bound. Distance through an incomplete observed graph is not generally a lower bound on the application's unknown shortest route. If the incumbent becomes stale, reconsider the exclusions that depend on it.

Keep a separate total-action/depth limit even if a later click-only objective assigns zero cost to keyboard actions.

### 6.5 Strict route replay

Freeze the exact action sequence, task version, environment, and predicates.

1. Reset the relevant browser and server fixture state.
2. Check initial conditions.
3. Replay each allowed action with freshly resolved locators.
4. Check required invariants and explicit asynchronous completion conditions.
5. Check the terminal goal over the declared stability interval.
6. Persist passed, failed, or inconclusive evidence.
7. Update the incumbent only on an applicable pass.

Do not repair a frozen verification into a pass. Recovery during exploration produces a different candidate route.

Browser storage alone is not a generic server-state reset. If restoration cannot be established, restrict the claim and report the limitation. One successful stochastic replay establishes an observed success, not a reliability probability.

### 6.6 Reuse, deduplication, and invalidation

Adopt the smallest useful efficiency package:

- Structured full observations before implementing deltas.
- Bounded retrieval of the selected history and relevant evidence.
- Exact-investigation deduplication by applicable context, history, action/data, versions, and purpose.
- Replay known sequences without repeated model planning when their preconditions hold.
- Selective screenshots where visual evidence matters.
- Central usage accounting.

Invalidate dependent records when the task/checks, app build, account/context, action policy, or relevant observation changes. Revalidate the chosen route fully after a build change. Unknown dependencies require conservative invalidation.

Resolve action targets from current observations; never reuse an ephemeral element reference blindly. If compression omitted a required control, expand the observation or remain incomplete.

### 6.7 Optional research extension: ambiguity probes

When grouped histories have conflicting outcomes, create a probe that inspects a distinguishing fact or performs an allowed experiment.

Rank probes by pending decisions affected, observed conflicts, lower restoration work, and age. Measure whether the extra probes reduce failed replay and repeated work enough to justify their cost.

This is a proposed extension. Neither novelty nor superiority has been established.

### Where ordinary shortest-path algorithms fit

BFS applies to a trustworthy graph with unit action costs; 0-1 BFS handles zero/one costs; Dijkstra handles nonnegative weights. They are local code with no inference cost.

They can help inspect known compatible subgraphs or a controlled oracle fixture. Running Dijkstra over approximate grouped screens does not turn incompatible transitions into an executable application workflow. The first search policy therefore prioritizes witnessed histories and verifies complete routes.

## 7. Objectives and accounting

Primary optimization is lexicographic:

1. Obtain a verified feasible route.
2. Improve its logical interaction count within remaining investigation budgets.

Default consumer primitives each cost one logical interaction: activate, fill one supplied field value, select one option, press a specified key/chord, and scroll one specified increment. Keep click and keyboard counts separately. A fill is not one physical keystroke.

Reset, restoration, observation, waiting, inference, and verification are investigation operations. Charge their actual resources, while keeping them separate from the consumer route cost.

Define separate caps for wall time, model requests/tokens, actual browser actions, route depth, retries, and optionally inference spending. Reserve enough capacity for route verification before optional exploration. Unknown provider usage stays unknown or estimated.

Do not silently obtain a shorter route through direct URL jumps, internal state mutation, forced clicks, or uncounted automatic scrolling when the task excludes them. Expand macros for costing.

An executable example goal is: logged out with an empty cart at the declared start; reach an enabled checkout form containing exactly one unit of product P after its update completes; never submit an order. Reaching the form and persisting a completed order are different tasks.

## 8. Implementation order and working checkpoints

Times below are relative six-hour targets, not promises about the current clock.

| Stage | Backend / algorithm | UI | Evaluation / integration | Exit evidence |
| --- | --- | --- | --- | --- |
| 0:00–0:30 | Freeze task/action/event records; create one resettable fixture and executable checks | Build one layout against clearly labeled development samples | Define task, counted actions, baseline and budgets | Shared contract and reset/check demonstration |
| 0:30–1:30 | Baseline policy, browser execution, observation capture, persisted events, usage and strict replay | Consume real events; inspect a route and evidence | Run one full baseline workflow | Actual verified end-to-end route |
| 1:30–2:30 | Witness histories, candidate generation, lexicographic selection, fairness and h=0 exclusion | Distinguish selected, deferred, excluded and verified records | Add shortcut and hidden-context cases | Proposed policy can run through the same harness |
| 2:30–3:30 | Checked restoration, bounded retries, stale-target handling, persistence and invalidation | Reconstruct from events after reconnect | Exercise delayed-update, modal and changed-build cases | Honest failure handling and reproducible results |
| 3:30–4:30 | Add only the most valuable reuse improvement | Polish setup, stable layout and evidence inspection | Freeze configuration and start comparison runs | Core demo and evaluation ready |
| 4:30–6:00 | Fix correctness defects; add a small extension only if stable | Prepare concise live flow | Complete measurements, export results, record genuine fallback trace | Reproducible submission |

The three workstreams share the same versioned records immediately. Backend owns the runner/policy; UI owns projections and interaction; evaluation owns fixtures, checks, harness and demonstration evidence. This does not require three runtime browser agents.

Prioritize a working end-to-end result at every checkpoint. If scheduling is unfinished, keep the baseline and evidence graph. If external restoration fails, demonstrate the controlled fixture. If inference is unavailable, deterministic candidate ordering still allows bounded exploration. Failed replay remains visible.

## 9. Dashboard and event contract

Use transactional records; publish events only after the records commit. An event contains schema version, ID, run/task/worker IDs, timestamp, increasing per-run sequence, entity reference, relevant versions, evidence references, and typed payload.

| Event | Essential content |
| --- | --- |
| state_discovered | Group and observation IDs; grouping fingerprint; equivalence status |
| transition_observed | Before/after observations, action, outcome, witness prefix |
| candidate_selected | Candidate revision, priority components and resource reservation |
| branch_deferred | Candidate/prefix, heuristic reason and reactivation trigger |
| branch_pruned | Exact prefix, strict-improvement scope, g/h/U, incumbent verification and assumptions |
| branch_reactivated | Prior decision, trigger and new revision |
| state_refined | Prior group, child groups and observation membership mapping |
| route_verified | Route, verification result, full witness, cost and applicable conditions |
| finding_recorded | Claim, suspected/reproduced status and reproduction evidence |
| usage_updated | Usage records and derived actual totals |
| task_finished | Stop reason, best verified route or null, unknowns, total usage and evidence manifest |

The UI distinguishes heuristic deferral from bound-based exclusion, and approximate grouping from proven equivalence. Highlight a passed route witness, not any visually convenient path.

Keep widget placement stable during a run. Reconnect using the last received sequence and tolerate duplicate event delivery. Evidence counts reconcile with records. A sample animation is labeled as a sample. Display actual tokens; a savings claim requires a measured comparison.

A persisted checkpoint restores search records. It does not promise to restore a live browser and arbitrary server state.

Stop with a specific reason: acceptable verified target reached, budget exhausted, configured search envelope exhausted, starting conditions unavailable, verification unavailable, user stop, or infrastructure failure. Budget/envelope exhaustion does not mean the application goal is unreachable. The task may finish with a best verified route or with none.

## 10. Evaluation and submission criteria

Use the same runner, observer, action grammar, goal checks, model configuration, initial conditions, budgets and verifier for:

1. Ordinary model-driven execution with compact recent history.
2. Model-driven execution with basic memory and checked navigation reuse.
3. The proposed history/graph selection policy.

Fixture variants should cover a normal route, a less obvious shortcut, visually similar states with different prerequisites, and delayed updates or an interrupting modal. Add a changed-build revalidation case. Keep oracle state IDs and shortest routes hidden from the policies.

The supplied design proposes four tasks × three policies × three prespecified runs = 36 cold runs, with example 90-second caps. Treat that as a pilot plan to validate against available time. If necessary, reduce the planned task set before collection and report the smaller scope. Keep failures. Include setup, reset, reconnaissance, retries, interpretation and verification in the accounting.

Report verified completion, best verified route interactions, time to first verified route, total tokens and requests, inference spending when known, investigation actions, restoration/verification work, replay passes/attempts and stop reason. Show cold and warm runs separately, including warm-up costs.

Useful core checks are witness soundness, prefix-pruning preservation on tiny oracle graphs, cost conservation, no silent verification repair, stale-action rejection, budget conservation, bounded termination, event consistency and version invalidation.

The product can be useful without winning every efficiency comparison. Only claim the benefit the measurements establish.

## 11. Current repository state and immediate next action

Observed at review time:

- [openrouter.py](/Users/nicholasmino/ProgrammingFiles/Hackathons/NOVA2026/openrouter.py): minimal OpenRouter request and chat-completion adapter.
- [scripts/verify_openrouter.py](/Users/nicholasmino/ProgrammingFiles/Hackathons/NOVA2026/scripts/verify_openrouter.py): provider smoke-test script.
- .env.example and .gitignore.
- One initial .gitignore commit; adapter/example/script files are untracked.
- No browser runner, graph search, evaluator registry, persistence layer, frontend or benchmark harness was present in the inspected project tree.

The existing adapter has not been exercised during this review. Neither runtime reliability nor model compatibility is established by its presence.

**Next implementation milestone:** define the shared task/action/event records, build a resettable checkout fixture with trusted initial/goal checks, and run one baseline workflow through a strict independent replay. Connect the dashboard to those real events before adding the optimizer.

Recorded event constraint: in the main chat, you said organizers prohibited using the supplied OpenRouter key to implement the project or power coding agents. Preserve that restriction in development; use separate authorized development access. The recorded statement does not settle every possible feedback use.

## 12. Technical references checked during this review

These sources support browser plumbing, not application-wide optimality or reliability:

- [Playwright Python locators](https://playwright.dev/python/docs/locators): role/label-based targets and fresh DOM resolution.
- [Playwright actionability](https://playwright.dev/python/docs/actionability): mechanical execution checks and assertion behavior.
- [Playwright authentication](https://playwright.dev/python/docs/auth): browser-context isolation and supported storage reuse.
- [Playwright Trace Viewer](https://playwright.dev/python/docs/trace-viewer): recording and inspecting actions, snapshots, screenshots, console and network evidence.

The supplied Astra design also cites research inspirations. This consolidation does not claim a new exhaustive literature review or transfer those papers' guarantees to this implementation.
