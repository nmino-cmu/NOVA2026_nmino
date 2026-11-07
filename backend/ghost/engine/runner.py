"""One forward investigation, then an independent frozen replay."""

from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import urlsplit

from ghost.accounting.ledger import Ledger
from ghost.engine.browser import TargetError, capture, open_context, perform
from ghost.engine.candidates import build, tried_name
from ghost.engine.observer import observe, page_key
from ghost.engine.restore import orbit_health, orbit_reset, orbit_state
from ghost.engine.verifier import verify_route
from ghost.hashing import action_sequence_hash
from ghost.ids import new_id
from ghost.providers.openrouter import redact
from ghost.registry import Ctx, evaluate, note_goal

log = logging.getLogger("ghost.runner")


def _names(controls) -> list[str]:
    names = []
    for control in controls or []:
        name = str(control.get("name") or "").strip()
        if name and name not in names:
            names.append(name[:80])
        if len(names) >= 8:
            break
    return names


def _set(checks: list[dict], check_id: str, status: str, detail: str) -> list[dict]:
    updated = []
    for item in checks:
        if item["id"] == check_id:
            updated.append({**item, "status": status, "detail": detail})
        else:
            updated.append(item)
    return updated


def _ctx(task, fixture, page, baseline: int, namespace: str, build: str | None) -> Ctx:
    return Ctx(fixture, page, baseline, namespace, task["allowedOrigins"], build)


def _left_origin(task: dict, url: str) -> bool:
    allowed = set(task.get("allowedOrigins") or [])
    if not allowed:
        return False
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}" not in allowed


async def _state(settings, task: dict, namespace: str):
    if task["reset"]["id"] != "orbit.reset.v1":
        return None
    return await orbit_state(settings.orbit_origin, settings.control_token, namespace)


def _policy(task: dict) -> str:
    policy = task["actionPolicy"]
    return f"{policy['id']}@{policy['version']}"


async def _save_trace(context, store, settings, run_id: str, label: str) -> None:
    path = settings.data_dir / "tmp" / f"{run_id}-{label}.zip"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        await context.tracing.stop(path=str(path))
        store.save_trace(run_id, path, label)
    except Exception:
        log.warning("trace not saved for %s", run_id)


async def execute_run(settings, store, browser, run_id: str, chooser_factory) -> None:
    try:
        await _execute(settings, store, browser, run_id, chooser_factory)
    except Exception as exc:
        log.exception("run %s failed", run_id)
        try:
            store.finish(
                run_id,
                status="error",
                stopReason="infrastructure_failure",
                error=redact(str(exc))[:300] or "The investigation stopped because of an internal error.",
            )
        except Exception:
            log.exception("could not finish %s", run_id)


async def _execute(settings, store, browser, run_id: str, chooser_factory) -> None:
    run = store.get_run(run_id)
    task = store.get_task(run["taskId"])
    ledger = Ledger.from_task(task)
    chooser = chooser_factory(ledger)
    limitations = [
        "No dollar cap is configured. Request and token bounds are the controls, and unreported charges stay unknown.",
        "Planner decisions use structured controls and visible text. Screenshots are stored as evidence.",
    ]
    if not task.get("strictReplay", True):
        limitations.append("Starting conditions only partially established.")
    if task.get("personaProfile"):
        limitations.append("This persona's profile is a preference among visible controls. Shared task constraints still apply.")
    checks = list(run["checks"])
    store.update_run(run_id, status="running", phase="setup", limitations=limitations, restoration=task.get("restoration"))
    if not ledger.can_start():
        store.finish(run_id, status="stopped", stopReason="budget_exhausted", error="The budget cannot reserve a replay.")
        return

    namespace = f"ns_{run_id}"
    build_id = "supplied"
    baseline = 0
    initial_hash = None
    if task["reset"]["id"] == "orbit.reset.v1":
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
            checks = _set(checks, "initial", "failed", reset.get("detail") or "Reset failed.")
            store.finish(
                run_id,
                status="inconclusive",
                stopReason="initial_conditions_unavailable",
                error=reset.get("detail") or "The fixture reset did not establish a known start.",
                checks=checks,
                buildId=build_id,
                namespace=namespace,
            )
            return
        baseline = int(reset.get("orders") or 0)
        initial_hash = reset.get("initialStateHash")
    versions = dict(run["versions"])
    versions["app"] = build_id
    store.update_run(run_id, buildId=build_id, namespace=namespace, versions=versions, checks=checks)

    context = await open_context(browser, url=task["url"], namespace=namespace, orbit_origin=settings.orbit_origin, namespace_header=task.get("namespaceHeader"))
    page = await context.new_page()
    try:
        try:
            await page.goto(task["url"], wait_until="domcontentloaded", timeout=15000)
        except Exception as exc:
            store.finish(run_id, status="error", stopReason="infrastructure_failure", error=f"Could not open the start page. {redact(str(exc))[:180]}", buildId=build_id)
            return
        try:
            await page.wait_for_function("() => ((document.body && document.body.innerText) || '').trim().length > 40", timeout=8000)
        except Exception:
            pass
        ledger.used_browser += 1
        _count(store, run_id, browser_actions=1, purpose="setup")
        observation = await observe(page)
        shot = await capture(page, store, run_id, "Start")
        fixture = await _state(settings, task, namespace)
        initial = [evaluate(ref["id"], ref.get("args") or {}, _ctx(task, fixture, observation, baseline, namespace, build_id if task["reset"]["id"] == "orbit.reset.v1" else None)) for ref in task["initial"]]
        if not all(item["ok"] for item in initial):
            checks = _set(checks, "initial", "failed", initial[0]["detail"] if initial else "Initial check failed.")
            store.finish(run_id, status="inconclusive", stopReason="initial_conditions_unavailable", checks=checks, error=checks[0]["detail"], buildId=build_id)
            return
        checks = _set(checks, "initial", "passed", initial[0]["detail"])
        root_id = new_id("pfx")
        seq = store.apply(
            run_id,
            records=[("prefix", root_id, {"id": root_id, "parentId": None, "label": "Start", "depth": 0}), ("observation", new_id("obs"), {"url": observation["url"], "screenshotId": shot})],
            event_type="state_discovered",
            entity_id=root_id,
            summary="Observed the start page",
        )
        prefix_ids = [root_id]
        parent = root_id
        actions: list[dict] = []
        history: list[dict] = []
        tried: set[tuple[str, str, str]] = set()
        depth = 0
        goal = False
        attempts = list(store.get_run(run_id).get("goalAttempts") or [])
        stop_reason = "search_envelope_exhausted"
        status = "stopped"
        store.update_run(run_id, phase="explore", checks=checks)
        while True:
            if store.get_run(run_id)["stopRequested"]:
                stop_reason, status = "stopped_by_user", "stopped"
                break
            fixture = await _state(settings, task, namespace)
            observation = await observe(page)
            goal_results = [evaluate(ref["id"], ref.get("args") or {}, _ctx(task, fixture, observation, baseline, namespace, build_id if task["reset"]["id"] == "orbit.reset.v1" else None)) for ref in task["goal"]]
            attempts, goal_ok, changed = note_goal(attempts, observation, goal_results)
            detail = goal_results[0]["detail"] if goal_results else "No goal check was declared."
            checks = _set(checks, "goal", "passed" if goal_ok else "failed", detail)
            if changed:
                store.update_run(run_id, checks=checks, goalAttempts=attempts)
                store.add_event(
                    run_id,
                    "check_observed",
                    "goal",
                    {"summary": f"Goal check: {detail}", "outcome": "passed" if goal_ok else "failed", "reason": detail, "url": observation.get("url") or ""},
                )
            if goal_ok:
                goal = True
                break
            block = ledger.explore_block(len(actions), chooser.needs_model)
            if block:
                stop_reason, status = block, "stopped"
                break
            candidates = build(
                observation.get("controls") or [],
                tried,
                task.get("forbiddenNames") or [],
                page_key(observation["url"]),
                queries=task.get("queries") or [],
                persona=task.get("persona"),
            )
            if not candidates:
                stop_reason, status = "search_envelope_exhausted", "stopped"
                break
            ledger.choices += 1
            choice = await chooser.choose(observation, candidates, history)
            if choice is None:
                if chooser.missing:
                    stop_reason, status = "search_envelope_exhausted", "failed"
                    checks = _set(checks, "goal", "failed", chooser.reason)
                elif chooser.needs_model and not chooser.last_ok:
                    stop_reason, status = "infrastructure_failure", "error"
                else:
                    stop_reason, status = "search_envelope_exhausted", "stopped"
                break
            chosen = next((item for item in candidates if item["id"] == choice), None)
            if chosen is None:
                stop_reason, status = "infrastructure_failure", "error"
                store.update_run(run_id, error="The model returned a candidate that was not available.")
                break
            store.update_run(run_id, currentAction={"name": chosen["target"]["name"], "reason": chooser.reason}, checks=checks)
            store.add_event(run_id, "candidate_selected", chosen["id"], {"summary": f"Selected {chosen['target']['name']}", "reason": chooser.reason})
            before = page_key(page.url)
            mark = (before, chosen["target"]["role"], tried_name(chosen["target"]))
            try:
                await perform(page, chosen["target"], chosen["kind"])
            except TargetError as exc:
                tried.add(mark)
                store.add_event(
                    run_id,
                    "transition_observed",
                    chosen["id"],
                    {"summary": f"{chosen['target']['name']} was {exc.reason}", "outcome": "blocked", "reason": chooser.reason, "url": page.url},
                )
                continue
            if _left_origin(task, page.url):
                tried.add(mark)
                store.add_event(
                    run_id,
                    "transition_observed",
                    chosen["id"],
                    {"summary": f"{chosen['target']['name']} left the allowed origin", "outcome": "blocked", "reason": chooser.reason, "url": page.url},
                )
                try:
                    await page.go_back(wait_until="domcontentloaded", timeout=8000)
                except Exception:
                    pass
                if not _left_origin(task, page.url):
                    continue
            if "optimistic=1" in page.url:
                await capture(page, store, run_id, "Optimistic checkout")
                await page.wait_for_timeout(1200)
            ledger.used_browser += 1
            _count(store, run_id, browser_actions=1, purpose="explore")
            observation = await observe(page)
            shot = await capture(page, store, run_id, chosen["target"]["name"])
            action = {
                "id": new_id("act"),
                "kind": chosen["kind"],
                "target": chosen["target"],
                "dataIdentity": chosen.get("dataIdentity") or "",
                "cost": chosen["cost"],
                "screenshotId": shot,
            }
            actions.append(action)
            tried.add(mark)
            history.append({"name": tried_name(chosen["target"]), "role": chosen["target"]["role"], "outcome": "executed", "url": observation["url"]})
            depth += 1
            child = new_id("pfx")
            transition_id = new_id("trn")
            prefix_ids.append(child)
            store.apply(
                run_id,
                records=[
                    ("prefix", child, {"id": child, "parentId": parent, "label": chosen["target"]["name"], "depth": depth}),
                    (
                        "transition",
                        transition_id,
                        {
                            "id": transition_id,
                            "parentPrefixId": parent,
                            "childPrefixId": child,
                            "name": chosen["target"]["name"],
                            "role": chosen["target"]["role"],
                            "outcome": "executed",
                            "screenshotId": shot,
                            "url": observation.get("url") or "",
                        },
                    ),
                ],
                event_type="transition_observed",
                entity_id=child,
                summary=f"{'Filled' if chosen['kind'] == 'fill' else 'Dragged' if chosen['kind'] == 'drag' else 'Activated'} {tried_name(chosen['target'])}",
                extra={
                    "url": observation.get("url") or "",
                    "reason": (chooser.reason or "")[:500],
                    "outcome": "executed",
                    "screenshotId": shot,
                    "visible": _names(observation.get("controls")),
                    "alerts": [str(item)[:160] for item in (observation.get("alerts") or []) if str(item).strip()][:3],
                },
            )
            parent = child
            fixture = await _state(settings, task, namespace)
            invariants = [evaluate(ref["id"], ref.get("args") or {}, _ctx(task, fixture, observation, baseline, namespace, build_id if task["reset"]["id"] == "orbit.reset.v1" else None)) for ref in task["invariants"]]
            if not all(item["ok"] for item in invariants):
                checks = _set(checks, "invariants", "failed", invariants[0]["detail"])
                stop_reason, status = "search_envelope_exhausted", "failed"
                break
            checks = _set(checks, "invariants", "passed", invariants[0]["detail"] if invariants else "No invariant registered.")

        verification = None
        if actions and (goal or getattr(chooser, "force_verify", False)) and status != "error":
            if not ledger.can_verify(len(actions)):
                stop_reason, status = "verification_unavailable", "inconclusive"
            else:
                store.update_run(run_id, phase="verify", checks=checks)
                route_id = new_id("route")
                sequence = action_sequence_hash(actions, _policy(task))
                store.apply(
                    run_id,
                    records=[("route", route_id, {"id": route_id, "actions": actions, "actionSequenceHash": sequence, "interactions": len(actions), "prefixIds": prefix_ids, "status": "candidate"})],
                    event_type="state_discovered",
                    entity_id=route_id,
                    summary="Froze the witnessed route",
                )
                verification = await verify_route(
                    settings=settings,
                    store=store,
                    browser=browser,
                    run_id=run_id,
                    task=task,
                    actions=actions,
                    ledger=ledger,
                    baseline_orders=baseline,
                    expected_build=build_id if task["reset"]["id"] == "orbit.reset.v1" else None,
                    prefix_ids=prefix_ids,
                    route_id=route_id,
                )
                store.apply(
                    run_id,
                    records=[("verification", verification["id"], {**verification, "buildId": build_id})],
                    event_type="route_verified",
                    entity_id=verification["id"],
                    summary=f"Replay {verification['status']}",
                    extra={"status": verification["status"]},
                )
                checks = _set(checks, "goal", "passed" if verification["status"] == "passed" else verification["status"], verification["detail"])
                if verification["status"] == "passed":
                    interactions = verification["interactions"]
                    acceptable = task.get("acceptableInteractions")
                    status = "passed"
                    stop_reason = "completed_target" if acceptable is not None and interactions <= acceptable else "search_envelope_exhausted"
                elif verification["status"] == "failed":
                    status = "failed"
                    stop_reason = "search_envelope_exhausted"
                else:
                    status = "inconclusive"
                    stop_reason = "initial_conditions_unavailable" if verification.get("initialFailed") else "verification_unavailable"
        elif goal:
            stop_reason, status = "verification_unavailable", "inconclusive"
        store.finish(run_id, status=status, stopReason=stop_reason, checks=checks, limitations=limitations, buildId=build_id, error=None if status != "error" else store.get_run(run_id).get("error"))
    finally:
        await _save_trace(context, store, settings, run_id, "Exploration trace")
        await context.close()


def _count(store, run_id: str, *, browser_actions: int = 0, resets: int = 0, purpose: str) -> None:
    usage_id = new_id("use")
    store.apply(
        run_id,
        records=[
            (
                "usage",
                usage_id,
                {
                    "channel": "reset" if resets else "browser",
                    "purpose": purpose,
                    "browserActions": browser_actions,
                    "resets": resets,
                    "inputTokens": None,
                    "outputTokens": None,
                    "totalTokens": None,
                    "spendingUSD": None,
                },
            )
        ],
        event_type="usage_updated",
        entity_id=usage_id,
        summary="Recorded browser work",
    )
