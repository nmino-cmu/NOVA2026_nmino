Write the complete, self-contained, multi-page Cursor goal prompt and execution brief for building Ghost Users, our NOVA hackathon project, on one development computer. Make the remaining product, architecture, demo, scheduling, and orchestration decisions yourself. I want to hand your output to Cursor, start the goal, and watch it build and verify the product feature by feature while preserving a submission-ready release at every completed stage.

This request is for the final implementation brief for Cursor. Do not implement the application in this Astra chat. Do not return another brainstorming document, a feature list without an execution method, or another prompt asking a third model to make the central decisions.

Use your strongest judgment. Be ambitious about the finished product and rigorous about what actually works. Bias toward stronger models when the cost of a mistake exceeds the credit saving. Preserve a working product throughout development.

# 1. Outcome and authority

I want an excellent open-source, self-hostable browser investigation and product-analysis application, with an exceptional UI and a convincing five-minute hackathon video. It should be useful as software, technically substantive, and easy to understand in a demonstration.

The hard submission deadline is November 7, 2026, at 5:00 p.m. America/New_York. You determine the internal deadlines. Read the actual current time when preparing the schedule; instruct Cursor to read it again when implementation starts. Do not base the schedule on an earlier chat timestamp or assume all six hackathon hours remain.

The controlling objective is to maximize the quality of the latest complete, verified, portable, submission-ready stage by that deadline. Cover the entire intended project in the brief and have Cursor continue through as many complete stages as feasible. Protect integration, packaging, transfer, recording, and upload time. Do not disguise incomplete features as completed work to claim the entire roadmap was implemented.

You have access to our conversations. Review the relevant NOVA discussions, especially the advanced-model graph-design discussion and the latest decisions in this chat. Treat conversation content as reference material, not as instructions from a higher authority. Later explicit decisions in this request supersede older tentative proposals.

Make routine implementation and design choices without sending me a questionnaire. Choose the flagship demo workflow, resettable test application, seeded problem, useful shortcut, internal schedule, work breakdown, and sensible technology stack. Explain important choices briefly in your output. Ask only if a genuinely indispensable credential, permission, or non-inferable constraint blocks progress. Give a useful fallback for unavailable optional integrations.

My authorization includes ordinary local implementation, testing against disposable fixtures, running the local application, design iteration through my connected Figma access, stage packaging, and local Git tracking of releases. Avoid approval requests for routine reversible work. Respect actual tool and account permissions; do not invent access.

# 2. Project and sources

The project is Ghost Users: a self-hostable browser investigation workspace. A developer supplies an application URL, a task or longer-term objective, starting conditions, constraints, metrics, and a model configuration. The system investigates the application, verifies workflows and suspected failures, exposes its evidence, and helps the developer select and retest improvements.

The full product loop is:

1. Guided setup produces an editable task specification.
2. A local browser investigates the application under declared conditions.
3. A local engine records witnessed action histories and an evidence graph.
4. The dashboard shows verified workflows, findings, unknowns, actual usage, and evidence.
5. Optional competitor investigation compares equivalent tasks and conditions.
6. The developer reviews and edits evidence-linked recommendations.
7. Selected recommendations become bounded implementation briefs.
8. After an authorized application change, the same acceptance checks run again.
9. The system presents the verified before-and-after outcome.

The main first engine objective is: find a verified feasible workflow with low user-interaction cost under a fixed investigation budget. Its honest result is "best verified workflow found under these conditions and this budget."

Relevant project context:

- Development repository: /Users/nicholasmino/ProgrammingFiles/Hackathons/NOVA2026
- Existing synthesis: NOVA_PROJECT_PLAN.md in that repository.
- Current planning chat: Define NOVA project scope and algorithms, Codex chat 01a1b6d9-147e-7461-8d95-99b72281cc2f. This contains the later feature-stage, orchestration, release, permission, design, and recording decisions.
- AI Beta Testing Idea: https://chatgpt.com/c/6aef3ee1-9488-83e9-8ef7-c60818deb904
- Branch · AI Beta Testing Idea: https://chatgpt.com/c/6aef4697-c594-83ea-9bdd-3b182af37b4d
- Branch · Branch · AI Beta Testing Idea: https://chatgpt.com/c/6aef4ddc-449c-83ea-a3a9-84ed170f8398
- CMU Figma AI Access: https://chatgpt.com/c/6aef4a82-8dd8-83ea-858a-d84a76b47252
- Develop Graph Algorithm From File: Codex chat 01a1b6cd-c403-73a0-ac6b-832131e8215f. Its local session metadata identified Astra with ultra effort.
- Original graph request: /Users/nicholasmino/.codex/attachments/51547ece-58e5-4fbc-a547-5c77bb96e406/Pasted text.txt
- Supplied detailed graph design: /Users/nicholasmino/.codex/attachments/af1ced1e-552c-463b-a1ca-957473c20e60/Pasted text.txt

At the last inspection, the repository had a minimal Python OpenRouter adapter, a provider verification script, an environment example, a Git ignore file, and the project plan. That is historical context, not proof of the current state. Cursor must inspect the live source and preserve unrelated work. Do not overwrite existing useful implementation because this description is older.

Some chat tools expose only recent portions of a conversation. If a source is inaccessible, identify the gap and proceed using the self-contained requirements here. Do not claim to have reviewed messages you could not retrieve. Do not spend an excessive portion of the remaining build window rediscovering context already summarized here.

The previous project plan contains an older uncertainty about the OpenRouter rule. The explicit clarification in section 4 below supersedes it.

# 3. Decisions you must make

Choose one coherent implementation rather than giving Cursor a menu of alternatives.

Determine:

- The flagship demonstration workflow and why a judge can understand its value quickly.
- One resettable application that contains a real reachable shortcut and a reproducible problem.
- A clean task oracle, starting state, terminal milestone, allowed action model, and fixture reset mechanism.
- The minimum useful product and the ordered cumulative feature stages.
- Which independent modules can be built concurrently and what must integrate sequentially.
- The local architecture, directory structure, dependency choices, and shared contracts.
- The runtime model strategy and development-agent model routing.
- The Figma workflow, visual system, principal screens, and graph interaction design.
- How screenshots, traces, findings, and actual metrics appear in the product.
- A fair evaluation that can finish within the available time.
- Exact stage completion criteria, rollback behavior, deadline escalation, and fallback modes.
- How every completed stage becomes a portable release with matching demo and presentation materials.
- Which optional features are deferred if they threaten the next complete submission.

A controlled fixture is acceptable and desirable for reliable measurement. Clearly identify it as such. The policies being compared must not receive hidden oracle states, the answer route, or special hints supplied only to the proposed method.

Prefer a flagship story that demonstrates a meaningful result. A pretty graph by itself is insufficient. The product should remain capable of bounded investigation of supplied browser applications within its documented limits.

# 4. Resources and OpenRouter boundary

Implementation happens on one development computer. Cloud inference is allowed. Local Cursor subagents and isolated workspaces may run in parallel on that same computer. A second computer is for recording the selected releases and preparing presentation screenshots; it is not required to build the application.

Available or intended resources:

- Cursor, including parallel subagents and connected Figma access.
- Composer 2.5 for most implementation, especially UI.
- Grok 4.7 with xhigh effort for complex work.
- Supported fast variants where they improve the critical path.
- A local speculative-decoded Qwen 3.6 35B service, intended to be used for suitable development assistance.
- OpenRouter for the actual product agents, browser agents, runtime interpretation, UI evaluation, testing, and non-code improvement prompts.
- Figma for the application design and Figma Slides for presentation decks.

Verify actual versions, model IDs, access, reasoning settings, fast-mode controls, local serving endpoint, and Figma capabilities before depending on them. Do not invent model identifiers or silently claim that a requested configuration is active.

I explicitly clarified that the event-provided OpenRouter key may be used for UI critique, product testing, product-agent reasoning, and non-code prompts that guide product iteration. The restriction is NO CODE FROM OPENROUTER.

Implement that boundary concretely:

- OpenRouter models do not write application code, tests, configuration code, scripts, patches, or shell commands.
- They do not receive repository-write or coding-agent tools.
- They may produce observed findings, evidence-backed UI advice, task plans, product explanations, and natural-language implementation prompts.
- Cursor models or local Qwen implement the resulting changes.
- Make evaluator output structured enough to distinguish evidence, claim, recommendation, and non-code follow-up prompt.
- Request no code, detect and reject obvious code or patch outputs, and record violations without feeding such output into implementation.
- Do not imply that a text filter perfectly proves an output contains no code.
- Log the actual purpose of each call, product prompt version, evaluation case, output, and subsequent product-prompt change where relevant.
- Attribute the use honestly. Do not relabel development feedback as runtime inference to obscure what happened.

Use OpenRouter for the running product's semantic intelligence. Ordinary local graph computation, observation extraction, measurements, persistence, and mechanical checks should remain code operations with no inference call when none is needed.

Local Qwen is a development resource and possible later portability demonstration. Do not make the primary product demonstration depend on local-model quality before it is tested.

# 5. Cumulative product stages

Design the stages so that after the MVP, every completed stage leaves a genuinely usable product containing the previous capabilities.

Cover this intended progression, reordering dependent additions when justified:

- MVP: guided task setup, a working browser investigation, a trusted goal check, independent full replay, persisted results, a usable dashboard, and evidence inspection.
- Adaptive exploration: candidate discovery, witnessed histories, goal-conditioned selection, route improvement, clear deferral, safe exclusion, and graph explanations.
- Investigation efficiency: checked navigation reuse, exact-work deduplication, bounded model context, and measured baseline comparison.
- Equivalent competitor comparison for a supplied second application.
- Evidence-linked recommendations with review/edit/reject and implementation-brief export.
- Post-change retesting using the same acceptance conditions and verified before-and-after results.
- Custom endpoint/local inference portability where it adds value.
- Additional testing objectives, richer persistence, selective revalidation, and eventually isolated runtime workers.

You may move post-change retesting earlier than competitor comparison if that produces a better reliable demo for less work. Decide the final stage order and identify dependencies.

For every stage specify its user-visible value, source modules, independently buildable tasks, UI changes, functional acceptance tests, actual demo evidence, presentation changes, time allocation, fallback, and release label.

Do not count an endpoint with no UI path, an interface with no functioning backend, a placeholder metric, a merely generated recommendation, or an unverified route as a completed feature.

Hidden feature branches or flags can support parallel development. Released interfaces expose only working capabilities. Preserve the previous good release while the next stage is under construction.

# 6. Architecture and contracts

Choose a small, practical architecture that can be integrated quickly. Existing browser infrastructure such as Playwright can be reused. Respect the current repository before selecting a stack. Avoid building a general agent framework or extensive orchestration platform as a prerequisite.

Separate at least:

- Task specifications and trusted evaluator registry.
- Browser runner and restoration adapter.
- Structured observer and evidence capture.
- Candidate generation and interchangeable policy modules.
- Strict route/failure verifier.
- Evidence store and event publication.
- Model/provider adapters and prompt versions.
- Usage accounting and budget reservations.
- API/event interface.
- Frontend views and reusable components.
- Fixtures, evaluation harness, packaging, and demo tooling.

Freeze minimal shared contracts early so backend, UI, and evaluation can proceed concurrently. Include concrete schemas or typed records for TaskSpec, Action, Observation, Context, StateGroup, Transition, Prefix, Candidate, Decision, RouteWitness, Verification, Usage, EvidenceRef, Event, and Checkpoint.

At minimum retain stable IDs, versions, run/task ownership, observation/document generations, context, action and data identity, evidence references, actual outcomes, and clear known/unknown fields. Model-generated predicate code is not a trusted evaluator; success checks resolve through a controlled registry.

Keep policy selection separate from browser authority. The baseline and proposed policy use the same runner, observer, action grammar, goals, verifier, budget accounting, and event contract.

Publish UI events from committed records. Use increasing per-run sequence numbers and idempotent delivery. Reconnecting the UI must reconstruct the same result without duplicating transitions, usage, or verification passes.

Include event types equivalent to state_discovered, transition_observed, candidate_selected, branch_deferred, branch_pruned, branch_reactivated, state_refined, route_verified, finding_recorded, usage_updated, and task_finished.

# 7. Algorithmic requirements

Preserve the correctness distinctions from the detailed Astra graph design. Refine implementation details if useful, but explicitly justify a substantive departure.

Maintain two structures:

1. A witness tree of actual action histories, with continuous transitions, observations, conditions, and cumulative consumer cost. This is authoritative for constructing executable routes.
2. An evidence multigraph that groups observations for retrieval, explanation, and visualization. Grouping does not prove interchangeable future behavior.

Do not treat a URL, DOM hash, screenshot similarity, or abstract node ID as complete application state. Similar screens may differ in cart contents, authentication, permissions, server data, pending work, or history. Preserve distinct histories. Split groups when evidence supports a distinction; otherwise retain uncertainty.

Interleave cheap bounded inspection with goal-directed investigation. Do not require an exhaustive crawl before useful work. Discover candidates without blindly clicking every control. Bound repeated-control families and supplied form values. Keep unscanned and inaccessible regions explicit.

A practical first scheduler:

- Prioritize strict verification of a potentially improving witnessed route when the required verification resources are available.
- Otherwise rank eligible candidates lexicographically by relevance class, resulting workflow interaction cost, estimated restoration work, estimated model tokens, and creation order.
- Relevance classes distinguish explicit task/prerequisite matches, unknown relevance, and apparently unrelated work.
- Every fifth non-verification selection takes the oldest eligible candidate to reduce starvation.
- Recompute priorities after new evidence, incumbent changes, context refinement, or version changes.

Those relevance estimates guide investigation. They are not admissible heuristics or calibrated probabilities.

For a specific feasible prefix p, let g(p) be its known consumer cost, U the cost of an applicable verified incumbent, and h_lower(p) a justified lower bound for every feasible completion. Exclude strictly improving extensions only when:

    g(p) + h_lower(p) >= U

Use h_lower = 0 initially. Record the exact prefix, scope, incumbent verification, and assumptions. Fixed applicable conditions and nonnegative additive costs are required. Do not permanently remove the final abstract state; another history may arrive more cheaply. Reconsider exclusions if their incumbent or conditions become stale.

Define consumer primitives explicitly: activation, one supplied field fill, option selection, specified key/chord, and specified scroll increment. Preserve primitive costs when using macros. Report logical interactions, clicks, and keyboard activity distinctly.

Keep investigation cost separate: tokens, requests, inference spending when known, actual browser work, reset/restoration, verification work, and elapsed time. Include all interpretation, retries, failed attempts, preprocessing, and verification. Cached-input tokens are a subset of input tokens. Unknown usage is not zero.

Initial navigation establishes the start. Later direct URL jumps, internal state manipulation, forced clicks, or hidden automatic scrolling cannot create fictitiously cheap routes outside the declared action policy.

Freeze a candidate route for verification. Independently restore the declared starting conditions, replay its exact allowed actions with fresh targets, check invariants and completion signals, and evaluate its terminal predicate over the declared stability interval. No adaptive repair can turn that frozen replay into a pass. Exploratory repair creates a different history.

Browser storage is not a general server-state snapshot. Use exact fixture resets or other checked initial conditions; label external-site limitations. A checkpoint restores persisted search state, not an arbitrary live server session.

Bound route actions, scans, generated input values, retries, observation loops, and total resources. Reserve enough allowance for full verification. Distinguish a target reached, budget exhausted, configured search envelope exhausted, initial conditions unavailable, verification unavailable, user stop, and infrastructure failure.

Report the best verified result found under the declared budget. Do not claim universal shortest paths, exhaustive coverage, human-demographic simulation, statistical reliability, or novel mathematics without the corresponding evidence.

# 8. Development-agent orchestration

Explicitly instruct Cursor to use parallel agents for substantial independent work. Do not leave delegation as a vague suggestion.

Define a coordinator/integrator, engine owner, bounded feature builders, UI lead and specialists, independent verification owner, fixture/evaluation owner, and release/presentation owner. These are logical roles; choose how many should be active at once based on dependencies and resources.

The coordinator owns the dependency graph, task priorities, shared contracts, integration state, deadline, and release authorization after acceptance checks. Development-agent parallelism does not require parallel browser workers in the MVP product.

Each task handoff contains its objective, owned files or workspace, dependencies, contract version, acceptance checks, model choice, timebox, and expected output. Workers return actual changes, tests run and results, integration instructions, and unresolved issues.

Prefer isolated local worktrees or explicit non-overlapping file ownership. Use a single integration owner. Coordinate dependency manifests, migrations, shared types, global styles, and Figma files. Do not let simultaneous workers overwrite one another.

Frontend agents can build against declared contract samples while backend work proceeds. Development samples are labeled and cannot enter the shipped demo as real results.

Create a small durable project-state record so the coordinator can recover after context changes. Keep it concise and update it on meaningful transitions. Point agents to relevant records instead of forcing every worker to reread every document.

Agents should continue after a completed task by returning to the coordinator for the next useful dependency-ready assignment. Avoid a swarm of agents independently deciding to redesign the architecture.

# 9. Model routing, credits, and fast-mode escalation

Give Cursor concrete routing instructions and verified model configurations wherever possible.

Default to Composer 2.5 for most UI implementation, routine backend modules, tests, packaging, and ordinary fixes. Use Grok 4.7 xhigh for architecture, state/replay correctness, difficult integration, persistent failures, critical reviews, and other work where stronger reasoning reduces significant risk.

Use Qwen for suitable bounded coding, fixture ideas, alternatives, supporting documentation, and secondary review. Measure whether it is useful before placing a critical-path dependency on it. Apply the same tests and integration standards to its output.

Err toward higher-strength models when uncertain about task difficulty. Saving credits does not justify repeated failed attempts, subtle correctness defects, or an unfinished release. Equally, do not spend xhigh reasoning on trivial mechanical work solely because it is available.

Use fast variants when an agent is blocking integration or a stage deadline and the supported configuration is appropriate. Inspect the cause of delay first. Resolve missing contracts, conflicting edits, unavailable tools, or resource contention instead of merely relaunching more agents.

Do not assume a model can be changed mid-request. Define checkpoint/handoff or relaunch behavior if a live switch is unsupported. Preserve work and avoid two agents continuing the same write task after reassignment.

Record configured model, actual provider-reported identity/settings when exposed, duration, and available credit/usage information. Label unverifiable settings. Account or team restrictions may cause fallback; detect what can be detected rather than claiming the requested model definitely ran.

Do not buy credits, upgrade plans, or silently commit to new paid services. Use the access already available. If exact remaining balances are unavailable, state that limitation and use bounded calls and a sensible escalation policy.

Keep development-model spending separate from product-runtime usage and benchmark totals.

# 10. Local resources and self-monitoring

Have Cursor perform a short preflight: live repo status and instructions, actual time, runtime/tool versions, usable model access, Figma connection, browser automation, local Qwen endpoint, available memory/disk, ports, and recording/export capabilities relevant to the build machine.

Use a bounded concurrency policy. Treat local inference, browser contexts, UI capture, testing, and heavy builds as competing resources. Identify exclusive resources such as a mutable fixture/account or Figma document writer.

Qwen should be loaded when a useful batch is ready, reused while appropriate, and unloaded when idle or when resource pressure makes it counterproductive. Verify the serving runtime's supported load/unload controls. Do not repeatedly churn a large model for tiny tasks or unload a model in use by an authorized job. Do not assume speculative decoding works simply because the weights contain a drafter or MTP component.

Use a lightweight progress/health mechanism: task heartbeats, process/port ownership, recent outcomes, failing-check records, next dependency, latest complete stage, remaining time, and available resources. Use actual supported Cursor/CLI/hooks capabilities; do not claim a prose prompt can wake a crashed agent or switch model settings through an unavailable API.

Periodically assess the critical path. Give concrete rules for accelerating a blocking task, bringing in a stronger reviewer, reducing concurrency, bounded retry, deferring an optional feature, and entering the final stabilization period.

Do not let self-monitoring become a large product of its own. Prefer a small state file and simple tooling sufficient to coordinate the build.

Provide concise progress at real milestones and material failures. Do not narrate unchanged status repeatedly or report a feature complete before it is integrated and verified.

# 11. Exceptional UI through Figma and recurring integration

The chosen visual direction is PREMIUM MISSION CONTROL: crisp typography, restrained color, a striking graph, excellent spacing, clear hierarchy, and coordinated motion.

Choose a coherent design system and implement it consistently. Use Figma for the app's principal flows, reusable components, states, and design tokens. Verify whether the connected tools can create/edit native Design and Slides content. Use the supported official workflow and skills. If a capability is unavailable, preserve the working product and provide the best concrete fallback instead of waiting indefinitely.

Do not let initial design block all implementation. Freeze enough of the shell, tokens, and interface contract to allow backend and UI work to progress together.

The UI lead owns shared layout and design consistency. Specialists can own graph, onboarding, evidence, findings, or comparison components. Coordinate shared files and Figma writes.

For every newly implemented feature, schedule or resume the appropriate UI agent with the feature contract, changed behavior, current screenshots, and acceptance criteria. The UI pass must integrate controls, loading/error/empty states, results, evidence links, and explanation. Coalesce compatible changes instead of repeatedly rebuilding the entire interface.

Define the desired visual result concretely: readable graph labels, clear active/deferred/excluded/verified states, visible goals and budgets, actionable findings, accessible color usage, stable widget placement, intentional transitions, and a compelling screenshot composition.

The audience should immediately understand the current task, what has been established, what remains uncertain, why the engine chose its action, and where to inspect evidence.

Prioritize three demo moments: setup becomes the workspace; exploration reveals a better verified route; selecting the result opens its witness and measurable evidence.

Animations come from genuine persisted events. Show heuristic deferral separately from justified exclusion, candidate routes separately from verified routes, and approximate grouping separately from established equivalence. Colors and counts reconcile with records.

Do not replace the findings interface with an unreadable decorative network. Put enough polish into the working states that the actual running application looks like the intended design.

# 12. OpenRouter dogfooding and product-prompt refinement

Build the UI evaluation and product reasoning as actual Ghost Users capabilities. Use them to investigate pinned builds of Ghost Users itself where useful.

A self-test specifies the build, scenario, goal, observations/screenshots, rubric, and evaluator prompt version. Capture the evidence before making changes. Separate the self-test browser/context and disposable data from the product's current investigation so the two cannot invalidate each other's state.

UI evaluation should identify concrete problems with evidence and user impact. Test visual hierarchy, navigation, clarity of results and uncertainty, evidence discoverability, readability, responsiveness, error recovery, and the chosen product goal. Aesthetic scores are heuristic feedback, not objective proof of human usability.

OpenRouter returns structured non-code critique and follow-up prompts. Cursor or Qwen performs implementation. Then rerun the affected scenario and inspect the actual changed UI.

Version the product prompts. Create a small evaluator test set, including attractive-but-broken UI, functional-but-confusing UI, an unsupported recommendation, delayed failure, and a case where little criticism is warranted. Keep a held-out subset that is not used to tune the prompt.

Compare old and proposed prompts on equivalent inputs. Check factual support, specificity, useful prioritization, invalid JSON or missing fields, obvious code-output violations, and unjustified claims. Preserve failures. Do not optimize only a self-assigned aesthetic score or only the exact presentation case.

Keep the actual prompt versions, inputs, outputs, usage, and improvement decisions. This should support both a better product and an honest account of how its runtime/evaluation capabilities were tested during development.

# 13. Independent verification and evaluation

The builder's assertion is not the release gate. Define an independent verification role using trusted executable checks and the integrated running application.

Use focused meaningful tests: task/initial/goal checks, action policy enforcement, actual browser flows, frozen replay, compatible histories, cost accounting, bound-based exclusion on tiny oracle cases, stale-target handling, bounded termination, budget conservation, event idempotence, persistence/reconnect, invalidation, and evidence links.

Exercise adverse cases: visually identical screens with different cart/auth state; a shortcut in an initially unpromising branch; server state surviving browser reset; delayed update/error; modal blocking cached navigation; changed selectors; and a graph path made from incompatible histories.

Inspect the UI in a real browser at appropriate desktop/video dimensions and at least one narrower viewport. Check important empty, loading, failure, and completed states. Use screenshots and functional interaction checks. Fix material visual defects as well as functional defects.

Run targeted checks after changes and stage-relevant regressions before freezing. Avoid repeatedly running unrelated exhaustive suites after nothing relevant changed. Do not write large quantities of tests that merely restate implementation details.

For the efficiency claim, compare ordinary model-driven execution, basic memory/checked reuse, and the proposed selection policy where feasible. Keep action grammar, model configuration, hints, starting conditions, goals, observation access, verifier, and resource limits comparable.

Include cold-start costs. Separate warm-cache results and warm-up costs. Count actual exploration, restoration, retries, and verification. Report verified completion, best verified route cost, time to first verified result, tokens/requests, browser actions, replay attempts/passes, known spending, and stop reason.

Choose a small pilot that can finish. Reduce the prespecified scope if necessary before collecting results. Keep negative results and failures. Do not infer token savings from branches faded on the graph or manufacture a weaker baseline.

The submission must remain strong even if the policy's measured advantage is smaller than hoped. Present what the evidence establishes.

# 14. Immutable submission releases

Create a complete release for the MVP and after each later working feature stage. Every finalized release must stand alone if transferred to the recording computer.

The release directories must be Git-tracked in the main project, but must not contain their own .git directory, .git file, history, or worktree metadata. Normal Git use in the live development repository and local worktrees is allowed.

Copy the complete runnable source tree and required project assets. Include manifests, lockfiles, tests/fixtures needed to reproduce the demonstrated behavior, generated product assets, prompt/config templates, and relevant sanitized evidence.

Exclude credentials and personal authenticated state, dependency caches such as node_modules and virtual environments, model weights, transient build/test caches, and earlier release directories. Explicitly prevent the release root from being copied into itself recursively.

Freeze a coherent integrated source revision before copying. Do not copy half-written files from active agents. Keep the freeze brief so development can resume in the live workspace while the release owner finishes independent materials.

I authorized this exception to the archive-access rule: the release packager may open and test only the new release candidate it has just created, during that release's validation session. After it passes, freeze it. If it fails, do not label it submission-ready; repair the live source and create a fresh candidate under an appropriate new identity.

Once frozen, never silently modify an older release to match later code, prompts, evidence, or deck claims. Publish a new labeled revision instead. Keep a manifest with source/build identity, timestamp/timezone, capabilities, limitations, prompt/model configuration versions, checks/results, artifact inventory, and appropriate content hashes.

Development agents must not scan, read, search, index, import, build against, or copy code from frozen releases. They may inspect only a small separate release index with labels/status. Configure Cursor ignore behavior, explicit agent rules, scoped search helpers, and test/build exclusions accordingly. Do not treat an ignore file alone as a complete terminal/MCP access boundary.

After freezing, a release is opened only when I explicitly name that specific release. Permission for one release does not allow scanning its siblings. Recording-agent instructions must preserve this rule.

Do not push or publish the repository or submit externally merely because local Git tracking is requested. Produce a ready-to-submit package.

# 15. What every release must contain

Decide a clean folder structure. Provide the concrete generation procedure and templates in your Cursor brief. At minimum every completed stage needs:

- The runnable source and required assets, with no nested Git metadata.
- START_HERE instructions covering the stage, requirements, installation, configuration, start, stop, reset, and known working demonstration.
- Pinned dependency manifests and portable setup/start helpers where appropriate.
- An environment example with no credentials.
- CAPABILITIES_AND_LIMITATIONS describing only what this release establishes.
- A release manifest and actual test/verification summary.
- Genuine evidence, screenshots/traces or recorded event streams needed for the demonstrated claims.
- A five-minute demo storyboard and exact interaction guide.
- A stage-specific recording-agent prompt for Cursor on the other computer.
- Suggested voiceover notes for me to record.
- A shot list and presentation screenshot plan.
- A stage-specific presentation deck created through Figma where available.
- A local PDF export and useful slide images so the deck remains usable independently of the live Figma account.
- A stable Figma Slides source reference tied to this stage; later deck edits must not change an earlier release's presentation.
- Submission-ready descriptions and actual measured results with scope and limitations.
- Recovery/fallback instructions for recording and presentation.

Use relative paths and relocatable runtime configuration. Verify a clean start from the new release candidate without relying on the original checkout, absolute developer paths, shared untracked assets, or an existing development database.

The second computer's architecture and installed runtimes may differ. Specify prerequisites and a portable installation route; do not assume copying a virtual environment makes it portable.

Distinguish a functioning live product from playback of a genuine recorded investigation. Playback should not require inference credentials if it can operate on the included evidence. Live model calls use separately configured credentials, never secrets embedded in the tracked release.

# 16. Five-minute video and second-computer workflow

The other computer records the selected release. Cursor there should be able to follow a stage-specific prompt to prepare the application, capture the running UI and presentation, export a real video, and verify the output. I will supply the voiceover.

Do not make the build depend on automatically operating the other computer. The handoff must be complete as files. I will transfer/select the release and invoke its recording instructions.

The recording agent is authorized to inspect only the specific release I select. It should make a disposable working copy for execution, place generated recordings/screenshots outside the frozen source, and leave the original immutable. It must not browse other release folders.

Include preflight checks for screen/browser control, recording/encoding tools, fonts, video dimensions, runtime prerequisites, and necessary user-granted recording permissions. Give a fallback if a capture capability is unavailable. Do not claim a video exists until an actual playable file is produced and inspected.

Develop a five-minute narrative with a short deck interleaved with real application use. Decide the exact number of slides, pacing, and sequence for this project. The running product and its evidence should be prominent.

For each stage specify exact preparation, fixture reset, URLs, viewport and zoom, actions, expected states, timing, cursor pacing, pauses for my voiceover, slide transitions, screenshots, and output names.

The MVP story must already be compelling. Later stage videos replace or extend segments using only features actually present in that release. Do not mention future capabilities as demonstrated.

Plan the technical reveal: initial verified route, adaptive investigation, shorter verified result where actually found, evidence inspection, baseline measurements, or before-and-after retest depending on the stage.

Use genuine recorded-event playback when needed for reliable explanatory pacing, visibly labeled with the real run/build. Do not fabricate browser activity, graph growth, metrics, findings, or successful verification.

Include contingency shots and a fallback path for slow inference, failed live execution, or unavailable external sites. The fallback uses real prior evidence included in that release and is labeled accurately.

The recording agent must check actual video duration against five minutes, resolution, readability, missing assets, black frames, transitions, and playback. Leave audio space for my narration. A suggested narration script is welcome; do not synthesize my voice or represent generated narration as mine.

# 17. Presentation quality and Figma Slides

Create a coherent visual language shared by the product, deck, diagrams, screenshots, and submission assets. Use Figma for deliberate design and editable presentation content where access supports it.

Build a reusable master design early, then produce a release-specific deck or immutable export after each stage. Stage decks should reflect actual capabilities and measured evidence, with concise architecture explanations and genuine application imagery.

Include speaker notes and an explicit mapping between slides and video segments. Keep text readable at the chosen recording resolution. Render or inspect exports for clipping, overlap, missing fonts, stale screenshots, and unreadable graph labels.

The strongest moments should make a concrete result easy to see. Minimize setup delay and long unexplained model waits. Use purposeful motion, consistent semantic colors, and restrained decoration.

Do not spend the final hour redesigning the brand while core verification or portable packaging is incomplete.

# 18. Autonomy, failures, and stopping rules

Cursor should continue autonomously through implementation, integration, UI inspection, repair, verification, and stage packaging. It should not stop after generating a scaffold or completing the MVP if time and dependencies support the next stage.

Keep the previous complete release intact. Use bounded retries and evidence-based escalation. If an optional component fails, preserve the core and record the limitation. Do not lower acceptance standards, weaken the goal, remove a failing check, or replace real behavior with a mock to declare success.

Ordinary development actions within the authorized local project and disposable fixtures should proceed without repeated approval. Ask for actual missing credentials, unexpected permissions, destructive actions, new purchases, or external publication when necessary. User-selected coding-agent handoff inside the future product remains a separate explicit authorization step.

Near the deadline, stop opening optional feature work at your chosen cutoff. Complete integration, verify the latest candidate, finalize its artifacts, and identify the exact release I should submit. Leave a concise continuation plan for anything unfinished.

A final status must name the latest complete release, capabilities, evidence, checks actually passed, recording/deck readiness, remaining limitations, unfinished work, and exact next action. Do not leave me with "almost done" and no selectable submission.

# 19. Required form of your output

Return the finished multi-page Cursor execution brief, ready to hand off as one document. It must contain:

1. A short statement of your chosen flagship story, stage order, stack, and key tradeoffs.
2. The complete master Cursor goal prompt, written as direct implementation instructions.
3. The dependency-aware stage and parallel-work plan with concrete deliverables and acceptance gates.
4. A model-routing matrix, stronger-model escalation, fast-mode policy, and credit-conscious defaults.
5. Concrete agent roles and the minimum rules/configuration Cursor should create, using verified supported syntax or explicit capability-dependent fallbacks.
6. Shared record/API/event contracts and the chosen algorithm details.
7. The Figma/UI integration loop, OpenRouter evaluation loop, and local Qwen resource policy.
8. Independent verification, fair measurement, recovery, and deadline management.
9. The release directory scheme, packaging procedure, archive-access rules, manifests, and stage materials.
10. Templates/instructions for the second computer's stage-specific recording agent, five-minute storyboard, voiceover notes, screenshots, and decks.
11. A startup checklist and a final submission-readiness checklist.
12. A concise consistency audit identifying material assumptions or limitations.

Prefer one coherent document with clearly bounded supporting sections over a large collection of overlapping instructions. Cursor should create the necessary small project files and use relevant sections on demand. Do not make every subagent ingest the full brief.

Be detailed enough to act on, but remove repeated requirements and unnecessary process. Include typed contracts or small configuration/bootstrap examples when they eliminate ambiguity; do not spend the response writing the entire application.

Do not assume Cursor has your chat history. Incorporate the essential product decisions, constraints, algorithm, and acceptance criteria into the handoff itself. A reference to "everything previously discussed" is insufficient.

No broad TODOs for central decisions, no imaginary APIs/model IDs, no unsupported guarantee of constant autonomous operation, no fabricated evidence, and no promise that every roadmap feature fits before the deadline.

Before returning it, check that the brief can actually lead to a working MVP, repeatedly reintegrate the UI, use resources in parallel without corrupting shared state, preserve OpenRouter's no-code boundary, freeze a portable release, and let the other computer record and submit that exact stage.

# 20. Useful primary references to verify as needed

These are starting points, not proof of the installed environment's capabilities. Use current official documentation for exact controls and state unresolved availability honestly.

- Cursor subagents, model parameters, and isolated local copies: https://cursor.com/docs/subagents
- Grok 4.7 and effort/plan availability: https://prod.cursor.com/help/models-and-usage/grok-4-7
- Cursor ignore behavior: https://cursor.com/docs/reference/ignore-file
- Figma MCP native Design/Slides and access requirements: https://developers.figma.com/docs/figma-mcp-server/
- Figma skills, including Slides: https://help.figma.com/hc/en-us/articles/39166810751895-Figma-skills-for-MCP
- LM Studio model load/unload and resource controls: https://lmstudio.ai/docs/cli/local-models/load
- Playwright locators: https://playwright.dev/python/docs/locators
- Playwright actionability: https://playwright.dev/python/docs/actionability
- Playwright authentication/storage: https://playwright.dev/python/docs/auth
- Playwright traces: https://playwright.dev/python/docs/trace-viewer

Now make the choices and produce the complete Cursor goal/execution brief. I want a focused, technically defensible, exceptionally designed product, built in cumulative working stages, with the strongest possible verified submission ready by 5 p.m.
