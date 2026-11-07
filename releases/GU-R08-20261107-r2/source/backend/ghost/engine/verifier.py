"""Frozen replay from a new reset. Nothing in here repairs a miss."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from ghost.engine.browser import activate, capture, open_context
from ghost.engine.observer import observe
from ghost.engine.restore import orbit_reset, orbit_state
from ghost.hashing import action_sequence_hash
from ghost.ids import new_id
from ghost.registry import Ctx, evaluate


def _policy(task: dict) -> str:
    policy = task["actionPolicy"]
    return f"{policy['id']}@{policy['version']}"


async def _fixture(settings, task: dict, namespace: str) -> dict | None:
    if task["reset"]["id"] != "orbit.reset.v1":
        return None
    return await orbit_state(settings.orbit_origin, settings.control_token, namespace)


def _ctx(task, fixture, page, baseline: int, namespace: str, build: str | None) -> Ctx:
    return Ctx(fixture, page, baseline, namespace, task["allowedOrigins"], build)


async def verify_route(
    *,
    settings,
    store,
    browser,
    run_id: str,
    task: dict,
    actions: list[dict],
    ledger,
    baseline_orders: int,
    expected_build: str | None,
    prefix_ids: list[str],
    route_id: str,
) -> dict:
    namespace = f"ns_{run_id}_verify"
    context = await open_context(browser, url=task["url"], namespace=namespace, orbit_origin=settings.orbit_origin)
    page = await context.new_page()
    trace = settings.data_dir / "tmp" / f"{run_id}-verify.zip"
    trace.parent.mkdir(parents=True, exist_ok=True)
    verification_id = new_id("ver")
    try:
        if task["reset"]["id"] == "orbit.reset.v1":
            reset = await orbit_reset(settings.orbit_origin, settings.control_token, namespace)
            ledger.used_resets += 1
            _usage(store, run_id, resets=1, purpose="verify")
            if not reset.get("ok"):
                return _result(verification_id, route_id, actions, prefix_ids, "inconclusive", "Reset failed before replay.", True, reset.get("resetInstanceId"), reset.get("initialStateHash"))
            if expected_build and reset.get("build") != expected_build:
                return _result(verification_id, route_id, actions, prefix_ids, "inconclusive", "The fixture build changed before replay.", True, reset.get("resetInstanceId"), reset.get("initialStateHash"))
            baseline_orders = reset.get("orders", 0)
            initial_hash = reset.get("initialStateHash")
            reset_id = reset.get("resetInstanceId")
        else:
            initial_hash = None
            reset_id = new_id("rst")
        await page.goto(task["url"], wait_until="domcontentloaded", timeout=15000)
        ledger.used_browser += 1
        _usage(store, run_id, browser_actions=1, purpose="verify")
        page_facts = await observe(page)
        fixture = await _fixture(settings, task, namespace)
        initial = [evaluate(ref["id"], ref.get("args") or {}, _ctx(task, fixture, page_facts, baseline_orders, namespace, expected_build)) for ref in task["initial"]]
        if not all(item["ok"] for item in initial):
            return _result(verification_id, route_id, actions, prefix_ids, "inconclusive", "Replay did not establish the starting conditions.", True, reset_id, initial_hash)
        replayed = []
        for action in actions:
            try:
                await activate(page, action["target"])
            except Exception:
                return _result(verification_id, route_id, replayed, prefix_ids, "failed", "A frozen target was missing, ambiguous, or blocked.", False, reset_id, initial_hash, action_sequence_hash(actions, _policy(task)))
            ledger.used_browser += 1
            _usage(store, run_id, browser_actions=1, purpose="verify")
            if "optimistic=1" not in page.url:
                await page.wait_for_timeout(100)
            page_facts = await observe(page)
            shot = await capture(page, store, run_id, action["target"]["name"])
            fixture = await _fixture(settings, task, namespace)
            invariants = [evaluate(ref["id"], ref.get("args") or {}, _ctx(task, fixture, page_facts, baseline_orders, namespace, expected_build)) for ref in task["invariants"]]
            copied = {**action, "replayOfActionId": action.get("id"), "screenshotId": shot}
            replayed.append(copied)
            if not all(item["ok"] for item in invariants):
                return _result(verification_id, route_id, replayed, prefix_ids, "failed", "An invariant failed during replay.", False, reset_id, initial_hash, action_sequence_hash(actions, _policy(task)))
        try:
            await page.wait_for_selector("[data-ready=true]", timeout=3000)
        except Exception:
            pass
        start_shot = await capture(page, store, run_id, "Terminal start")
        samples = []
        started = time.monotonic()
        while True:
            page_facts = await observe(page)
            fixture = await _fixture(settings, task, namespace)
            goal = [evaluate(ref["id"], ref.get("args") or {}, _ctx(task, fixture, page_facts, baseline_orders, namespace, expected_build)) for ref in task["goal"]]
            invariants = [evaluate(ref["id"], ref.get("args") or {}, _ctx(task, fixture, page_facts, baseline_orders, namespace, expected_build)) for ref in task["invariants"]]
            samples.append(
                {
                    "ok": all(item["ok"] for item in goal + invariants),
                    "errorVisible": page_facts.get("errorVisible"),
                    "detail": (goal[0]["detail"] if goal else ""),
                }
            )
            if time.monotonic() - started >= 1.5:
                break
            await asyncio.sleep(0.1)
        end_shot = await capture(page, store, run_id, "Terminal end")
        sample_ref = store.save_evidence(run_id, "samples", json.dumps(samples).encode(), "application/json", "Terminal samples")
        passed = bool(samples) and all(sample["ok"] for sample in samples)
        status = "passed" if passed else "failed"
        detail = samples[-1]["detail"] if samples else "No terminal sample."
        if passed and not task.get("strictReplay", True):
            status = "inconclusive"
            detail = "Starting conditions only partially established."
        result = _result(
            verification_id,
            route_id,
            replayed,
            prefix_ids,
            status,
            detail,
            False,
            reset_id,
            initial_hash,
            action_sequence_hash(actions, _policy(task)),
        )
        result["screenshotIds"] = [item for item in (start_shot, end_shot, sample_ref["id"]) if item]
        return result
    finally:
        try:
            await context.tracing.stop(path=str(trace))
            store.save_trace(run_id, trace, "Replay trace")
        except Exception:
            pass
        await context.close()


def _usage(store, run_id: str, *, browser_actions: int = 0, resets: int = 0, purpose: str) -> None:
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
        summary="Replay work recorded",
    )


def _result(verification_id, route_id, actions, prefix_ids, status, detail, initial_failed, reset_id, initial_hash, sequence_hash=None) -> dict:
    interactions = sum((action.get("cost") or {}).get("interactions", 1) for action in actions)
    return {
        "id": verification_id,
        "routeId": route_id,
        "status": status,
        "interactions": interactions,
        "actionSequenceHash": sequence_hash,
        "resetInstanceId": reset_id,
        "initialStateHash": initial_hash,
        "repaired": False,
        "detail": detail,
        "prefixIds": prefix_ids,
        "actions": actions,
        "initialFailed": initial_failed,
    }
