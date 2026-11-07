# Ghost Users / NOVA 2026
## Conversation packet and decision history

Prepared November 7, 2026, America/New_York.

This packet brings together the 12 identified conversations about Ghost Users and the connected NOVA project work. It contains a detailed synthesis, a record of changing requirements, the algorithm and product decisions, the implementation and release plans, the later audits, and the available user/assistant transcripts.

**The most important clarification:** the intended product is a conversation-driven product investigation workspace. The user discusses what they want to understand; the system clarifies the request, develops a suitable plan, creates a tailored live dashboard, launches relevant persona investigations, and delivers deep, correct, actionable advice supported by links and screenshots. A browser runner, a setup form, an animated graph, or a persisted report individually does not deliver that experience. This interpretation follows the latest explicit clarification in C12.

**Coverage limit:** this is a complete collection of the user and assistant messages returned for the identified sources, not a certified export of every message ever sent. Some ChatGPT histories expose only recent turns and return no older-page cursor. The Figma UI Prompt assistant response is explicitly truncated at 20,000 characters by the reader. Missing text has not been reconstructed. The archive preserves the retrieved message data and relevant local reference documents.

# 1. How to use this packet

Read sections 2-5 to understand what you were trying to build and how that idea evolved. Sections 6-9 explain the engineering and algorithm decisions, with the assumptions that make them defensible. Sections 10-12 preserve the build orchestration, release requirements, and observed implementation gaps. Section 13 records unresolved questions and gives acceptance examples derived from the latest requirements.

The transcript appendix retains each conversation separately, including repeated branch messages. Repetition shows shared conversational ancestry; it is not independent evidence that several reviewers agreed. Source IDs C01-C12 are used throughout this packet and appear in each transcript heading.

The ZIP archive also contains editable Markdown, structured message data, individual conversation files, a source register with hashes, supporting planning documents, and the two locally available historical images shared in C12. The PDF includes those images with captions that identify their historical context. Those supporting documents are historical inputs. Their instructions are quoted context, not new authorization to run the project, use a model, alter a release, or send information elsewhere.

## 1.1 What was searched and read

The app's active and archived history listings were paginated to their returned ends: 90 active Codex entries, 18 archived Codex entries, 469 active ChatGPT entries, and no archived ChatGPT entries. Selection used the NOVA project association, the current repository, conversation titles, and relevant summaries. The adjacent speculative-decoding discussion was included because the implementation planning explicitly referred to the local Qwen resource.

Twelve relevant conversations were read through the chat reader. The returned pages contained 46 user messages and 77 assistant messages. Some turns contain several progress messages or explicit answers to planning questions. Turn counts therefore differ from message counts.

An older, separate HackCMU brainstorming conversation was excluded because its project and event differed. Unrelated course, internship, and other project conversations were not included. The present packet-creation chat is also excluded from its own historical appendix.

## 1.2 Editorial treatment and evidence levels

The structured archive preserves the returned user/assistant text, apart from any detected API-key redaction. The readable transcript normalizes historical artifact wrappers, converts question-answer envelopes into readable answers, and replaces source markers whose destination was not returned with a clearly labeled historical-reference note. It omits hidden reasoning, tool calls, terminal output, system/developer instructions, and automatically supplied application context.

The PDF renders the normalized transcript and labels the one explicitly truncated response. Some original answers contain technical recommendations, product claims, prices, software versions, event interpretations, or model-performance claims. They are included as historical statements. This task did not reverify those external claims or rerun the application.

Four evidence levels should remain distinct:
- **User requirement:** what you explicitly asked for or clarified.
- **Proposed design:** an assistant recommendation or a planning document.
- **Reported observation:** a prior conversation's account of a running test, screenshot, or audit.
- **Current source declaration:** what a local status document says at packet capture.

The packet does not silently upgrade a proposal into an implemented capability, a test result into complete product acceptance, or an old status document into current verified behavior.

# 2. Source register and reading map

| ID | Exact conversation title | Main contribution |
| --- | --- | --- |
| C01 | AI Beta Testing Idea | Product expansion, guided setup, graph visualization, workflow/token objectives, OpenRouter restriction and correction |
| C02 | Brainstorm NOVA Ideas | Request for alternative NOVA ideas and delegation into a work conversation |
| C03 | Develop NOVA hackathon project ideas | Event-driven alternatives; rejection of an overdone direction and request for innovation |
| C04 | Branch · AI Beta Testing Idea | Critical evaluation, full feature inventory, request for the rigorous Astra algorithm brief |
| C05 | CMU Figma AI Access | Figma Education/AI discussion and design-tool integration |
| C06 | Branch · Branch · AI Beta Testing Idea | Correction of inflated novelty claims and explicit local computation/cloud reasoning architecture |
| C07 | Develop Graph Algorithm From File | Original algorithm request, inaccessible Library-link issue, detailed mathematical and execution design |
| C08 | Speculative Decoding Models | Local model/runtime discussion relevant to the proposed Qwen development resource |
| C09 | Define NOVA project scope and algorithms | Consolidated scope, cumulative features, hackathon evaluation, orchestration requirements, Astra handoff |
| C10 | Create Cursor build brief for Ghost… | Detailed Cursor execution brief and direct goal prompt |
| C11 | Figma UI Prompt | Extensive interactive prototype prompt; returned assistant message is truncated |
| C12 | Show the Figma file | Figma preview, live-system audits, missing capabilities, conversational/persona requirements, final clarification |

C01, C04, and C06 overlap. Preserve their relationship when interpreting apparent repetition. C02 and C03 form the alternative-ideas path. C07 supplies the technical correction to early graph claims. C09 and C10 transform that design into a build-and-release program. C11 covers the desired presentation. C12 is the most important source for the gap between the built mechanics and the experience you intended.

## 2.1 Supporting documents retained in the archive

The archive includes the original pasted algorithm request, the supplied Astra design, the pasted request for the execution brief, and the four live-root planning documents: NOVA_PROJECT_PLAN.md, ASTRA_GOAL_PROMPT.md, GHOST_USERS_CURSOR_EXECUTION_BRIEF.md, and CURSOR_GOAL_PROMPT.md.

It also captures selected live documentation and operational status files. The release index is represented only by release labels, stages, statuses, and the selected label. Frozen release directories were not used as source or opened for this packet.

The source register records paths, capture hashes, and editorial status. Copies are provided for historical review, not as a new runnable release or a claim that every instruction in them was fulfilled.

# 3. The product you wanted

## 3.1 The core promise

Across the early conversations, you wanted an open-source alternative to paid product-testing and analysis tools. It should help a developer understand how a website works for different users, find friction and failures, compare important workflows, and decide what to improve.

The later conversations make the interaction much more specific:
1. Describe a website and an investigation request in ordinary language.
2. Have a useful discussion with an agent about goals, audience, constraints, and priorities.
3. Review a plan that contains appropriate tasks, personas, checks, budgets, and expected outputs.
4. Refine and accept that plan.
5. Receive a dashboard configured for that investigation.
6. Watch real browser work, persona progress, and the graph develop together.
7. Read substantial findings tied to exact actions, relevant screenshots, URLs, and checks.
8. Ask follow-up questions, accept or reject findings, and commission deeper or changed work.
9. Review an implementation brief and retest a real change under the same relevant acceptance conditions.

This is a coherent product loop. The workflow optimizer is an engine within that loop. It does not replace the product-analysis experience.

## 3.2 Conversation before configuration

You did not mean a chat-shaped setup form, a single prompt box, or a status feed labeled Agent activity. The agent should ask useful questions when a broad request lacks information, inspect the site when needed, and propose relevant investigations.

For a broad website review, useful unknowns include the site's purpose, audience, desired outcomes, important journeys, concerns, excluded actions, and budget. For a precise task, unnecessary interrogation would be friction: the agent can confirm the task and expose the remaining assumptions.

The agreed plan should be readable and editable. It should not force the user to know internal run IDs, evaluator names, or backend vocabulary. C12 specifically objected to disconnected review forms and an experience where the user could not see the system doing useful work or giving advice.

## 3.3 A dashboard that follows the request

The early idea was a guided chat that transforms into a dashboard with preset widgets selected according to the user's goals. The latest clarification preserves that idea.

A search investigation could emphasize queries, result quality, unsuccessful searches, and search-to-task journeys. An onboarding review could emphasize entry points, steps, confusion, completion, and barriers. A persona comparison could emphasize individual journeys and supported differences. A general review could combine navigation, key tasks, page evidence, findings, and unexplored regions.

The implementation proposal in the latest audit uses a validated dashboard specification made from supported widget types. The reasoning model selects configuration data. It does not produce executable UI code. Stable widget placement during execution prevents the interface from moving under the user's pointer.

A single fixed plan editor, agent list, and report page for every request does not establish this requirement.

## 3.4 Personas as investigation policies

You wanted persona agents with individual investigations, visible progress, and actionable feedback. Persona names alone are insufficient. Each persona needs a task-relevant objective or constraint that can affect decisions, evidence selection, and interpretation.

Examples in the shopping work included price-conscious, search-focused, browse-oriented, careful, and hurried shoppers. Those are examples for that domain. A landing-page or documentation review should receive relevant personas rather than the same shopper roster.

A persona should expose its role, assigned work, current state, action history, findings, and uncertainty. Multiple runs that happen to follow the same route must be reported as matching observations. Different persona labels do not prove different behavior.

Agent attempts are also not a representative human-user study. One attempt per profile is a small amount of evidence about those attempts, not a population estimate or a demonstrated demographic effect.

## 3.5 Deep, actionable feedback

The repeated demand for in-depth advice means more than generating long prose. Each important finding should explain:
- The specific page, element, or step.
- What the agent actually observed.
- The persona and goal affected.
- Relevant actions, failed or passed checks, and surrounding context.
- Inline screenshots with descriptive captions and a way to inspect the full evidence.
- Likely impact and confidence, with reasons.
- A concrete proposed improvement.
- Useful alternatives or tradeoffs.
- Acceptance criteria and a practical retest.

A concise overview can coexist with expandable depth. An arbitrary four-finding cap and one-or-two-sentence fields conflict with the requested depth when substantial evidence exists. Conversely, a sparse investigation should not be padded with unsupported criticism.

Links should have useful labels. Raw evidence IDs are useful for provenance, but they are a poor primary presentation for advice. A report must retrieve the evidence relevant to each claim rather than rely only on the final screenshots.

# 4. How the idea evolved

## 4.1 From beta testing to product investigation

C01 expanded the idea beyond automated testing. You asked about reviewing the application's UI, scanning competitors, identifying useful features, proposing improvements, and optimizing user-defined metrics such as steps to checkout. You wanted cloud models for the strongest demonstration and optional local inference for portability.

The assistant initially framed a broad autonomous product-intelligence platform. That direction explains the full vision, but later sources narrow what can be claimed in a short build.

## 4.2 Cheap reconnaissance plus adaptive reasoning

You proposed using lightweight models or crawlers to map what they could reach before the optimization work. The subsequent correction was to interleave reconnaissance and goal-directed investigation. Waiting for an exhaustive crawl is impractical for dynamic applications, forms, permissions, and large data spaces.

The durable part of the idea is selective use of inference: ordinary code should inspect obvious controls, manage records, calculate priorities, and reuse checked knowledge. Expensive reasoning should answer specific semantic questions.

## 4.3 The graph as both explanation and optimization

You wanted a large, attractive, colored graph that visibly changes as the search focuses on the goal. Early answers described goal-conditioned pruning, possible routes, and token-aware exploration.

Later work corrected the underlying claim. A useful visualization can show discovered evidence, candidates, deferred branches, justified exclusions, and the best verified route. It must not treat a faded node as measured savings, a candidate edge as an executed transition, or a screen group as a complete application state.

## 4.4 Critical evaluation replaced inflated confidence

C04 asked for evaluation without reinforcing you if you were wrong. C06 explicitly corrected earlier overconfident novelty and winning claims. The resulting assessment was that usefulness and demo potential were plausible, while reliability, efficiency benefits, differentiation, and mathematical novelty needed evidence.

Historical scores are subjective opinions about a proposed design. They are not measurements, probabilities of winning, or current product results. The honest competitive story is a real product loop and a well-supported technical demonstration.

## 4.5 A local graph does not require a local LLM

You clarified that graph computation should run locally while cloud models power the agents. C06 agreed and separated ordinary computation from inference.

Browser execution, graph maintenance, search, accounting, persistence, mechanical verification, and rendering can run locally. Cloud inference interprets compact observations and returns constrained decisions. A local Qwen backend can replace inference later. It is not needed to perform graph arithmetic.

## 4.6 Rigorous algorithm work narrowed the guarantee

C07's governing correction was to search over witnessed action histories and use the graph to organize evidence. Similar-looking pages can conceal different cart contents, authentication, server state, pending updates, or arrival histories.

The system should report the best independently verified workflow found under declared conditions and a bounded budget. Without much stronger assumptions, it cannot claim the globally shortest workflow or exhaustive application coverage.

## 4.7 Cumulative releases became a build strategy

C09 asked whether the MVP could remain usable while features were added sequentially. The answer became a cumulative plan with a working checkpoint after each accepted stage.

You then asked for an ambitious orchestration prompt: parallel development agents, Figma, model routing, independent testing, repeated UI integration, time monitoring, immutable stage packages, decks, and recording instructions for the other computer. C10 produced the concrete execution brief and direct Cursor prompt.

## 4.8 The audits exposed a mismatch in completion

C12 found real browser mechanics and passing checks, but repeatedly showed missing end-user capabilities. The conversation then progressed through three sharper corrections:
- The product still lacked the conversational request-and-plan interface.
- Persona agents and deep actionable feedback were central requirements.
- Even a persisted conversation with persona runs and a report was insufficient without clarification, a tailored dashboard, a live embedded graph, general website investigation, and correct evidence-rich advice.

These later requirements clarify the product's center. They must not be buried beneath the earlier minimum-engine scope.

# 5. Decisions, corrections, and authority

| Topic | Earlier proposal or confusion | Consolidated interpretation |
| --- | --- | --- |
| Product center | Browser testing plus many optional panels | Conversation-driven investigation and actionable feedback, supported by the engine |
| Setup | Wizard or single prompt | Dialogue when needed, editable plan, then request-specific workspace |
| Graph state | URL or similar screen as one state | Approximate evidence groups plus separate exact histories |
| Route construction | Shortest path through grouped nodes | A continuous witnessed route, independently replayed |
| Pruning | Remove irrelevant parts of the graph | Reversible heuristic deferral; exact-prefix exclusion only under a valid bound |
| Optimization | Combine clicks, tokens, money, and time into a score | Workflow objective under separate investigation resource constraints |
| Reconnaissance | Map everything before reasoning | Bounded scans interleaved with execution |
| Model location | Local inference needed for local graph work | Local ordinary computation; cloud semantic reasoning; optional local inference |
| Persona evidence | Different labels imply different users | Separate policies and attributable attempts; report matching behavior honestly |
| Feedback | Generic failure text or short report | Specific, supported recommendations with relevant inline evidence and retests |
| Completion | Tests or endpoints marked done | Integrated, usable workflow plus requirement-specific evidence |
| Release | Later snapshot means later accepted product | Only a validated package supersedes the selected frozen release |
| Improvement claim | Graph animation implies savings | Prespecified measured comparison with all work charged |

## 5.1 OpenRouter clarification over time

C01 first received an answer that was too permissive about using the event key for development feedback. You then clarified that organizers prohibited using it to implement the project or power coding agents. The assistant corrected its interpretation.

Later in C09, you explicitly confirmed product agents, browser testing, UI critique, and non-code product iteration as permitted uses in your event context. The build plans adopted that clarification while retaining a no-code boundary.

The current repository instruction is narrower and concrete: OpenRouter is for product reasoning only; do not send it repository source or ask it to write code. This packet records that chronology. It is not a new legal or event-rules determination.

Product reasoning may return validated actions, evaluation data, or non-code advice. Repository implementation and code changes belong to the authorized development tools. An exported brief is not by itself permission for the product to modify somebody else's repository.

## 5.2 Release access and ownership

The repository assigns the coordinator ownership of contracts, the API, the store, manifests, and release authorization. It instructs agents to search live roots with scripts/live-search and not treat frozen release directories as source.

The selected frozen label remains GU-R01-20261107-r4 unless a later package passes its own validation. The release index labels GU-R08-20261107-r1 and GU-R08-20261107-r2 as snapshots. That distinction matters even if later live code contains additional capabilities.

The packet does not inspect or reopen those frozen packages and does not change release status.

# 6. Architecture and the two layers of agency

## 6.1 Product runtime

The product's runtime loop separates responsibilities:
- The conversation layer clarifies the user's request and keeps the investigation context.
- The planner creates structured, editable tasks and dashboard configuration.
- Persona policies choose bounded investigations appropriate to those tasks.
- The browser runner observes and acts within explicit scope.
- The search controller manages candidate work and exact histories.
- Trusted evaluators check initial conditions, invariants, and goals.
- The verifier performs an independent frozen replay.
- The evidence store persists observations, actions, checks, findings, and usage.
- The dashboard derives its views from actual records.
- The reporting layer retrieves relevant evidence and distinguishes fact from inference.

The cloud model does not need direct access to localhost. A local controller collects permitted observations, sends a bounded representation, validates the response, and executes an allowed action.

## 6.2 Development orchestration is a different system

The implementation plans also described multiple coding/design/review agents working on the project. Those development agents are distinct from the persona agents inside Ghost Users.

Several agents building UI, fixtures, and the engine do not establish that Ghost Users supports isolated concurrent browser investigations. Similarly, a development-time model switch does not prove the end-user provider selector changes a running investigation.

This distinction became important in later claims about worker support, model portability, and completion.

## 6.3 Shared contracts and durable records

The plans called for stable records carrying IDs, task/run ownership, timestamps, versions, and evidence relationships. The main concepts are:
- Task specification: goals, origins, initial conditions, allowed actions, evaluator versions, budgets, and reset capability.
- Observation: witnessed context, visible controls/values, document revision, readiness, screenshots, and limitations.
- Transition: actual before/after observations, action, outcome, and history witness.
- Prefix or route witness: a continuous sequence from a checked root with cumulative primitive cost.
- Candidate and decision: proposed investigation, eligibility, priority, selected reason, deferral, exclusion, and reactivation.
- Verification: frozen sequence, reset evidence, initial/invariant/goal samples, result, and repaired=false.
- Usage ledger: actual and reserved requests, tokens, charges, actions, resets, timing, and unresolved accounting.
- Finding and recommendation: supported claim, evidence, uncertainty, review state, change scope, and acceptance checks.
- Checkpoint: committed investigation state and explicit restoration limits.

Persistence must precede publication to the UI. Refresh and reconnect should reconstruct the same facts rather than add duplicate totals or fabricate a second event.

# 7. The algorithm, precisely enough to preserve its meaning

## 7.1 Concrete state, observation, and grouping

Let x be the full environment state: browser state, server state, account, cart, data, pending work, and any history that affects future behavior. The agent usually cannot observe x completely.

An observation o contains what was actually available: URL, visible text, roles, enabled controls, relevant values, screenshots, and declared instrumentation. A grouped graph node summarizes observations that look related. Group membership does not prove interchangeable futures.

A witness prefix p records the exact continuous sequence from a checked initial state to a particular observation. Its cost g(p) is the accumulated allowed consumer-action cost. A route is constructed from that sequence's own transitions.

## 7.2 Why the witness tree is authoritative

Consider two visits to a visually identical checkout page. One follows an actual committed cart update; another follows an Express action that navigated before the update committed. A graph that merges both screens may combine the arrival from the failed history with a successful outgoing edge from the other history.

That combined path may never have existed. The witness tree prevents this by preserving exact histories. The evidence multigraph can still group screens for visualization and retrieval, but it cannot manufacture a verified workflow by concatenating incompatible transitions.

When distinguishing evidence appears, a group can be refined or split. When equivalence remains unknown, keep the histories separate. Aggressive merging is an optional optimization only where its assumptions are established.

## 7.3 Bounded observation and candidate generation

The design enumerates permitted controls and supplied data without blindly executing every control. Example configuration limits in the brief are 64 control descriptors per chunk, three chunks, three repeated-control instances, and two supplied values per field. Those are proposed bounds, not optimal settings or measured product coverage.

Unscanned chunks, inaccessible frames, disabled controls, untested repeated instances, and unsupported actions remain explicit. An interpretation call is useful when a specific unresolved semantic question affects a decision. Unchanged observations should not cause endless model calls.

A candidate action is possible work. An observed transition exists only after execution. The dashboard must distinguish them.

## 7.4 Baseline before optimization

The first working engine should be a competent ordinary model-driven policy. It receives the current structured observation, task, compact recent history, and available candidates, selects a valid candidate, acts, checks, and eventually attempts strict replay.

This baseline shares the runner, observer, evaluator, store, and budgets with the adaptive policy. It should not be made artificially forgetful or forced to replan mechanical replay just to make the proposed optimizer look efficient.

## 7.5 The adaptive scheduling rule

The later design uses an implementable lexicographic scheduler rather than an uncalibrated reward-per-token formula. For eligible candidates, compare:

(relevanceClass, g(prefix) + actionCost, estimatedRestoreActions, estimatedModelTokens, creationOrder)

Relevance class is 0 for explicit goal/prerequisite matches, 1 for unknown, and 2 for apparently unrelated. Relevance and restoration/token estimates are heuristics. They are not probabilities, correctness certificates, or admissible lower bounds.

Every fifth non-verification selection chooses the oldest eligible candidate instead. Inspections and interpretations count toward that schedule. Invalid, excluded, or unaffordable work remains ineligible. The fairness rule protects uncertain branches from permanent starvation without pretending the search is exhaustive.

New evidence, incumbent changes, group refinement, and scope changes trigger affected priority updates. A justified candidate route receives a separate verification attempt when that work can fit the reserved allowance.

## 7.6 Exact-prefix exclusion

Let U be the cost of an applicable independently verified incumbent. For a particular feasible prefix p, let g(p) be its known cost and h_lower(p) a justified lower bound on every feasible completion. Initially use h_lower(p) = 0.

Exclude extensions from the search for a strictly shorter route only when:

g(p) + h_lower(p) >= U

This depends on nonnegative additive action costs, compatible task/build/environment conditions, a valid prefix, an applicable incumbent, and a valid lower bound. Persist the exact prefix, incumbent verification, scope, g/h/U values, assumptions, and reason.

The bound excludes strictly improving completions of that history. It does not prove that the final grouped node is unreachable, that the branch has no bugs, or that no cheaper arrival exists. Another history reaching the same visual group stays independently eligible.

An LLM relevance estimate is not h_lower. A shortest distance through the currently discovered incomplete graph is not necessarily a lower bound on the true application distance. Unknown transitions can create shortcuts. Changing task, checks, action policy, build, context, or incumbent validity invalidates dependent exclusions.

## 7.7 Strict full-route verification

Freeze the candidate action sequence, data, sequence hash, initial-state scope, task/check versions, application build, action policy, and completion interval.

Then establish a new reset instance, check the initial state, replay the exact primitives with fresh targets, check invariants, and evaluate the terminal predicate over the declared stability interval. Persist passed, failed, or inconclusive.

A fallback click, adaptive repair, or changed target semantics creates a new exploratory route. It cannot silently turn the frozen route into a passing replay. A fresh DOM observation may rebind the same unambiguous target semantics; it must not change the route identity.

A single observed pass is useful evidence. It does not establish a statistical reliability rate. A suspected failure becomes a reproduced failure only when the relevant behavior repeats under checked comparable conditions.

## 7.8 Action discipline and restoration

Consumer cost must reflect the declared primitive interaction model. Do not claim a cheap route by jumping to private URLs, setting application state, using hidden APIs, or allowing convenience scrolling that was not represented and charged.

Fixture resets are investigation work, not consumer steps. Browser cookies and local storage do not restore arbitrary server state. A checkpoint preserves committed search/accounting state; after a process loss, the browser and environment may need to be recreated and rechecked.

When exact restoration is unavailable for an external site, report that limit. Do not grant the result the same guarantee as the resettable fixture.

## 7.9 What the result can honestly say

The default claim is: best verified workflow found under the declared conditions and investigation budget.

It is not automatically the globally shortest workflow, a proof of unreachability, comprehensive bug coverage, general accessibility certification, a human-usability estimate, or a measured efficiency improvement. Those require additional assumptions, evaluators, or experiments.

# 8. Costs, efficiency, and fair evaluation

## 8.1 Keep the objectives separate

Workflow cost measures the user's route. Investigation cost measures the work spent finding, interpreting, restoring, and verifying it.

The plans avoid adding clicks, dollars, time, and uncertainty into an arbitrary weighted sum. Instead, minimize the relevant workflow objective under separate limits on requests, tokens, actions, resets, and elapsed time.

The execution brief's example envelope is 180 seconds, 12 route actions, 24 selected work items, 12 model requests, 60,000 total model tokens, 180 browser primitives across all phases, and 12 resets. It also reserves one reset, 12 replay primitives, and 40 seconds for verification. These are configuration proposals to validate, not demonstrated optimal settings.

## 8.2 Charge every phase

Account for reconnaissance, preprocessing, interpretation, failed attempts, retries, restoration, verification, and orchestration where measured. Separate reservations from actual usage and settle each operation once.

Unknown token or money usage remains unknown. It is not zero. Prompt caching, cheaper models, shorter latency, fewer browser actions, and lower total tokens are distinct improvements. A cancelled request may still incur cost.

A graph fading 80% of its visual branches does not establish 80% token savings. The example 24-node graph in C01 was explicitly illustrative. No fabricated counters should become product metrics.

## 8.3 The proposed benchmark

The brief proposes three policies:
- A: competent ordinary model-driven execution.
- B: the same policy with basic memory and checked reuse.
- C: the adaptive scheduler with tested efficiency mechanisms.

Use common runner, observations, actions, goals, verifier, model/settings, hints, initial conditions, and budgets. Do not preload one policy with answers.

The planned pilot was two fixture variants, three policies, and two repetitions: 12 cold runs. A smaller three-run illustration could be selected before scored collection if time required it. Incomplete and failed runs remain in the record. Two repetitions do not establish statistical reliability.

Per-run data should include verified completion, best route cost, time to first verified result, total time, model usage, known charges, browser and restoration work, resets, replay attempts, repeated exact work, stop reason, and unknowns. Cold and warm comparisons must remain distinct. App performance measurements should exclude model thinking and orchestration delay.

## 8.4 What remains unmeasured

The local continuation notes explicitly say no 12-run efficiency study and no prompt evaluation were completed in that recorded session. The later audit also treats measured efficiency as open.

The packet therefore preserves efficiency as a design and evaluation goal. It does not report savings, a speedup, or a better-policy result as established.

# 9. Full feature inventory and cumulative stages

## 9.1 Features requested across the conversations

The complete inventory spans:
- Conversational request intake, clarifying questions, editable assumptions, tasks, and plan approval.
- Cloud provider selection, custom compatible endpoints, optional local inference, and transparent inference location.
- Task scope, allowed actions, goals, invariants, starting conditions, budgets, and supported authentication limits.
- Browser control, bounded scanning, input/slider/drag/keyboard actions where supported, observations, screenshots, traces, and exact histories.
- Persona assignment, attributable individual runs, live status, and supported comparison.
- Live graph discovery, candidate/observed distinctions, route highlighting, deferral, justified exclusion, reactivation, filtering, and evidence selection.
- Dashboard widgets suited to the request, stable layout, persistent conversation, and live browser visibility.
- Clear completed/failed/blocked/cancelled/queued/verifying states and relevant run controls.
- Deep findings, supported impact hypotheses, confidence, screenshots, useful links, and practical recommendations.
- Keep/edit/reject review, bounded implementation-brief export, and retest under comparable checks.
- Competitor task comparison under matched conditions.
- Actual usage, budgets, costs, stop reasons, and measured policy evaluation.
- Persistent history, playback, export, restart/reconnect correctness, and invalidation after changes.
- Mechanically defined additional objectives such as keyboard-constrained investigations.
- Isolated concurrent workers with ownership, recovery, and reconciled budgets.
- Self-hostable source, portable accepted packages, decks, recording materials, and stage-specific demonstrations.

Not every item was demonstrated. The list is the union of requirements and proposed extensions, with the latest conversation determining which experience is central.

## 9.2 The R01-R08 execution sequence

| Stage | Added value | Evidence required before claiming the stage |
| --- | --- | --- |
| R01 Verified investigation | A real task runs, persists evidence, and passes an independent replay | Actual model selection, checked reset, goal verification, inspectable evidence, restart and supplied-URL smoke |
| R02 Adaptive workflows | Investigate alternatives and explain search decisions | Fairness, valid exclusion, reactivation, alias safety, real adaptive run and replay |
| R03 Improvement and retest | Review evidence, export bounded work, test a real fixed build | Persistent review, supported recommendations, unchanged acceptance criteria, before/after evidence |
| R04 Efficiency and prompt evaluation | Avoid exact repeated work and measure the tradeoff | Correct invalidation, complete accounting, fair pilot, retained failures and prompt cases |
| R05 Equivalent competitor comparison | Compare the same conceptual task across two apps | Matched conditions, separate state, independent witnesses, clear non-comparability |
| R06 Model portability | Select and use another semantic endpoint | Real configuration affecting a completed investigation, actual identity/usage/errors |
| R07 Additional objectives and durability | Keyboard constraints, history, selective revalidation | End-to-end policy enforcement, persistence, conservative invalidation, final full replay |
| R08 Isolated runtime workers | Bounded concurrent investigations | Independent server/browser state, leases, crash recovery, no duplicate dispatch, budget conservation |

These stages were an implementation sequence, not permission to omit the requested conversation/persona/advice experience. C12 shows why the engine-first plan needed a product acceptance target in addition to stage mechanics.

## 9.3 A working checkpoint is useful, but the full request remains open

You wanted each completed stage to preserve a useful product while adding capabilities. That is compatible with labeling a stage accepted and the broader project partial.

The recurring failure was treating narrow tests, endpoints, a scripted fixture, or a copied snapshot as proof that the whole feature or product was complete. The user's request for the remaining R01-R08 scope and the later experience clarifications remain distinct from release status.

# 10. Build orchestration and the handoff documents

## 10.1 One computer, several independent workstreams

The plans allocate a coordinator, engine owner, fixture/evaluator owner, UI lead, independent verifier, feature builders, and a release/presentation role. Logical roles need not all run simultaneously.

Shared contracts should be agreed before independent work. The coordinator owns high-conflict integration surfaces. Separate ownership or worktrees reduce collisions. Feature-ready events should trigger UI integration rather than leave completed backend capabilities invisible.

Development parallelism must respond to dependencies and machine limits. More agents do not automatically reduce elapsed time or improve runtime efficiency.

## 10.2 Model routing you requested

C09 requested Composer for UI and routine implementation, Grok 4.7 xhigh for complex work, local Qwen where useful, and stronger models when correctness warranted the cost. You also wanted supported fast modes when a task blocked the rest of the work.

These are historical requested model labels and routing preferences for that build. Availability, exact identities, live-switch support, and inference performance needed startup checks. The packet does not claim those configurations are currently available.

The local Qwen discussion distinguished a replacement MTP-capable checkpoint from attaching an unrelated drafter. Runtime support, model loading, memory use, and actual speculative-decoding benefit remained separate checks. A model file or a compatible endpoint alone does not prove a successful product investigation.

## 10.3 Recurring UI and self-review loop

The requested cycle was:
feature ready -> UI/Figma update -> integrated browser test -> screenshot critique -> fixes -> release checks.

Figma should inform a consistent visual system and matching deck. The selected direction was premium mission control: crisp typography, restrained color, and a striking graph. A design preview is evidence of a design, not proof that its interactions are implemented.

The self-review loop should use the product's own non-code evaluation pipeline where authorized. Its prompt, evidence bundle, model, outputs, usage, and resulting product findings should be attributable. It should not quietly become an OpenRouter coding workflow.

## 10.4 Deadline and recovery

You set 5 p.m. Eastern as the hard submission deadline for November 7. The plans worked backward to protect stabilization, packaging, transfer, recording, voiceover, and upload.

The coordinator was expected to monitor time, dependencies, agent failures, UI integration, machine resources, and readiness. Acceleration should address the actual bottleneck without weakening acceptance criteria. Repeated failed repairs should trigger a bounded escalation or optional-feature deferral rather than an endless loop.

This is a record of the event plan. It is not a newly scheduled task or an instruction to resume the implementation.

# 11. Immutable packages, slides, and the five-minute video

## 11.1 What a release was supposed to mean

After the MVP and each accepted cumulative stage, you wanted a Git-tracked portable copy without nested Git metadata. It should contain the working app, setup/playback instructions, evidence, known limits, slides, and exact recording guidance for another computer.

You allowed the packager to test the newly created package once and then freeze it. Development agents should avoid scanning frozen copies and continue from live source. A later incomplete stage must not damage the strongest validated package.

## 11.2 Common acceptance gate

The execution brief requires integrated live behavior, a usable UI path, meaningful loading/empty/error/result states, stage-relevant checks, independent browser inspection, real evidence, valid links, consistent metrics, restart/reconnect correctness, updated limits, clean portable setup, genuine credential-free playback, matching materials, and package validation.

A status entry saying done is not the same evidence as satisfying that gate. A later stage label in a snapshot is not a frozen release.

## 11.3 The requested recording handoff

You wanted the other computer to produce a five-minute video with your voiceover, using a presentation deck, the running product, and screenshots. The detailed brief settled on four slides and a 300-second narrative:
- 00:00-00:18: problem and product promise.
- 00:18-00:55: request/setup and the declared checks.
- 00:55-01:45: actual investigation or clearly labeled genuine playback.
- 01:45-02:05: architecture and why independent replay matters.
- 02:05-03:20: the strongest accepted stage-specific technical reveal.
- 03:20-04:05: inspect witness, screenshots, checks, trace, and usage.
- 04:05-04:30: actual result and a material limitation.
- 04:30-04:45: practical final interaction.
- 04:45-05:00: exact release and honest next step.

The reveal changes by stage: verified route, actual improvement, before/after retest, measured policy comparison, competitor task pair, provider switch, keyboard/revalidation, or isolated workers.

The materials must reflect the actual accepted result. A shorter route should not be staged if it was not discovered. Recording instructions and a slide plan do not establish that a video or deck was produced. The captured continuation notes explicitly say no demo video was recorded.

# 12. What the later audits actually established

## 12.1 Early live-system audit

C12 reports that the interface built and automated checks passed. At one point 25 checks passed; after new action code, 26 passed. A real model-guided Orbit investigation and a search/typing/slider/drag flow each passed independent replay in six interactions. Express failed and its fixed-build retest passed.

Those are reported observations from that audit, not fresh tests performed while creating this packet. They establish useful mechanics within the tested conditions.

The same audit found serious product gaps: evidence and replay were disconnected from the dashboard; failed Express behavior could still display verified labels; a stale invalidated result could remain the best verified route; provider testing did not prove provider selection; comparisons reused contaminated cart state; and later-stage capabilities were narrower than their descriptions.

## 12.2 Missing conversational interface

When you asked why the agent interface was absent, the audit confirmed a setup wizard and status log rather than a conversation-driven planning session. It distinguished a working browser backend from the experience of describing a request, discussing a plan, watching useful work, and receiving advice.

This was not merely a cosmetic problem. The product lacked the coordinating interaction that made the other features usable together.

## 12.3 Persona and feedback correction

You then emphasized that persona agents and in-depth actionable feedback were central. The response acknowledged that personas had largely been instructions to a shared runner and that advice was basic failure text.

A correct response to that requirement must demonstrate individual relevant investigations and evidence-rich advice, not only show persona names in a roster.

## 12.4 Persisted conversation and two shopper attempts

The latest user message quoted a reported implementation at conversation conv_bc5a0739809344d5 and source revision 796e276. It described two ordinary model-guided runs in separate browsers:
- Price-conscious: run_4c1c0814b7ef4646.
- Search-focused: run_1d576d6e97ae4b9b.

Both reportedly exhausted their budgets after nine page actions and followed the same action sequence. They searched notebook, added the notebook and pen, dragged the mug, and navigated to Orbit Supply and Catalog. The quoted report said the price ceiling remained unchanged and the goal stayed pending.

The record also described a rejected fenced planner response, a revised plan, preserved run links, a report, an accepted finding, and a follow-up answer surviving reload. These are useful persistence and integration observations. Separate browsers alone do not establish independent mutable server state.

## 12.5 The latest audit's concrete findings

The assistant reported verifying the saved conversation, persona runs, report, review state, and follow-up. It also submitted a fresh general-review request, recorded as conv_c310aebd0de940d7.

That broader test exposed:
- Immediate shopper personas without clarification of the website's audience or purpose.
- The same fixed conversation layout rather than a tailored widget configuration.
- No embedded live graph beside the conversation.
- A general review reducing to a heading check named Done.
- A report prompt capped at four findings with very short fields.
- Raw evidence IDs rather than integrated screenshot presentation.
- Screenshot selection limited to the final two per persona, up to four total.
- A misleading diagnosis about the budget preventing the goal check.

The audit's important correction was that the runner evaluates the goal before checking budget exhaustion. The recorded screenshot showed all three items while the price ceiling remained 80, whereas acceptance required 40 or below. That means the report should explain the actual unmet condition and task/check alignment before recommending more budget.

The budget may have ended the run. That does not prove the budget prevented evaluation or caused a product defect.

## 12.6 Why the evidence-selection problem matters

The reported analysis focused on homepage/catalog screenshots that showed an empty cart after earlier item additions. That supported a question about whether adds registered or whether the cart survived navigation, but did not establish the cause.

Relevant evidence should include the item actions, immediate cart state, slider value, navigation transition, check results, and any known instrumentation. A recommendation to change product code is premature if the failure is actually an unmet investigation requirement or an automation-policy gap.

This is a central product lesson: an existing evidence link is not enough. The linked evidence must support the specific claim.

## 12.7 Conflicting status records

The captured ops/TASKS.json marks several stages done. The captured continuation and STATE documents describe the product as partial and list open efficiency, UI-review, keyboard-policy, isolation, live-model, and video work. The later conversation adds further product-experience gaps.

These are different records from a changing working tree. The packet preserves the discrepancy instead of choosing the most optimistic label. No full current acceptance audit was performed for this packet.

The release-label record still selects GU-R01-20261107-r4 as frozen and marks the two R08 labels as snapshots.

# 13. Outstanding requirements and concrete acceptance examples

This section is an editorial consolidation of the latest explicit requirements. It is not a claim that the following work has been implemented or a new replacement implementation brief.

## 13.1 Broad review acceptance

A user asks to review a website generally. The system should determine whether clarification is needed, learn the site's purpose and audience, inspect relevant pages, propose bounded domain-appropriate investigations, and agree on a plan.

The resulting dashboard should reflect those investigations. It should show actual task/persona work and live evidence, then present a supported overview and detailed findings. It should distinguish investigation sufficiency, individual task success, supported product issues, and unexplored areas.

Success is not a single Done heading or a default shopping plan on an unrelated site.

## 13.2 Focused workflow acceptance

A user asks whether a particular shopper can find and add specified items without signing in or ordering. The plan should expose all relevant conditions, including a price-ceiling requirement if it is part of acceptance.

The agent should carry out permitted actions, record checks along the way, and independently verify any claimed route. If the items are present but the ceiling is wrong, explain that exact condition. If two persona attempts match, report that rather than invent behavioral differences.

The dashboard should let the user inspect each action and screenshot and ask why the task failed.

## 13.3 Focused product-analysis acceptance

A user asks about search, onboarding, navigation, or a landing page's clarity. The proposed tasks, personas, checks, and widgets should differ appropriately from the shopping workflow.

Some observations may be mechanically verified; design judgments may remain reasoned hypotheses. The report should identify that distinction and propose a practical validation or retest. The system should not pretend every UX judgment has the same pass/fail evaluator as a cart check.

## 13.4 Operational follow-up acceptance

A follow-up may be answerable from existing evidence, may only change presentation, may revise pending work, or may require a new investigation. The agent should say which case applies.

Requests for deeper inspection or retesting should create connected work with a concrete plan. The conversation, dashboard configuration, graph, evidence, findings, and review decisions should survive reload. Failure and cancellation should remain understandable.

## 13.5 Requirements still needing demonstrated evidence

The conversation record leaves these areas open or insufficiently demonstrated:
- Useful clarification and genuinely general website-review planning.
- Request-specific dashboard configuration.
- A live graph embedded with the conversation and evidence.
- Persona behavior attributable to relevant policies and task evidence.
- Substantial, correct, screenshot-rich recommendations and claim validation.
- Operational follow-up that creates or revises work.
- End-to-end provider selection affecting actual investigations.
- Repeatable equivalent competitor comparisons without state contamination.
- Measured efficiency and prompt evaluation.
- General enforced keyboard constraints and durable revalidation.
- Isolated concurrent application state and worker recovery.
- Complete presentation, recorded video, portable validation, and later frozen release acceptance.

Some pieces may exist in live source. That is different from demonstrated complete user-facing capability.

# 14. Lessons that should survive future handoffs

1. Preserve the user-facing loop as the primary product acceptance target. Engine correctness and product usefulness need separate evidence.
2. Keep exact witnessed histories authoritative. Use graph groups to explain and retrieve evidence, not to invent executable routes.
3. Distinguish observations, hypotheses, unsupported inferences, and verified conclusions.
4. Make advice specific enough to act on and evidence-specific enough to check.
5. Report persona attempts and differences as observed; do not equate labels with human populations.
6. Keep workflow cost separate from investigation cost and charge unsuccessful work.
7. Require real integrated behavior before a feature is called complete.
8. Preserve a validated release while later work remains partial.
9. Treat visual polish as a way to make real work understandable. Graph animation, long reports, and mockups do not replace evidence.
10. Let the most recent explicit clarification correct earlier scope interpretations.

The transcript appendix follows. It preserves the original dialogue rather than rewriting early answers to agree with later conclusions.
