"""Trusted evaluators. Models never supply the predicates."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

DATASET = "orbit-data-1"
BUDGET_CAPS = {
    "wallMs": 180_000,
    "requests": 12,
    "totalTokens": 60_000,
    "browserActions": 180,
    "resets": 12,
}
LIMITS = {
    "routeActions": 12,
    "candidates": 24,
    "scanChunks": 3,
    "controlsPerChunk": 64,
    "familyInstances": 3,
    "valuesPerField": 2,
    "retries": 1,
    "settleMs": 3000,
    "stabilityMs": 1500,
}

ORBIT_OBJECTIVE = "Reach checkout with exactly one Nova Mug, and do not place an order."
ORBIT_TASK = (
    "Starting signed out with an empty cart, reach the checkout form with exactly one Nova Mug. "
    "Do not place an order."
)


@dataclass
class Ctx:
    fixture: dict | None
    page: dict
    baseline_orders: int
    namespace: str
    allowed_origins: list[str]
    expected_build: str | None


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def _one_mug(cart: list[dict] | None) -> bool:
    return bool(cart) and len(cart) == 1 and cart[0].get("sku") == "nova-mug" and cart[0].get("qty") == 1


def evaluate(evaluator_id: str, args: dict, ctx: Ctx) -> dict:
    names = {
        "orbit.initial.v1": "Initial conditions",
        "orbit.invariants.v1": "Invariants",
        "orbit.checkout.v1": "Checkout goal",
        "browser.start.v1": "Starting page",
        "browser.invariant.v1": "Origin",
        "visible_milestone.v1": "Visible milestone",
    }
    if evaluator_id not in names:
        return {"id": evaluator_id, "name": evaluator_id, "ok": False, "status": "failed", "detail": "Unknown evaluator."}
    ok, detail = _IMPL[evaluator_id](args, ctx)
    return {
        "id": evaluator_id,
        "name": names[evaluator_id],
        "ok": ok,
        "status": "passed" if ok else "failed",
        "detail": detail,
    }


def _orbit_initial(args: dict, ctx: Ctx) -> tuple[bool, str]:
    state = ctx.fixture or {}
    page = ctx.page
    ok = (
        state.get("loggedIn") is False
        and state.get("cart") == []
        and state.get("pending") == []
        and state.get("commitCount") == 0
        and state.get("orders") == ctx.baseline_orders
        and page.get("homeVisible") is True
        and page.get("signedOutVisible") is True
        and (ctx.expected_build is None or state.get("build") == ctx.expected_build)
    )
    return ok, "Logged out, empty cart, home visible." if ok else "Initial fixture or home conditions were not met."


def _orbit_invariants(args: dict, ctx: Ctx) -> tuple[bool, str]:
    state = ctx.fixture or {}
    origin_ok = _origin(ctx.page.get("url") or "") in ctx.allowed_origins
    ok = (
        origin_ok
        and state.get("orders") == ctx.baseline_orders
        and state.get("namespace") == ctx.namespace
        and state.get("loggedIn") is False
    )
    return ok, "Origin, namespace, and order count held." if ok else "An invariant failed."


def _orbit_checkout(args: dict, ctx: Ctx) -> tuple[bool, str]:
    state = ctx.fixture or {}
    page = ctx.page
    ok = (
        _one_mug(state.get("cart"))
        and state.get("commitCount", 0) >= 1
        and page.get("checkoutFormEnabled") is True
        and page.get("errorVisible") is not True
        and state.get("pending") == []
        and state.get("orders") == ctx.baseline_orders
        and state.get("loggedIn") is False
    )
    if ok:
        return True, "Checkout is enabled with exactly one Nova Mug."
    if not _one_mug(state.get("cart")):
        return False, "Authoritative cart is not exactly one Nova Mug."
    if page.get("errorVisible"):
        return False, "A visible error is showing."
    if not page.get("checkoutFormEnabled"):
        return False, "Checkout form is not enabled."
    return False, "Checkout conditions were not met."


def _browser_start(args: dict, ctx: Ctx) -> tuple[bool, str]:
    page = ctx.page
    if args.get("urlIncludes") and args["urlIncludes"] not in (page.get("url") or ""):
        return False, "Start URL did not match."
    visible = _visible_names(page)
    for name in args.get("absentNames") or []:
        if name in visible:
            return False, f"{name} was already visible."
    return True, "Declared start facts held."


def _browser_invariant(args: dict, ctx: Ctx) -> tuple[bool, str]:
    ok = _origin(ctx.page.get("url") or "") in ctx.allowed_origins
    return ok, "Page stayed on an allowed origin." if ok else "Page left the allowed origin."


def _visible_names(page: dict) -> set[str]:
    names = {item.get("name") for item in page.get("headings") or []}
    names.update(item.get("name") for item in page.get("controls") or [] if item.get("enabled"))
    return {name for name in names if name}


def _milestone(args: dict, ctx: Ctx) -> tuple[bool, str]:
    page = ctx.page
    if args.get("urlIncludes") and args["urlIncludes"] not in (page.get("url") or ""):
        return False, "URL did not match the milestone."
    if page.get("errorVisible"):
        return False, "A visible error is showing."
    for target in args.get("targets") or []:
        if target.get("role") == "heading":
            found = any(item.get("name") == target.get("name") for item in page.get("headings") or [])
        else:
            found = any(
                item.get("role") == target.get("role") and item.get("name") == target.get("name") and item.get("enabled")
                for item in page.get("controls") or []
            )
        if not found:
            return False, f"Missing {target.get('name')}."
    return True, "Visible milestone held."


_IMPL = {
    "orbit.initial.v1": _orbit_initial,
    "orbit.invariants.v1": _orbit_invariants,
    "orbit.checkout.v1": _orbit_checkout,
    "browser.start.v1": _browser_start,
    "browser.invariant.v1": _browser_invariant,
    "visible_milestone.v1": _milestone,
}

EVALUATORS = [
    {"id": "orbit.reset.v1", "kind": "reset", "args": {}},
    {"id": "orbit.initial.v1", "kind": "initial", "args": {}},
    {"id": "orbit.invariants.v1", "kind": "invariant", "args": {}},
    {"id": "orbit.checkout.v1", "kind": "goal", "args": {}},
    {"id": "browser.reset.v1", "kind": "reset", "args": {"mode": "fresh_context"}},
    {"id": "browser.start.v1", "kind": "initial", "args": {"urlIncludes": "string", "absentNames": ["string"]}},
    {"id": "browser.invariant.v1", "kind": "invariant", "args": {}},
    {"id": "visible_milestone.v1", "kind": "goal", "args": {"urlIncludes": "string", "targets": [{"role": "heading", "name": "string"}]}},
]


def _budget(raw: dict | None) -> dict:
    source = raw or {}
    budget = {}
    for key, cap in BUDGET_CAPS.items():
        value = int(source.get(key, cap))
        if value < 1 or value > cap:
            raise ValueError(f"{key} must be from 1 to {cap}.")
        budget[key] = value
    if source.get("spendingUSD") not in (None,):
        raise ValueError("This run has no dollar authorization.")
    budget["spendingUSD"] = None
    return budget


def _acceptable(raw: object) -> int | None:
    if raw is None:
        return None
    value = int(raw)
    if not 1 <= value <= LIMITS["routeActions"]:
        raise ValueError("acceptableInteractions must be from 1 to 12, or empty.")
    return value


def _base(draft: dict, mode: str) -> dict:
    return {
        "mode": mode,
        "objective": (draft.get("objective") or "").strip(),
        "task": (draft.get("task") or "").strip(),
        "budget": _budget(draft.get("budget")),
        "acceptableInteractions": _acceptable(draft.get("acceptableInteractions", LIMITS["routeActions"])),
        "limits": dict(LIMITS),
        "forbiddenNames": ["Place order"],
        "model": draft.get("model") or "anthropic/claude-sonnet-4.6",
    }


def build_task(draft: dict, *, orbit_origin: str, model: str) -> dict:
    mode = draft.get("mode")
    if mode == "orbit":
        task = _base({**draft, "model": model}, "orbit")
        if not task["objective"]:
            task["objective"] = ORBIT_OBJECTIVE
        if not task["task"]:
            task["task"] = ORBIT_TASK
        task.update(
            {
                "url": orbit_origin + "/",
                "allowedOrigins": [orbit_origin],
                "restoration": "fixture_reset",
                "strictReplay": True,
                "actionPolicy": {"id": "orbit.consumer.v1", "version": 1},
                "initial": [{"id": "orbit.initial.v1", "version": 1, "args": {}}],
                "goal": [{"id": "orbit.checkout.v1", "version": 1, "args": {}}],
                "invariants": [{"id": "orbit.invariants.v1", "version": 1, "args": {}}],
                "reset": {"id": "orbit.reset.v1", "version": 1, "args": {}},
                "checks": [
                    {"id": "orbit.initial.v1", "label": "Logged out, empty cart, home"},
                    {"id": "orbit.invariants.v1", "label": "No order placed, same origin"},
                    {"id": "orbit.checkout.v1", "label": "Checkout enabled with exactly one Nova Mug"},
                ],
                "datasetVersion": DATASET,
            }
        )
        return task
    if mode != "supplied":
        raise ValueError("Mode must be orbit or supplied.")
    url = (draft.get("url") or "").strip()
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError("Supplied URL must be http or https.")
    target = (draft.get("targetName") or "").strip()
    if not target:
        raise ValueError("A visible target name is required.")
    restoration = draft.get("restoration") or "unknown"
    if restoration not in {"fresh_context", "unknown"}:
        raise ValueError("Restoration must be fresh_context or unknown.")
    origin = f"{parts.scheme}://{parts.netloc}"
    task = _base({**draft, "model": model}, "supplied")
    if not task["objective"]:
        task["objective"] = f"Reach a page where {target} is visible."
    if not task["task"]:
        task["task"] = task["objective"]
    task.update(
        {
            "url": url,
            "allowedOrigins": [origin],
            "restoration": "browser_context" if restoration == "fresh_context" else "unknown",
            "strictReplay": restoration == "fresh_context",
            "actionPolicy": {"id": "browser.activate.v1", "version": 1},
            "initial": [{"id": "browser.start.v1", "version": 1, "args": {"urlIncludes": parts.path or "/", "absentNames": [target]}}],
            "goal": [{"id": "visible_milestone.v1", "version": 1, "args": {"urlIncludes": parts.path or "/", "targets": [{"role": "heading", "name": target}]}}],
            "invariants": [{"id": "browser.invariant.v1", "version": 1, "args": {}}],
            "reset": {"id": "browser.reset.v1", "version": 1, "args": {"mode": "fresh_context"}},
            "checks": [
                {"id": "browser.start.v1", "label": "Fresh page without the milestone"},
                {"id": "visible_milestone.v1", "label": f"{target} is visible"},
            ],
            "datasetVersion": None,
        }
    )
    if restoration == "unknown":
        task["checks"].append(
            {"id": "restoration", "label": "Starting conditions only partially established"}
        )
    return task


def _self_check() -> None:
    empty = {"loggedIn": False, "cart": [], "pending": [], "commitCount": 0, "orders": 0, "namespace": "n", "build": "orbit-buggy-v1"}
    ready = {"checkoutFormEnabled": True, "errorVisible": False, "url": "http://127.0.0.1:8788/checkout?optimistic=1", "homeVisible": False, "signedOutVisible": True}
    ctx = Ctx(empty, ready, 0, "n", ["http://127.0.0.1:8788"], "orbit-buggy-v1")
    assert evaluate("orbit.checkout.v1", {}, ctx)["ok"] is False
    full = dict(empty, cart=[{"sku": "nova-mug", "qty": 1}], commitCount=1)
    ctx.fixture = full
    ctx.page = dict(ready, url="http://127.0.0.1:8788/checkout", errorVisible=False, checkoutFormEnabled=True)
    assert evaluate("orbit.checkout.v1", {}, ctx)["ok"] is True


if __name__ == "__main__":
    _self_check()
    print("registry ok")
