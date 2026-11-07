from __future__ import annotations

import uuid

import httpx
from playwright.sync_api import expect, sync_playwright


def _reset(server, namespace: str) -> dict:
    response = httpx.post(
        server["url"] + "/control/reset",
        headers={"X-Orbit-Control": server["token"]},
        json={"namespace": namespace},
        timeout=5,
    )
    response.raise_for_status()
    return response.json()


def _state(server, namespace: str) -> dict:
    response = httpx.get(
        server["url"] + "/control/state",
        headers={"X-Orbit-Control": server["token"], "X-Orbit-Namespace": namespace},
        timeout=5,
    )
    response.raise_for_status()
    return response.json()


def _page(server, namespace: str):
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1440, "height": 900},
        extra_http_headers={"X-Orbit-Namespace": namespace},
    )
    page = context.new_page()
    page.goto(server["url"] + "/")
    return playwright, browser, page


def test_reset_identity_and_hidden_control(orbit_server):
    namespace = "ns" + uuid.uuid4().hex[:8]
    first = _reset(orbit_server, namespace)
    second = _reset(orbit_server, namespace)
    assert first["ok"] and second["ok"]
    assert first["initialStateHash"] == second["initialStateHash"]
    assert first["resetInstanceId"] != second["resetInstanceId"]
    denied = httpx.get(orbit_server["url"] + "/control/state", headers={"X-Orbit-Namespace": namespace}, timeout=5)
    assert denied.status_code == 404
    stale = httpx.post(
        orbit_server["url"] + "/api/cart/items",
        headers={"X-Orbit-Namespace": namespace, "Content-Type": "application/json"},
        json={"sku": "nova-mug", "qty": 1, "generation": first["generation"]},
        timeout=5,
    )
    assert stale.status_code == 409
    assert _state(orbit_server, namespace)["cart"] == []


def test_ordinary_shortcut_and_express(orbit_server):
    namespace = "ns" + uuid.uuid4().hex[:8]
    _reset(orbit_server, namespace)
    playwright, browser, page = _page(orbit_server, namespace)
    try:
        html = page.content()
        assert "buggy" not in html.lower()
        assert "/control" not in html
        page.get_by_role("link", name="Catalog", exact=True).click()
        page.get_by_role("link", name="Nova Mug", exact=True).click()
        page.get_by_role("button", name="Add to cart", exact=True).click()
        page.get_by_role("link", name="View cart", exact=True).click()
        page.get_by_role("link", name="Continue to checkout", exact=True).click()
        expect(page.get_by_role("button", name="Place order")).to_be_enabled()
        assert _state(orbit_server, namespace)["cart"] == [{"sku": "nova-mug", "qty": 1}]
        assert _state(orbit_server, namespace)["orders"] == 0
    finally:
        browser.close()
        playwright.stop()

    namespace = "ns" + uuid.uuid4().hex[:8]
    _reset(orbit_server, namespace)
    playwright, browser, page = _page(orbit_server, namespace)
    try:
        page.get_by_role("button", name="More", exact=True).click()
        page.get_by_role("button", name="Quick order", exact=True).click()
        page.get_by_role("button", name="Nova Mug checkout", exact=True).click()
        page.wait_for_url("**/checkout")
        expect(page.get_by_role("button", name="Place order")).to_be_enabled()
        assert _state(orbit_server, namespace)["cart"] == [{"sku": "nova-mug", "qty": 1}]
    finally:
        browser.close()
        playwright.stop()

    namespace = "ns" + uuid.uuid4().hex[:8]
    _reset(orbit_server, namespace)
    playwright, browser, page = _page(orbit_server, namespace)
    try:
        page.get_by_role("button", name="Express Nova Mug", exact=True).click()
        page.wait_for_url("**/checkout?optimistic=1")
        expect(page.get_by_text("Checkout ready")).to_be_visible()
        assert _state(orbit_server, namespace)["cart"] == []
        expect(page.get_by_role("alert")).to_be_visible(timeout=4000)
        page.wait_for_timeout(1500)
        state = _state(orbit_server, namespace)
        assert state["cart"] == []
        assert state["commitCount"] == 0
        assert state["orders"] == 0
    finally:
        browser.close()
        playwright.stop()
