from __future__ import annotations

from pathlib import Path

import pytest
from playwright.async_api import async_playwright

from fixtures.orbit.checks import EXPRESS, ORDINARY, SHORTCUT
from ghost.config import Settings
from ghost.engine.adaptive import run_adaptive
from ghost.engine.keyboard import run_keyboard
from ghost.engine.runner import execute_run
from ghost.registry import build_task
from ghost.regressions import Scripted
from ghost.store.projections import snapshot
from ghost.store.sqlite import Store

REPO = Path(__file__).resolve().parents[1]


def _settings(tmp_path: Path, orbit) -> Settings:
    return Settings(
        host="127.0.0.1",
        port=8787,
        data_dir=tmp_path,
        repo_root=REPO,
        model="anthropic/claude-sonnet-4.6",
        fallback_model="anthropic/claude-opus-4.6",
        orbit_origin=orbit["url"],
        control_token=orbit["token"],
        planner_images=False,
    )


async def _run(settings, store, browser, actions, policy_id: str):
    task = store.create_task(build_task({"mode": "orbit"}, orbit_origin=settings.orbit_origin, model=settings.model))
    run = store.create_run(
        task_id=task["id"],
        policy_id=policy_id,
        idempotency_key="idem-" + task["id"],
        discovery=False,
        label="Fixture regression check",
    )
    await execute_run(settings, store, browser, run["id"], lambda ledger: Scripted(actions))
    return snapshot(store, run["id"]), store


@pytest.mark.asyncio
async def test_replay_ordinary_shortcut_and_express(orbit_server, tmp_path):
    settings = _settings(tmp_path, orbit_server)
    store = Store(tmp_path)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            ordinary, store = await _run(settings, store, browser, ORDINARY, "regression.ordinary.v1")
            shortcut, store = await _run(settings, store, browser, SHORTCUT, "regression.shortcut.v1")
            express, store = await _run(settings, store, browser, EXPRESS, "regression.express.v1")
        finally:
            await browser.close()

    assert ordinary["status"] == "passed"
    assert ordinary["projection"]["bestVerified"]["interactions"] == 5
    assert ordinary["projection"]["bestVerified"]["status"] == "passed"
    verified = store.find("verification", ordinary["projection"]["bestVerified"]["verificationId"])
    assert verified["repaired"] is False
    assert ordinary["usage"]["resets"] >= 2
    assert ordinary["usage"]["spendingUSD"] is None

    assert shortcut["status"] == "passed"
    assert shortcut["projection"]["bestVerified"]["interactions"] == 3

    assert express["status"] == "failed"
    assert express["projection"]["bestVerified"] is None
    assert express["projection"]["latestVerification"]["status"] == "failed"
    assert express["projection"]["latestVerification"]["interactions"] == 1
    assert express["discovery"] is False
    assert express["projection"]["evidence"]


@pytest.mark.asyncio
async def test_supplied_page_reaches_a_visible_milestone(orbit_server, tmp_path):
    settings = _settings(tmp_path, orbit_server)
    store = Store(tmp_path)
    task = store.create_task(
        build_task(
            {
                "mode": "supplied",
                "url": orbit_server["url"] + "/milestone",
                "targetName": "Milestone reached",
                "restoration": "fresh_context",
                "objective": "Make the milestone heading visible.",
            },
            orbit_origin=settings.orbit_origin,
            model=settings.model,
        )
    )
    run = store.create_run(
        task_id=task["id"],
        policy_id="ordinary-model-v1",
        idempotency_key="idem-milestone",
        discovery=True,
        label="Investigation",
    )
    actions = [{"kind": "activate", "target": {"role": "button", "name": "Show milestone"}}]
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            await execute_run(settings, store, browser, run["id"], lambda ledger: Scripted(actions))
        finally:
            await browser.close()
    body = snapshot(store, run["id"])
    assert body["status"] == "passed"
    assert body["projection"]["bestVerified"]["interactions"] == 1
    assert body["buildId"] == "supplied"


@pytest.mark.asyncio
async def test_adaptive_verifies_a_real_route(orbit_server, tmp_path):
    settings = _settings(tmp_path, orbit_server)
    store = Store(tmp_path)
    task = store.create_task(build_task({"mode": "orbit"}, orbit_origin=settings.orbit_origin, model=settings.model))
    run = store.create_run(task_id=task["id"], policy_id="adaptive-v1", idempotency_key="idem-adaptive", discovery=True, label="Investigation")
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            await run_adaptive(settings, store, browser, run["id"])
        finally:
            await browser.close()
    body = snapshot(store, run["id"])
    activity = [item["summary"] for item in body["projection"]["activity"] if item["summary"] != "Recorded browser work"]
    assert body["status"] == "passed", (body["stopReason"], body["usage"]["resets"], body["usage"]["browserActions"], body["usage"]["elapsedMs"], activity)
    assert body["projection"]["bestVerified"]["status"] == "passed"
    assert body["projection"]["bestVerified"]["interactions"] <= 6
    decisions = store.records(run["id"], "decision")
    assert decisions


@pytest.mark.asyncio
async def test_keyboard_confirmation_uses_enter(tmp_path):
    settings = _settings(tmp_path, {"url": "http://127.0.0.1:8788", "token": "test-token"})
    store = Store(tmp_path)
    task = store.create_task(build_task({"mode": "orbit"}, orbit_origin=settings.orbit_origin, model=settings.model))
    run = store.create_run(task_id=task["id"], policy_id="keyboard.confirm.v1", idempotency_key="idem-key", discovery=False, label="Keyboard check")
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            await run_keyboard(settings, store, browser, run["id"])
        finally:
            await browser.close()
    body = snapshot(store, run["id"])
    assert body["status"] == "passed"
    assert body["projection"]["bestVerified"]["interactions"] == 1
