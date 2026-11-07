"""Fresh measurements of the same mug checkout on two storefronts."""

from __future__ import annotations

import uuid

import httpx
from playwright.async_api import Browser

from ghost.engine.restore import orbit_reset, orbit_state


def _namespace() -> str:
    return "cmp_" + uuid.uuid4().hex[:10]


async def orbit_shortcut(browser: Browser, origin: str, *, token: str) -> dict:
    namespace = _namespace()
    reset = await orbit_reset(origin, token, namespace)
    if not reset.get("ok"):
        return {
            "status": "unavailable",
            "interactions": None,
            "detail": reset.get("detail") or "Could not establish a fresh Orbit cart.",
            "namespace": namespace,
            "build": None,
        }
    context = await browser.new_context(
        viewport={"width": 1440, "height": 900},
        extra_http_headers={"X-Orbit-Namespace": namespace},
    )
    page = await context.new_page()
    steps = [("button", "More"), ("button", "Quick order"), ("button", "Nova Mug checkout")]
    try:
        await page.goto(origin.rstrip("/") + "/", wait_until="domcontentloaded")
        for role, name in steps:
            await page.get_by_role(role, name=name, exact=True).click()
            await page.wait_for_load_state("domcontentloaded")
        button = page.get_by_role("button", name="Place order", exact=True)
        await button.wait_for(state="visible", timeout=5000)
        ready = await button.is_enabled()
        state = await orbit_state(origin, token, namespace)
    except Exception:
        await context.close()
        return {"status": "failed", "interactions": None, "detail": "The Orbit shortcut did not reach checkout.", "namespace": namespace, "build": "orbit-buggy-v1"}
    await context.close()
    cart = state.get("cart") or []
    one = len(cart) == 1 and cart[0].get("sku") == "nova-mug" and cart[0].get("qty") == 1
    passed = bool(ready and one and state.get("loggedIn") is False and state.get("orders") == reset.get("orders"))
    if passed:
        detail = "Checkout is ready for one Nova Mug."
    elif not one:
        detail = "Orbit cart was not exactly one Nova Mug after a fresh reset."
    else:
        detail = "The shortcut did not leave one Nova Mug ready."
    return {
        "status": "passed" if passed else "failed",
        "interactions": len(steps) if passed else None,
        "detail": detail,
        "build": state.get("build") or "orbit-buggy-v1",
        "namespace": namespace,
    }


async def harbor_checkout(browser: Browser, origin: str) -> dict:
    namespace = _namespace()
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            health = await client.get(origin.rstrip("/") + "/health")
            if health.status_code != 200:
                return {"status": "unavailable", "interactions": None, "detail": "Harbor Goods is not running.", "namespace": namespace, "build": None}
            reset = await client.post(origin.rstrip("/") + "/control/reset", json={"namespace": namespace})
            if reset.status_code != 200:
                return {"status": "unavailable", "interactions": None, "detail": "Harbor Goods did not reset a fresh cart.", "namespace": namespace, "build": "harbor-v1"}
    except httpx.HTTPError:
        return {"status": "unavailable", "interactions": None, "detail": "Harbor Goods is not running.", "namespace": namespace, "build": None}
    context = await browser.new_context(viewport={"width": 1440, "height": 900}, extra_http_headers={"X-Harbor-Namespace": namespace})
    page = await context.new_page()
    steps = [("link", "Catalog"), ("link", "Nova Mug"), ("button", "Add to cart"), ("link", "Continue to checkout")]
    try:
        await page.goto(origin.rstrip("/") + "/", wait_until="domcontentloaded")
        for role, name in steps:
            await page.get_by_role(role, name=name, exact=True).click()
            await page.wait_for_load_state("domcontentloaded")
        ready = await page.locator("[data-ready='true']").count()
        cart = await page.locator("#bag").inner_text()
    except Exception:
        await context.close()
        return {"status": "failed", "interactions": None, "detail": "Harbor Goods did not complete the checkout route.", "namespace": namespace, "build": "harbor-v1"}
    await context.close()
    one = "Nova Mug × 1" in cart
    passed = bool(ready and one)
    return {
        "status": "passed" if passed else "failed",
        "interactions": len(steps) if passed else None,
        "detail": "Checkout is ready for one Nova Mug." if passed else "Harbor checkout was not one Nova Mug.",
        "build": "harbor-v1",
        "namespace": namespace,
    }
