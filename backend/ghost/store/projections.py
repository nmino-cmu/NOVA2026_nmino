"""Run snapshots are derived from committed records."""

from __future__ import annotations

import time

from ghost.store.sqlite import Store


def _usage(rows: list[dict], elapsed_ms: int) -> dict:
    model = [row for row in rows if row.get("channel") == "model"]
    def total(field: str):
        if not model:
            return 0, "reported"
        if any(row.get(field) is None for row in model):
            return None, "unknown"
        return sum(row[field] for row in model), "reported"

    input_tokens, _ = total("inputTokens")
    output_tokens, _ = total("outputTokens")
    total_tokens, token_accounting = total("totalTokens")
    if model and any(row.get("spendingUSD") is None for row in model):
        spending, spending_accounting = None, "unknown"
    elif model:
        spending, spending_accounting = sum(row["spendingUSD"] for row in model), "reported"
    else:
        spending, spending_accounting = None, "unknown"
    cached_values = [row.get("cachedInputTokens") for row in model]
    reasoning_values = [row.get("reasoningTokens") for row in model]
    return {
        "requests": len(model),
        "inputTokens": input_tokens,
        "outputTokens": output_tokens,
        "totalTokens": total_tokens,
        "tokenAccounting": token_accounting,
        "cachedInputTokens": None if any(value is None for value in cached_values) else sum(cached_values),
        "reasoningTokens": None if any(value is None for value in reasoning_values) else sum(reasoning_values),
        "browserActions": sum(int(row.get("browserActions") or 0) for row in rows),
        "resets": sum(int(row.get("resets") or 0) for row in rows),
        "elapsedMs": elapsed_ms,
        "spendingUSD": spending,
        "spendingAccounting": spending_accounting,
    }


def _current_pass(item: dict) -> bool:
    return item.get("status") == "passed" and item.get("repaired") is False and not item.get("stale")


def _route_view(item: dict) -> dict:
    actions = []
    for action in item.get("actions") or []:
        target = action.get("target") or {}
        actions.append(
            {
                "kind": action.get("kind"),
                "name": target.get("name"),
                "interactions": (action.get("cost") or {}).get("interactions", 1),
            }
        )
    return {
        "verificationId": item.get("id"),
        "routeId": item.get("routeId"),
        "status": item.get("status"),
        "interactions": item.get("interactions"),
        "stale": bool(item.get("stale")),
        "detail": item.get("detail"),
        "buildId": item.get("buildId"),
        "actions": actions,
    }


def snapshot(store: Store, run_id: str) -> dict:
    run = store.get_run(run_id)
    task = store.get_task(run["taskId"])
    prefixes = store.records(run_id, "prefix")
    transitions = store.records(run_id, "transition")
    verifications = store.records(run_id, "verification")
    current_ids = set()
    stale_ids = set()
    failed_ids = set()
    for item in verifications:
        ids = set(item.get("prefixIds") or [])
        if _current_pass(item):
            current_ids.update(ids)
        elif item.get("status") == "passed" and item.get("stale"):
            stale_ids.update(ids)
        elif item.get("status") == "failed":
            failed_ids.update(ids)
            if item.get("stale"):
                stale_ids.update(ids)
    by_child = {item.get("childPrefixId"): item for item in transitions}
    observations = store.records(run_id, "observation")
    nodes = []
    for item in prefixes:
        status = "witnessed"
        if item["id"] in current_ids:
            status = "verified"
        elif item["id"] in failed_ids:
            status = "failed"
        incoming = by_child.get(item["id"]) or {}
        nodes.append(
            {
                "id": item["id"],
                "label": item.get("label") or "Step",
                "x": 48 + int(item.get("depth") or 0) * 196,
                "y": 48 + int(item.get("lane") or 0) * 92,
                "status": status,
                "freshness": "stale" if item["id"] in stale_ids and item["id"] not in current_ids else "current",
                "seq": item.get("seq") or 0,
                "url": incoming.get("url") or "",
                "screenshotId": incoming.get("screenshotId"),
                "outcome": incoming.get("outcome") or "",
                "action": incoming.get("name") or "",
                "reason": incoming.get("reason") or "",
            }
        )
    if nodes and observations:
        if not nodes[0].get("url"):
            nodes[0]["url"] = observations[0].get("url") or ""
        if not nodes[0].get("screenshotId"):
            nodes[0]["screenshotId"] = observations[0].get("screenshotId")
            nodes[0]["outcome"] = nodes[0].get("outcome") or "start"
    attempts = list(run.get("goalAttempts") or [])
    for node in nodes:
        hits = [item for item in attempts if item.get("url") and item.get("url") == node.get("url")]
        if hits:
            node["check"] = hits[-1].get("detail") or ""
            node["checkOk"] = bool(hits[-1].get("ok"))
    if run["status"] in {"queued", "running"} and nodes:
        if nodes[-1]["status"] == "witnessed":
            nodes[-1]["status"] = "current"
    edges = [
        {
            "id": item["id"],
            "source": item["parentPrefixId"],
            "target": item.get("childPrefixId"),
            "label": item.get("name") or "",
        }
        for item in transitions
        if item.get("outcome") == "executed" and item.get("childPrefixId")
    ]
    passed = [item for item in verifications if _current_pass(item)]
    best = min(passed, key=lambda item: item.get("interactions") or 0) if passed else None
    witness_source = best
    witness = []
    if witness_source:
        for index, action in enumerate(witness_source.get("actions") or [], start=1):
            target = action.get("target") or {}
            witness.append(
                {
                    "index": index,
                    "kind": action.get("kind"),
                    "name": target.get("name"),
                    "role": target.get("role"),
                    "interactions": (action.get("cost") or {}).get("interactions", 1),
                    "outcome": "executed",
                    "screenshotId": action.get("screenshotId"),
                }
            )
    if run.get("elapsedMs") is not None:
        elapsed = int(run["elapsedMs"])
    else:
        elapsed = int((time.time() - float(run.get("startedEpoch") or time.time())) * 1000)
    events = store.events_after(run_id, 0)
    budget = dict(task["budget"])
    budget["routeActions"] = task["limits"]["routeActions"]
    return {
        "id": run["id"],
        "status": run["status"],
        "stopReason": run.get("stopReason"),
        "throughSeq": run["throughSeq"],
        "readOnly": False,
        "discovery": bool(run.get("discovery")),
        "label": run.get("label") or "Investigation",
        "policyId": run.get("policyId"),
        "buildId": run.get("buildId"),
        "error": run.get("error"),
        "task": {
            "id": task["id"],
            "version": task["version"],
            "objective": task["objective"],
            "task": task["task"],
            "url": task["url"],
            "acceptableInteractions": task.get("acceptableInteractions"),
        },
        "budget": budget,
        "usage": _usage(store.records(run_id, "usage"), elapsed),
        "projection": {
            "phase": run.get("phase") or "setup",
            "currentAction": run.get("currentAction"),
            "bestVerified": None
            if not best
            else {
                "routeId": best["routeId"],
                "verificationId": best["id"],
                "status": best["status"],
                "interactions": best["interactions"],
                "actionSequenceHash": best["actionSequenceHash"],
                "resetInstanceId": best.get("resetInstanceId"),
                "initialStateHash": best.get("initialStateHash"),
                "detail": best.get("detail"),
            },
            "latestVerification": None
            if not verifications
            else {
                "verificationId": verifications[-1]["id"],
                "status": verifications[-1]["status"],
                "interactions": verifications[-1].get("interactions"),
                "detail": verifications[-1].get("detail"),
                "stale": bool(verifications[-1].get("stale")),
            },
            "nodes": nodes,
            "edges": edges,
            "witness": witness,
            "checks": run.get("checks") or [],
            "goalAttempts": run.get("goalAttempts") or [],
            "coveragePaths": task.get("coveragePaths") or [],
            "decisions": [
                {
                    "id": item.get("id"),
                    "kind": item.get("kind") or "heuristic",
                    "reason": item.get("reason") or "",
                    "g": item.get("g"),
                    "h": item.get("h"),
                    "U": item.get("U"),
                }
                for item in store.records(run_id, "decision")
            ][-24:],
            "activity": [
                {
                    "seq": event["seq"],
                    "type": event["type"],
                    "summary": event["payload"].get("summary") or event["type"],
                    "reason": event["payload"].get("reason") or "",
                    "outcome": event["payload"].get("outcome") or "",
                    "url": event["payload"].get("url") or "",
                }
                for event in events
            ][-200:],
            "evidence": store.evidence_list(run_id),
            "limitations": run.get("limitations") or [],
            "restoration": run.get("restoration") or task.get("restoration"),
            "identity": {
                "goal": task.get("objective"),
                "url": task.get("url"),
                "taskId": task["id"],
                "taskVersion": task["version"],
                "buildId": run.get("buildId"),
                "model": (run.get("versions") or {}).get("model") or task.get("model"),
                "promptSet": (run.get("versions") or {}).get("promptSet"),
                "policyId": run.get("policyId"),
                "persona": task.get("persona"),
                "queries": task.get("queries") or [],
            },
            "routes": {
                "best": None if not best else _route_view(best),
                "failed": [_route_view(item) for item in verifications if item.get("status") == "failed"],
                "historical": [_route_view(item) for item in verifications if item.get("status") == "passed" and item.get("stale")],
                "candidates": [
                    {"routeId": item.get("id"), "status": item.get("status"), "interactions": item.get("interactions")}
                    for item in store.records(run_id, "route")
                    if not best or item.get("id") != best.get("routeId")
                ],
            },
            "attempt": []
            if not verifications
            else [
                {
                    "index": index,
                    "kind": action.get("kind"),
                    "name": (action.get("target") or {}).get("name"),
                    "interactions": (action.get("cost") or {}).get("interactions", 1),
                    "status": verifications[-1].get("status"),
                    "stale": bool(verifications[-1].get("stale")),
                }
                for index, action in enumerate(verifications[-1].get("actions") or [], start=1)
            ],
        },
        "versions": run.get("versions") or {},
    }


def playback(store: Store, run_id: str) -> dict:
    body = snapshot(store, run_id)
    body["readOnly"] = True
    body["events"] = store.events_after(run_id, 0)
    return body
