"""One keyboard-only confirmation. Focus evidence is the pressed key, not a click."""

from __future__ import annotations

from ghost.engine.browser import capture, open_context
from ghost.ids import new_id

PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>Desk</title></head>
<body style="font-family:Inter,sans-serif;background:#0B1020;color:#F4F7FB">
<main>
<h1 id="title">Confirm the desk</h1>
<button id="confirm" autofocus>Confirm desk</button>
</main>
<script>
document.getElementById("confirm").addEventListener("keydown", (event) => {
  if (event.key === "Enter") document.getElementById("title").textContent = "Desk confirmed";
});
</script>
</body></html>"""


async def run_keyboard(settings, store, browser, run_id: str) -> None:
    store.update_run(run_id, status="running", phase="explore", buildId="keyboard-local")
    context = await open_context(browser, url="http://127.0.0.1/", namespace=f"ns_{run_id}", orbit_origin=settings.orbit_origin)
    page = await context.new_page()
    try:
        await page.set_content(PAGE)
        await page.locator("#confirm").focus()
        focused = await page.evaluate("() => document.activeElement && document.activeElement.id")
        await page.keyboard.press("Enter")
        title = await page.locator("#title").inner_text()
        shot = await capture(page, store, run_id, "Desk confirmed" if title == "Desk confirmed" else "Keyboard result")
        passed = title == "Desk confirmed" and focused == "confirm"
        verification_id = new_id("ver")
        route_id = new_id("route")
        action = {"id": new_id("act"), "kind": "key", "key": "Enter", "target": {"role": "button", "name": "Confirm desk"}, "cost": {"interactions": 1, "clicks": 0, "keyEvents": 1, "fieldFills": 0, "scrolls": 0}, "screenshotId": shot}
        verification = {
            "id": verification_id,
            "routeId": route_id,
            "status": "passed" if passed else "failed",
            "interactions": 1,
            "detail": "Enter on the focused Confirm desk control." if passed else "The keyboard confirmation did not change the heading.",
            "repaired": False,
            "actions": [action],
            "prefixIds": [],
            "actionSequenceHash": "keyboard-enter-confirm-desk",
            "buildId": "keyboard-local",
        }
        store.apply(
            run_id,
            records=[("route", route_id, {"id": route_id, "actions": [action], "interactions": 1, "status": "candidate"}), ("verification", verification_id, verification)],
            event_type="route_verified",
            entity_id=verification_id,
            summary=f"Keyboard check {verification['status']}",
            extra={"status": verification["status"]},
        )
        store.finish(
            run_id,
            status="passed" if passed else "failed",
            stopReason="completed_target" if passed else "search_envelope_exhausted",
            buildId="keyboard-local",
            checks=[{"id": "keyboard.confirm", "name": "Focused Enter confirms the desk", "status": verification["status"], "detail": verification["detail"]}],
        )
    finally:
        await context.close()
