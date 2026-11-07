# Ghost Users contract v1

Frozen for the R01 implementation. Wire JSON uses camelCase. Timestamps are ISO-8601 with an offset. Unknown money is `null`, never zero.

## Product boundary

Orbit Supply is a controlled demo application on its own origin. Policies receive observations and candidate ids. They do not receive a browser handle, fixture reset, oracle routes, or the control token.

OpenRouter purposes: `task_draft`, `browser_plan`, `relevance`, `ui_review`, `recommendation`, `prompt_eval`. Responses are data and natural language. Reject code-shaped output.

## Evaluators

| ID | Passes when |
|---|---|
| `orbit.reset.v1` | Control reset cleared the namespace, returned a stable `initialStateHash` and a fresh `resetInstanceId` |
| `orbit.initial.v1` | Logged out, empty cart, no pending work, zero commits, home visible, signed out |
| `orbit.invariants.v1` | Allowed origin, no new order, same namespace, still logged out |
| `orbit.checkout.v1` | Authoritative cart is exactly one `nova-mug`, a commit exists, checkout submit is visible and enabled, no alert, no pending work, orders unchanged |
| `browser.reset.v1` | Fresh browser context |
| `browser.start.v1` | URL contains `urlIncludes` and `absentNames` are not visible |
| `browser.invariant.v1` | Page origin is allowed |
| `visible_milestone.v1` | URL contains `urlIncludes`, each declared target role/name is visible, and any `cartIncludes` text is present. An empty target list fails. |
| `shop.cart.v1` | Cart text contains each required cheaper item, excludes the named higher-priced alternatives, and the price ceiling is at or below `maxPrice`. A heading alone does not pass. |

`orbit.checkout.v1` reads server state through the controller. A success-looking screenshot cannot pass it. Behavioral check args do not hardcode the buggy build. The run records the selected build separately.

Terminal checks wait up to 3 seconds for `[data-ready=true]`, then sample every 100 ms for 1500 ms. Every sample must pass.

## Action hash

`actionSequenceHash` covers ordered primitive kind, role, name, region, supplied-data identity, primitive cost, and action-policy version. It excludes action ids, observation ids, document generations, dispatch ids, reset ids, and timestamps.

## API

`POST /api/task-drafts` with `{"mode":"orbit"}` or `{"mode":"supplied","url","objective","targetName","restoration":"fresh_context"|"unknown"}`.

`POST /api/tasks` stores that draft. The server, not the client, attaches evaluator ids.

`POST /api/runs` body: `{"taskId","taskVersion","policyId","idempotencyKey"}`. Policy ids: `ordinary-model-v1`, `regression.ordinary.v1`, `regression.shortcut.v1`.

`POST /api/fixture-checks` body: `{"kind":"ordinary"|"shortcut","idempotencyKey"}`. These are labeled fixture regression checks, not discovered routes.

`GET /api/runs/{id}` returns the snapshot below. `GET /api/runs/{id}/events?after=` streams SSE. `?format=json` returns an array. `POST /api/runs/{id}/stop` requests a cooperative stop.

`GET /api/evidence/{id}` returns immutable bytes. `GET /api/playback/{id}` is the snapshot plus events and `readOnly: true`. It does not launch a browser or a model call.

`POST /api/routes/{id}/verify` queues another frozen replay.

## Run snapshot

```json
{
  "id": "run_…",
  "status": "queued",
  "stopReason": null,
  "throughSeq": 0,
  "readOnly": false,
  "discovery": true,
  "label": "Investigation",
  "policyId": "ordinary-model-v1",
  "buildId": "orbit-buggy-v1",
  "error": null,
  "task": {"id": "task_…", "version": 1, "objective": "", "task": "", "url": "", "acceptableInteractions": 12},
  "budget": {"wallMs": 180000, "requests": 12, "totalTokens": 60000, "browserActions": 180, "resets": 12, "routeActions": 12, "spendingUSD": null},
  "usage": {"requests": 0, "inputTokens": null, "outputTokens": null, "totalTokens": null, "tokenAccounting": "unknown", "cachedInputTokens": null, "reasoningTokens": null, "browserActions": 0, "resets": 0, "elapsedMs": 0, "spendingUSD": null, "spendingAccounting": "unknown"},
  "projection": {
    "phase": "setup",
    "currentAction": null,
    "bestVerified": null,
    "nodes": [{"id": "p", "label": "Start", "x": 40, "y": 80, "status": "witnessed", "seq": 1}],
    "edges": [{"id": "e", "source": "a", "target": "b", "label": "Catalog"}],
    "witness": [{"index": 1, "kind": "activate", "name": "Catalog", "role": "link", "interactions": 1, "outcome": "executed", "screenshotId": null}],
    "checks": [{"id": "initial", "name": "Initial conditions", "status": "pending", "detail": ""}],
    "activity": [{"seq": 1, "type": "state_discovered", "summary": "Observed home"}],
    "evidence": [{"id": "ev_…", "kind": "screenshot", "mediaType": "image/jpeg", "label": "Start", "capturedAt": ""}],
    "limitations": [],
    "restoration": "fixture_reset"
  },
  "versions": {"schema": 1, "task": 1, "app": "", "environment": "local", "policy": "", "observer": "observer-v1", "graph": 1, "promptSet": "planner-v1"}
}
```

`bestVerified` is `{"routeId","verificationId","status","interactions","actionSequenceHash","resetInstanceId","initialStateHash"}` or null.

Node status is `witnessed`, `current`, `verified`, or `failed`. Positions come from the server. The UI must not invent a second layout or a second usage total.

## Default budget

180000 ms, 12 route actions, 24 candidate selections, 12 model requests, 60000 tokens, 180 browser actions, 12 resets. Verification reserves 1 reset, the route's replay primitives, and 40 seconds. `spendingUSD` stays null unless the provider reports a charge.

## Stop reasons

`completed_target`, `budget_exhausted`, `search_envelope_exhausted`, `initial_conditions_unavailable`, `verification_unavailable`, `stopped_by_user`, `infrastructure_failure`.

`completed_target` requires a passed replay whose interactions are at most `acceptableInteractions`.
