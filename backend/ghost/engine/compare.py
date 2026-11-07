"""Run the same mug checkout on Harbor Goods and return the measured cost."""

from __future__ import annotations

import httpx
from playwright.async_api import Browser


async def orbit_shortcut(browser: Browser, origin: str) -> dict:
    context = await browser.new_context(
        viewport={"width": 1440, "height": 900},
        extra_http_headers={"X-Orbit-Namespace": "compare-orbit"},
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
    except Exception:
        await context.close()
        return {"status": "failed", "interactions": None, "detail": "The Orbit shortcut did not reach checkout."}
    await context.close()
    return {
        "status": "passed" if ready else "failed",
        "interactions": len(steps) if ready else None,
        "detail": "Checkout is ready for one Nova Mug." if ready else "The shortcut did not leave one Nova Mug ready.",
        "build": "orbit-buggy-v1",
    }


async def harbor_checkout(browser: Browser, origin: str) -> dict:
    async with httpx.AsyncClient(timeout=5) as client:
        health = await client.get(origin.rstrip("/") + "/health")
    if health.status_code != 200:
        return {"status": "unavailable", "interactions": None, "detail": "Harbor Goods is not running."}
    namespace = "compare"
    context = await browser.new_context(viewport={"width": 1440, "height": 900}, extra_http_headers={"X-Harbor-Namespace": namespace})
    page = await context.new_page()
    steps = [("link", "Catalog"), ("link", "Nova Mug"), ("button", "Add to cart"), ("link", "Continue to checkout")]
    try:
        await page.goto(origin.rstrip("/") + "/", wait_until="domcontentloaded")
        for role, name in steps:
            await page.get_by_role(role, name=name, exact=True).click()
            await page.wait_for_load_state("domcontentloaded")
        ready = await page.locator("[data-ready='true']").count()
    except Exception:
        await context.close()
        return {"status": "failed", "interactions": None, "detail": "Harbor Goods did not complete the checkout route."}
    await context.close()
    return {
        "status": "passed" if ready else "failed",
        "interactions": len(steps) if ready else None,
        "detail": "Checkout is ready for one Nova Mug." if ready else "Harbor checkout was not ready.",
        "build": "harbor-v1",
    }
