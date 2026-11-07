"""Adaptive search: exact prefixes, fairness, and strict exclusion."""

from __future__ import annotations

import logging

from ghost.engine.browser import TargetError, capture, open_context, perform
from ghost.engine.candidates import build, tried_name
from ghost.engine.observer import observe, page_key
from ghost.engine.restore import orbit_health, orbit_reset, orbit_state
from ghost.engine.schedule import choose, claim_exact, partition, relevance
from ghost.engine.verifier import verify_route
from ghost.hashing import action_sequence_hash
from ghost.ids import new_id
from ghost.providers.openrouter import redact
from ghost.registry import Ctx, evaluate, note_goal

log = logging.getLogger("ghost.adaptive")


def _set(checks, check_id, status, detail):
    return [{**item, "status": status, "detail": detail} if item["id"] == check_id else item for item in checks]


def _policy(task: dict) -> str:
    policy = task["actionPolicy"]
    return f"{policy['id']}@{policy['version']}"


def _count(store, run_id: str, *, browser_actions: int = 0, resets: int = 0, purpose: str) -> None:
    usage_id = new_id("use")
    store.apply(
        run_id,
        records=[("usage", usage_id, {"channel": "reset" if resets else "browser", "purpose": purpose, "browserActions": browser_actions, "resets": resets, "inputTokens": None, "outputTokens": None, "totalTokens": None, "spendingUSD": None})],
        event_type="usage_updated",
        entity_id=usage_id,
        summary="Recorded browser work",
    )


def _exact(prefix: list[dict], candidate: dict) -> str:
    parts = [f"{item.get('kind')}:{tried_name(item['target'])}" for item in prefix]
    parts.append(f"{candidate.get('kind')}:{tried_name(candidate['target'])}")
    return "|".join(parts)


def _signature(actions: list[dict]) -> tuple:
    return tuple((item["target"]["role"], item["target"]["name"]) for item in actions)


def _repeats(live: list[dict], candidate: dict) -> bool:
    """A field is filled once. A control repeats only to apply a fill made on the previous step."""
    name = tried_name(candidate["target"])
    if candidate["kind"] == "fill" and any(
        step.get("kind") == "fill" and step["target"].get("name") == candidate["target"]["name"] for step in live
    ):
        return True
    prior = [
        index
        for index, step in enumerate(live)
        if step.get("kind") == candidate["kind"] and tried_name(step["target"]) == name
    ]
    if not prior:
        return False
    return not (live and live[-1].get("kind") == "fill")


async def run_adaptive(settings, store, browser, run_id: str) -> None:
    try:
        await _run(settings, store, browser, run_id)
    except Exception as exc:
        log.exception("adaptive %s failed", run_id)
        try:
            store.finish(run_id, status="error", stopReason="infrastructure_failure", error=redact(str(exc))[:300] or "The investigation stopped because of an internal error.")
        except Exception:
            log.exception("could not finish %s", run_id)


async def _run(settings, store, browser, run_id: str) -> None:
    from ghost.accounting.ledger import Ledger

    run = store.get_run(run_id)
    task = store.get_task(run["taskId"])
    ledger = Ledger.from_task(task)
    checks = list(run["checks"])
    limitations = [
        "No dollar cap is configured. Request and token bounds are the controls, and unreported charges stay unknown.",
        "This run searches alternatives. A verified route is replayed from a fresh reset before it becomes the result.",
    ]
    store.update_run(run_id, status="running", phase="setup", limitations=limitations, restoration=task.get("restoration"))
    if not ledger.can_start():
        store.finish(run_id, status="stopped", stopReason="budget_exhausted", error="The budget cannot reserve a replay.")
        return
    namespace = f"ns_{run_id}"
    try:
        health = await orbit_health(settings.orbit_origin)
    except Exception:
        store.finish(run_id, status="error", stopReason="infrastructure_failure", error="Orbit Supply is not responding. Start the fixture and try again.")
        return
    build_id = health.get("build") or "unknown"
    reset = await orbit_reset(settings.orbit_origin, settings.control_token, namespace)
    ledger.used_resets += 1
    _count(store, run_id, resets=1, purpose="setup")
    if not reset.get("ok"):
        store.finish(run_id, status="inconclusive", stopReason="initial_conditions_unavailable", error=reset.get("detail") or "The fixture reset did not establish a known start.", buildId=build_id, namespace=namespace)
        return
    baseline = int(reset.get("orders") or 0)
    versions = dict(run["versions"])
    versions["app"] = build_id
    versions["policy"] = "adaptive-v1"
    store.update_run(run_id, buildId=build_id, namespace=namespace, versions=versions)
    context = await open_context(browser, url=task["url"], namespace=namespace, orbit_origin=settings.orbit_origin, namespace_header=task.get("namespaceHeader"))
    page = await context.new_page()
    try:
        await page.goto(task["url"], wait_until="domcontentloaded", timeout=15000)
        ledger.used_browser += 1
        _count(store, run_id, browser_actions=1, purpose="setup")
        observation = await observe(page)
        await capture(page, store, run_id, "Start")
        fixture = await orbit_state(settings.orbit_origin, settings.control_token, namespace)
        initial = [evaluate(ref["id"], ref.get("args") or {}, Ctx(fixture, observation, baseline, namespace, task["allowedOrigins"], build_id)) for ref in task["initial"]]
        if not all(item["ok"] for item in initial):
            checks = _set(checks, "initial", "failed", initial[0]["detail"] if initial else "Initial check failed.")
            store.finish(run_id, status="inconclusive", stopReason="initial_conditions_unavailable", checks=checks, error=checks[0]["detail"], buildId=build_id)
            return
        checks = _set(checks, "initial", "passed", initial[0]["detail"])
        root_id = new_id("pfx")
        store.apply(run_id, records=[("prefix", root_id, {"id": root_id, "parentId": None, "label": "Start", "depth": 0, "lane": 0})], event_type="state_discovered", entity_id=root_id, summary="Observed the start page")
        text = f"{task.get('task', '')} {task.get('objective', '')}"
        frontier: list[dict] = []
        scanned: set[tuple] = set()
        seen_exact: set[str] = set()
        live: list[dict] = []
        live_prefix = root_id
        prefix_of: dict[tuple, str] = {(): root_id}
        lanes = {"Start": 0}
        creation = 0
        picks = 0
        incumbent = None
        verified_hashes: set[str] = set()
        stop_reason, status = "search_envelope_exhausted", "stopped"
        attempts = list(store.get_run(run_id).get("goalAttempts") or [])
        store.update_run(run_id, phase="explore", checks=checks)

        async def at_goal() -> bool:
            nonlocal attempts, checks
            fixture_now = await orbit_state(settings.orbit_origin, settings.control_token, namespace)
            facts = await observe(page)
            results = [evaluate(ref["id"], ref.get("args") or {}, Ctx(fixture_now, facts, baseline, namespace, task["allowedOrigins"], build_id)) for ref in task["goal"]]
            attempts, ok, changed = note_goal(attempts, facts, results)
            detail = results[0]["detail"] if results else "No goal check was declared."
            checks = _set(checks, "goal", "passed" if ok else "failed", detail)
            if changed:
                store.update_run(run_id, checks=checks, goalAttempts=attempts)
                store.add_event(run_id, "check_observed", "goal", {"summary": f"Goal check: {detail}", "outcome": "passed" if ok else "failed", "reason": detail, "url": facts.get("url") or ""})
            return ok

        while True:
            if store.get_run(run_id)["stopRequested"]:
                stop_reason, status = "stopped_by_user", "stopped"
                break
            signature = _signature(live)
            if signature not in scanned:
                if await at_goal():
                    sequence = action_sequence_hash(live, _policy(task))
                    if sequence not in verified_hashes and ledger.can_verify(len(live)):
                        verified_hashes.add(sequence)
                        route_id = new_id("route")
                        chain = [root_id, *[item["prefixId"] for item in live]]
                        store.apply(run_id, records=[("route", route_id, {"id": route_id, "actions": live, "actionSequenceHash": sequence, "interactions": len(live), "prefixIds": chain, "status": "candidate"})], event_type="state_discovered", entity_id=route_id, summary="Froze a witnessed route")
                        store.update_run(run_id, phase="verify")
                        verification = await verify_route(settings=settings, store=store, browser=browser, run_id=run_id, task=task, actions=live, ledger=ledger, baseline_orders=baseline, expected_build=build_id, prefix_ids=chain, route_id=route_id)
                        store.apply(run_id, records=[("verification", verification["id"], {**verification, "buildId": build_id})], event_type="route_verified", entity_id=verification["id"], summary=f"Replay {verification['status']}", extra={"status": verification["status"]})
                        if verification["status"] == "passed" and (incumbent is None or verification["interactions"] < incumbent["interactions"]):
                            incumbent = verification
                            checks = _set(checks, "goal", "passed", verification["detail"])
                    scanned.add(signature)
                else:
                    facts = await observe(page)
                    for candidate in build(
                        facts.get("controls") or [],
                        set(),
                        task.get("forbiddenNames") or [],
                        page_key(facts["url"]),
                        queries=task.get("queries") or [],
                        persona=task.get("persona"),
                    ):
                        name = tried_name(candidate["target"])
                        key = _exact(live, candidate)
                        if len(live) + 1 > task["limits"]["routeActions"] or _repeats(live, candidate):
                            continue
                        if not claim_exact(seen_exact, key):
                            continue
                        creation += 1
                        frontier.append({
                            "id": f"cand_{creation}",
                            "prefix": list(live),
                            "parentPrefixId": live_prefix,
                            "target": candidate["target"],
                            "kind": candidate["kind"],
                            "dataIdentity": candidate.get("dataIdentity") or "",
                            "cost": candidate["cost"],
                            "relevance": relevance(name, text),
                            "g": len(live),
                            "h": 0,
                            "actionCost": 1,
                            "restore": 0,
                            "tokens": 0,
                            "creation": creation,
                            "status": "ready",
                        })
                    scanned.add(signature)
            live_sig = _signature(live)
            for item in frontier:
                if item["status"] == "ready":
                    item["restore"] = 0 if _signature(item["prefix"]) == live_sig else len(item["prefix"]) + 1
            ready, excluded = partition(frontier, None if incumbent is None else incumbent["interactions"])
            for item in excluded:
                if item["status"] != "excluded":
                    item["status"] = "excluded"
                    decision_id = new_id("dec")
                    store.apply(
                        run_id,
                        records=[("decision", decision_id, {"id": decision_id, "kind": "bound", "candidateId": item["id"], "verificationId": incumbent["id"], "g": item["g"], "h": 0, "U": incumbent["interactions"], "reason": "Extensions of this history cannot beat the verified route under a zero lower bound.", "prefix": [step["target"]["name"] for step in item["prefix"]], "action": item["target"]["name"]})],
                        event_type="branch_pruned",
                        entity_id=decision_id,
                        summary=f"Excluded {item['target']['name']} because g+0 is at least the verified cost",
                    )
            for item in frontier:
                if item["status"] == "excluded":
                    still = any(other["id"] == item["id"] for other in excluded)
                    if not still:
                        item["status"] = "ready"
                        store.add_event(run_id, "branch_reactivated", item["id"], {"summary": f"Reactivated {item['target']['name']}"})
            ready = [item for item in frontier if item["status"] == "ready"]
            if not ready:
                if incumbent:
                    acceptable = task.get("acceptableInteractions")
                    status = "passed"
                    stop_reason = "completed_target" if acceptable is None or incumbent["interactions"] <= acceptable else "search_envelope_exhausted"
                break
            affordable = [
                item for item in ready
                if _signature(item["prefix"]) == live_sig or ledger.used_resets + 1 < ledger.resets
            ]
            if picks >= 24 or ledger.elapsed_ms() + 40_000 > ledger.wall_ms or ledger.used_browser + 6 > ledger.browser_actions or not affordable:
                stop_reason = "search_envelope_exhausted" if picks >= 24 else "budget_exhausted"
                status = "passed" if incumbent else "stopped"
                break
            local = [item for item in affordable if _signature(item["prefix"]) == live_sig]
            if local:
                relevant = [item for item in local if item["relevance"] == 0]
                pool = local if (picks + 1) % 5 == 0 else (relevant or local)
            else:
                pool = affordable
            selected, kind = choose(pool, picks)
            picks += 1
            decision_id = new_id("dec")
            store.apply(
                run_id,
                records=[("decision", decision_id, {"id": decision_id, "kind": kind, "candidateId": selected["id"], "relevance": selected["relevance"], "g": selected["g"], "h": 0, "U": None if incumbent is None else incumbent["interactions"], "tuple": [selected["relevance"], selected["g"] + selected["actionCost"], selected["restore"], selected["tokens"], selected["creation"]], "reason": "Oldest eligible work." if kind == "fairness" else "Smallest relevance, cost, restore, and creation tuple."})],
                event_type="candidate_selected",
                entity_id=decision_id,
                summary=f"Selected {selected['target']['name']}",
            )
            store.update_run(run_id, currentAction={"name": selected["target"]["name"], "reason": "Fairness picked the oldest eligible step." if kind == "fairness" else "This step is the best eligible continuation."}, checks=checks)
            if _signature(live) != _signature(selected["prefix"]):
                restored = await _restore(page, settings, task, namespace, selected["prefix"], ledger, store, run_id)
                if not restored:
                    selected["status"] = "invalid"
                    continue
                live = list(selected["prefix"])
                live_prefix = prefix_of.get(_signature(live), root_id)
            try:
                await perform(page, selected["target"], selected["kind"])
            except TargetError as exc:
                selected["status"] = "done"
                seen_exact.add(_exact(selected["prefix"], {"kind": selected["kind"], "target": selected["target"]}))
                store.add_event(run_id, "transition_observed", selected["id"], {"summary": f"{selected['target']['name']} was {exc.reason}", "outcome": "blocked"})
                continue
            if "optimistic=1" in page.url:
                await capture(page, store, run_id, "Optimistic checkout")
                await page.wait_for_timeout(1200)
            ledger.used_browser += 1
            _count(store, run_id, browser_actions=1, purpose="explore")
            selected["status"] = "done"
            seen_exact.add(_exact(selected["prefix"], {"kind": selected["kind"], "target": selected["target"]}))
            shot = await capture(page, store, run_id, selected["target"]["name"])
            first = selected["prefix"][0]["target"]["name"] if selected["prefix"] else selected["target"]["name"]
            if first not in lanes:
                lanes[first] = len(lanes)
            child = new_id("pfx")
            action = {"id": new_id("act"), "kind": selected["kind"], "target": selected["target"], "dataIdentity": selected.get("dataIdentity") or "", "cost": selected["cost"], "screenshotId": shot, "prefixId": child}
            live = [*selected["prefix"], action]
            live_prefix = child
            prefix_of[_signature(live)] = child
            transition_id = new_id("trn")
            store.apply(
                run_id,
                records=[
                    ("prefix", child, {"id": child, "parentId": selected["parentPrefixId"], "label": selected["target"]["name"], "depth": len(live), "lane": lanes[first]}),
                    ("transition", transition_id, {"id": transition_id, "parentPrefixId": selected["parentPrefixId"], "childPrefixId": child, "name": selected["target"]["name"], "role": selected["target"]["role"], "outcome": "executed", "screenshotId": shot}),
                ],
                event_type="transition_observed",
                entity_id=child,
                summary=f"{'Filled' if selected['kind'] == 'fill' else 'Dragged' if selected['kind'] == 'drag' else 'Activated'} {tried_name(selected['target'])}",
            )
            fixture_now = await orbit_state(settings.orbit_origin, settings.control_token, namespace)
            facts = await observe(page)
            invariants = [evaluate(ref["id"], ref.get("args") or {}, Ctx(fixture_now, facts, baseline, namespace, task["allowedOrigins"], build_id)) for ref in task["invariants"]]
            if not all(item["ok"] for item in invariants):
                checks = _set(checks, "invariants", "failed", invariants[0]["detail"])
                stop_reason, status = "search_envelope_exhausted", "failed"
                break
            checks = _set(checks, "invariants", "passed", invariants[0]["detail"] if invariants else "No invariant registered.")
        if incumbent and status != "failed":
            checks = _set(checks, "goal", "passed", incumbent["detail"])
        store.finish(run_id, status=status, stopReason=stop_reason, checks=checks, limitations=limitations, buildId=build_id, error=None)
    finally:
        path = settings.data_dir / "tmp" / f"{run_id}-explore.zip"
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            await context.tracing.stop(path=str(path))
            store.save_trace(run_id, path, "Exploration trace")
        except Exception:
            log.warning("trace not saved for %s", run_id)
        await context.close()


async def _restore(page, settings, task, namespace, actions, ledger, store, run_id) -> bool:
    reset = await orbit_reset(settings.orbit_origin, settings.control_token, namespace)
    ledger.used_resets += 1
    _count(store, run_id, resets=1, purpose="restore")
    if not reset.get("ok"):
        return False
    await page.goto(task["url"], wait_until="domcontentloaded", timeout=15000)
    ledger.used_browser += 1
    _count(store, run_id, browser_actions=1, purpose="restore")
    for action in actions:
        await perform(page, action["target"], action.get("kind") or "activate")
        if "optimistic=1" in page.url:
            await page.wait_for_timeout(1200)
        ledger.used_browser += 1
        _count(store, run_id, browser_actions=1, purpose="restore")
    return True
