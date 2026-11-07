"""One leased browser. Policies never receive the page handle."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from playwright.async_api import Browser, BrowserContext, Page


class TargetError(RuntimeError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def context_headers(url: str, namespace: str, orbit_origin: str, namespace_header: str | None = None) -> dict[str, str]:
    parts = urlsplit(url)
    origin = f"{parts.scheme}://{parts.netloc}"
    if origin == orbit_origin.rstrip("/"):
        return {"X-Orbit-Namespace": namespace}
    if namespace_header:
        return {namespace_header: namespace}
    return {}


async def open_context(browser: Browser, *, url: str, namespace: str, orbit_origin: str, namespace_header: str | None = None) -> BrowserContext:
    context = await browser.new_context(
        viewport={"width": 1440, "height": 900},
        locale="en-US",
        extra_http_headers=context_headers(url, namespace, orbit_origin, namespace_header),
    )
    await context.tracing.start(screenshots=True, snapshots=True, sources=False)
    return context


async def perform(page: Page, target: dict, kind: str = "activate") -> None:
    if kind == "fill":
        await fill(page, target)
        return
    if kind == "drag":
        await drag(page, target)
        return
    await activate(page, target)


async def _locator(page: Page, role: str, name: str):
    locator = page.get_by_role(role, name=name, exact=True)
    if await locator.count() == 0 and role in {"textbox", "searchbox", "slider"}:
        locator = page.get_by_placeholder(name, exact=True)
    if await locator.count() == 0 and len(name) >= 60:
        locator = page.get_by_role(role, name=re.compile("^" + re.escape(name)))
    if await locator.count() > 1:
        locator = locator.first
    return locator


async def fill(page: Page, target: dict) -> None:
    locator = await _locator(page, target["role"], target["name"])
    count = await locator.count()
    if count != 1:
        raise TargetError("ambiguous" if count else "missing")
    await locator.scroll_into_view_if_needed(timeout=3000)
    await locator.fill(target.get("value") or "", timeout=5000)


async def drag(page: Page, target: dict) -> None:
    if target["role"] == "slider":
        locator = page.get_by_role("slider", name=target["name"], exact=True)
        if await locator.count() != 1:
            locator = page.get_by_placeholder(target["name"], exact=True)
        count = await locator.count()
        if count != 1:
            raise TargetError("ambiguous" if count else "missing")
        await locator.scroll_into_view_if_needed(timeout=3000)
        box = await locator.bounding_box()
        if not box:
            raise TargetError("missing")
        y = box["y"] + box["height"] / 2
        await page.mouse.move(box["x"] + box["width"] * 0.85, y)
        await page.mouse.down()
        await page.mouse.move(box["x"] + box["width"] * 0.12, y, steps=12)
        await page.mouse.up()
        return
    source = page.locator("[draggable=true]").filter(has_text=target["name"])
    dest = page.locator("[data-drop]").filter(has_text=target.get("onto") or "")
    if await source.count() != 1 or await dest.count() != 1:
        raise TargetError("missing")
    await source.scroll_into_view_if_needed(timeout=3000)
    await source.drag_to(dest)


async def activate(page: Page, target: dict) -> None:
    role = target["role"]
    name = target["name"]
    locator = await _locator(page, role, name)
    count = await locator.count()
    if count != 1:
        raise TargetError("ambiguous" if count else "missing")
    try:
        await locator.scroll_into_view_if_needed(timeout=3000)
    except Exception:
        pass
    box = await locator.bounding_box()
    viewport = page.viewport_size or {"width": 1440, "height": 900}
    if not box:
        raise TargetError("missing")
    if (
        box["y"] < -2
        or box["x"] < -2
        or box["y"] + box["height"] > viewport["height"] + 2
        or box["x"] + box["width"] > viewport["width"] + 2
    ):
        raise TargetError("outside_viewport")
    before = page.url
    try:
        await locator.click(timeout=5000)
    except Exception:
        await _wait_ready(page)
        if page.url == before:
            raise TargetError("blocked")
        return
    try:
        await page.wait_for_function("() => document.documentElement.dataset.busy !== '1'", timeout=8000)
    except Exception:
        pass
    if page.url != before:
        await _wait_ready(page)


async def capture(page: Page, store, run_id: str, label: str) -> str | None:
    try:
        data = await page.screenshot(type="jpeg", quality=60)
    except Exception:
        return None
    return store.save_evidence(run_id, "screenshot", data, "image/jpeg", label)["id"]


async def _wait_ready(page: Page) -> None:
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=8000)
    except Exception:
        return
