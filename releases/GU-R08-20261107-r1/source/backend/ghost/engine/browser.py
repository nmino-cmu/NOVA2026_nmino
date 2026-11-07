"""One leased browser. Policies never receive the page handle."""

from __future__ import annotations

from urllib.parse import urlsplit

from playwright.async_api import Browser, BrowserContext, Page


class TargetError(RuntimeError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def context_headers(url: str, namespace: str, orbit_origin: str) -> dict[str, str]:
    parts = urlsplit(url)
    origin = f"{parts.scheme}://{parts.netloc}"
    if origin == orbit_origin.rstrip("/"):
        return {"X-Orbit-Namespace": namespace}
    return {}


async def open_context(browser: Browser, *, url: str, namespace: str, orbit_origin: str) -> BrowserContext:
    context = await browser.new_context(
        viewport={"width": 1440, "height": 900},
        locale="en-US",
        extra_http_headers=context_headers(url, namespace, orbit_origin),
    )
    await context.tracing.start(screenshots=True, snapshots=True, sources=False)
    return context


async def activate(page: Page, target: dict) -> None:
    role = target["role"]
    name = target["name"]
    locator = page.get_by_role(role, name=name, exact=True)
    count = await locator.count()
    if count != 1:
        raise TargetError("ambiguous" if count else "missing")
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
