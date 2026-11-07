from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest
from playwright.async_api import async_playwright

from fixtures.orbit.checks import ORDINARY, SHORTCUT
from ghost.config import Settings
from ghost.engine.adaptive import run_adaptive
from ghost.engine.compare import harbor_checkout, orbit_shortcut
from ghost.engine.keyboard import run_keyboard
from ghost.engine.policies import CompatibleChooser
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
async def test_replay_ordinary_and_shortcut(orbit_server, tmp_path):
    settings = _settings(tmp_path, orbit_server)
    store = Store(tmp_path)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            ordinary, store = await _run(settings, store, browser, ORDINARY, "regression.ordinary.v1")
            shortcut, store = await _run(settings, store, browser, SHORTCUT, "regression.shortcut.v1")
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
async def test_shop_brief_searches_browses_and_drags(orbit_server, tmp_path):
    settings = _settings(tmp_path, orbit_server)
    store = Store(tmp_path)
    task = store.create_task(
        build_task(
            {
                "mode": "supplied",
                "url": orbit_server["url"] + "/shop",
                "targetName": "Cart ready",
                "restoration": "fresh_context",
                "objective": "Put the notebook and the mug in the cart at a low price.",
                "task": "Search for the notebook, browse to Mugs, drag the price ceiling down, and drag the mug into the cart.",
                "queries": ["notebook"],
                "persona": "price",
            },
            orbit_origin=settings.orbit_origin,
            model=settings.model,
        )
    )
    run = store.create_run(task_id=task["id"], policy_id="ordinary-model-v1", idempotency_key="idem-shop", discovery=True, label="Shop")
    actions = [
        {"kind": "fill", "target": {"role": "searchbox", "name": "Search the shop", "value": "notebook"}},
        {"kind": "activate", "target": {"role": "button", "name": "Search"}},
        {"kind": "activate", "target": {"role": "button", "name": "Add Field notebook $4"}},
        {"kind": "drag", "target": {"role": "slider", "name": "Price ceiling"}},
        {"kind": "activate", "target": {"role": "link", "name": "Pens"}},
        {"kind": "activate", "target": {"role": "button", "name": "Add Basic ballpoint pen $2"}},
        {"kind": "activate", "target": {"role": "link", "name": "Mugs"}},
        {"kind": "drag", "target": {"role": "draggable", "name": "Ceramic mug $6", "onto": "Cart"}},
    ]
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            await execute_run(settings, store, browser, run["id"], lambda ledger: Scripted(actions))
        finally:
            await browser.close()
    body = snapshot(store, run["id"])
    summaries = [item["summary"] for item in body["projection"]["activity"]]
    assert body["status"] == "passed", summaries
    assert any(item.startswith("Filled Search the shop") for item in summaries)
    assert any(item.startswith("Dragged Price ceiling") for item in summaries)
    assert any(item.startswith("Dragged Ceramic mug") for item in summaries)
    assert body["projection"]["bestVerified"]["interactions"] == 8
    assert "Field notebook $4" in body["projection"]["latestVerification"]["detail"]
    assert "Leather notebook" not in body["projection"]["latestVerification"]["detail"]


@pytest.mark.asyncio
async def test_off_origin_click_is_rejected_and_the_search_continues(orbit_server, tmp_path):
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
        idempotency_key="idem-off-origin",
        discovery=True,
        label="Investigation",
    )
    actions = [
        {"kind": "activate", "target": {"role": "link", "name": "Outside notes"}},
        {"kind": "activate", "target": {"role": "button", "name": "Show milestone"}},
    ]
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            await execute_run(settings, store, browser, run["id"], lambda ledger: Scripted(actions))
        finally:
            await browser.close()
    body = snapshot(store, run["id"])
    summaries = [item["summary"] for item in body["projection"]["activity"]]
    assert body["status"] == "passed"
    assert body["projection"]["bestVerified"]["interactions"] == 1
    assert any("left the allowed origin" in item for item in summaries)


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
    assert body["projection"]["decisions"]
    assert {item["kind"] for item in decisions} <= {"heuristic", "fairness", "bound"}


@pytest.mark.asyncio
async def test_adaptive_shop_fills_drags_and_verifies(orbit_server, tmp_path):
    settings = _settings(tmp_path, orbit_server)
    store = Store(tmp_path)
    task = store.create_task(
        build_task(
            {"mode": "shop", "persona": "browse", "queries": ["notebook"]},
            orbit_origin=settings.orbit_origin,
            model=settings.model,
        )
    )
    run = store.create_run(task_id=task["id"], policy_id="adaptive-v1", idempotency_key="idem-adaptive-shop", discovery=True, label="Adaptive shop")
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            await run_adaptive(settings, store, browser, run["id"])
        finally:
            await browser.close()
    body = snapshot(store, run["id"])
    summaries = [
        (event.get("payload") or {}).get("summary") or event.get("type")
        for event in store.events_after(run["id"], 0)
    ]
    assert body["status"] == "passed", (body["stopReason"], summaries)
    assert any(item.startswith("Filled Search the shop") for item in summaries)
    assert any(item.startswith("Dragged Price ceiling") for item in summaries)
    assert any(item.startswith("Dragged Ceramic mug") for item in summaries)
    assert "Field notebook $4" in body["projection"]["bestVerified"]["detail"]
    assert "Leather notebook" not in body["projection"]["bestVerified"]["detail"]


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


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _serve(module: str, port: int) -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", f"{module}:app", "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=REPO,
        env=env,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(base + "/health", timeout=0.5) as response:
                if response.status == 200:
                    return proc
        except Exception:
            if proc.poll() is not None:
                raise RuntimeError(f"{module} exited during startup")
            time.sleep(0.1)
    proc.terminate()
    raise RuntimeError(f"{module} did not become healthy")


@pytest.mark.asyncio
async def test_compatible_endpoint_completes_a_route(orbit_server, tmp_path):
    port = _free_port()
    proc = _serve("fixtures.echo_model", port)
    settings = _settings(tmp_path, orbit_server)
    store = Store(tmp_path)
    task = store.create_task(build_task({"mode": "orbit"}, orbit_origin=settings.orbit_origin, model=settings.model))
    run = store.create_run(task_id=task["id"], policy_id="compatible-v1", idempotency_key="idem-compatible", discovery=True, label="Compatible endpoint")
    base = f"http://127.0.0.1:{port}/v1"
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            try:
                await execute_run(settings, store, browser, run["id"], lambda ledger: CompatibleChooser(base, store, ledger, run["id"], task, "echo-local"))
            finally:
                await browser.close()
    finally:
        proc.terminate()
        proc.wait(timeout=5)
    body = snapshot(store, run["id"])
    assert body["status"] == "passed", (body["stopReason"], body.get("error"), [item["summary"] for item in body["projection"]["activity"]])
    route = [item["name"] for item in body["projection"]["witness"]]
    assert body["projection"]["bestVerified"]["interactions"] == 5, route
    assert body["usage"]["requests"] == 5, route


@pytest.mark.asyncio
async def test_two_runs_keep_separate_carts(orbit_server, tmp_path):
    settings = _settings(tmp_path, orbit_server)
    store = Store(tmp_path)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            first, second = await asyncio.gather(
                _run(settings, store, browser, SHORTCUT, "regression.shortcut.v1"),
                _run(settings, store, browser, SHORTCUT, "regression.shortcut.v1"),
            )
        finally:
            await browser.close()
    assert first[0]["status"] == "passed"
    assert second[0]["status"] == "passed"
    assert first[0]["id"] != second[0]["id"]
    assert first[0]["projection"]["bestVerified"]["interactions"] == 3
    assert second[0]["projection"]["bestVerified"]["interactions"] == 3


@pytest.mark.asyncio
async def test_comparison_measures_both_storefronts(orbit_server):
    port = _free_port()
    proc = _serve("fixtures.harbor.app", port)
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            try:
                harbor, orbit = await asyncio.gather(
                    harbor_checkout(browser, f"http://127.0.0.1:{port}"),
                    orbit_shortcut(browser, orbit_server["url"], token=orbit_server["token"]),
                )
                harbor_again, orbit_again = await asyncio.gather(
                    harbor_checkout(browser, f"http://127.0.0.1:{port}"),
                    orbit_shortcut(browser, orbit_server["url"], token=orbit_server["token"]),
                )
            finally:
                await browser.close()
    finally:
        proc.terminate()
        proc.wait(timeout=5)
    assert harbor["status"] == "passed"
    assert harbor["interactions"] == 4
    assert orbit["status"] == "passed"
    assert orbit["interactions"] == 3
    assert harbor_again["status"] == "passed"
    assert orbit_again["status"] == "passed", orbit_again
    assert orbit["namespace"] != orbit_again["namespace"]
