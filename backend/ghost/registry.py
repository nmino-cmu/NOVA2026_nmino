"""Trusted evaluators. Models never supply the predicates."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from ghost.engine.personas import PERSONAS, SHOP_TASK

DATASET = "orbit-data-1"
BUDGET_CAPS = {
    "wallMs": 360_000,
    "requests": 20,
    "totalTokens": 60_000,
    "browserActions": 180,
    "resets": 12,
}
LIMITS = {
    "routeActions": 16,
    "candidates": 24,
    "scanChunks": 3,
    "controlsPerChunk": 64,
    "familyInstances": 3,
    "valuesPerField": 3,
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
        "shop.cart.v1": "Shop cart",
        "review.open.v1": "Review coverage",
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
        and page.get("errorVisible") is False
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


def _shop_cart(args: dict, ctx: Ctx) -> tuple[bool, str]:
    page = ctx.page
    cart = page.get("cartText") or ""
    if page.get("errorVisible") is True:
        return False, "A visible error is showing."
    required = list(args.get("required") or [])
    banned = list(args.get("banned") or [])
    if not required:
        return False, "No cart items were declared."
    missing = [item for item in required if item not in cart]
    if missing:
        return False, "Cart is missing " + ", ".join(missing) + "."
    extra = [item for item in banned if item in cart]
    if extra:
        return False, "Cart includes a higher-priced alternative: " + ", ".join(extra) + "."
    try:
        ceiling = float(page.get("priceCeiling"))
    except (TypeError, ValueError):
        return False, "Price ceiling was not reported."
    limit = float(args.get("maxPrice", 40))
    if ceiling > limit:
        return False, f"Price ceiling is {ceiling}, above {limit}."
    if not any(item.get("name") == "Cart ready" for item in page.get("headings") or []):
        return False, "The cart summary is not ready."
    return True, "Cart holds " + ", ".join(required) + f" with the ceiling at {ceiling}."


def _milestone(args: dict, ctx: Ctx) -> tuple[bool, str]:
    page = ctx.page
    if args.get("urlIncludes") and args["urlIncludes"] not in (page.get("url") or ""):
        return False, "URL did not match the milestone."
    if page.get("errorVisible") is True:
        return False, "A visible error is showing."
    targets = list(args.get("targets") or [])
    if not targets:
        return False, "No milestone target was declared."
    for item in args.get("cartIncludes") or []:
        if item not in (page.get("cartText") or ""):
            return False, f"Cart text is missing {item}."
    for target in targets:
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


def _review_open(args: dict, ctx: Ctx) -> tuple[bool, str]:
    path = urlsplit(ctx.page.get("url") or "").path or "/"
    wanted = [str(item).rstrip("/") or "/" for item in (args.get("paths") or [])]
    current = path.rstrip("/") or "/"
    if wanted and current not in wanted:
        return False, f"Opened {path}, which is outside the planned paths."
    return False, "Coverage is counted from the URLs this run opens. A heading named Done does not pass this review."


def note_goal(attempts: list[dict], observation: dict, results: list[dict]) -> tuple[list[dict], bool, bool]:
    """Keep a failed goal result. The same URL and detail are not stored twice."""
    detail = results[0].get("detail") if results else "No goal check was declared."
    ok = bool(results) and all(item.get("ok") for item in results)
    attempt = {
        "ok": ok,
        "detail": str(detail or "")[:300],
        "url": str(observation.get("url") or "")[:300],
        "cartText": str(observation.get("cartText") or "")[:240],
        "priceCeiling": observation.get("priceCeiling"),
    }
    if attempts and attempts[-1].get("detail") == attempt["detail"] and attempts[-1].get("url") == attempt["url"]:
        return attempts, ok, False
    return [*attempts, attempt][-16:], ok, True


_IMPL = {
    "orbit.initial.v1": _orbit_initial,
    "orbit.invariants.v1": _orbit_invariants,
    "orbit.checkout.v1": _orbit_checkout,
    "browser.start.v1": _browser_start,
    "browser.invariant.v1": _browser_invariant,
    "visible_milestone.v1": _milestone,
    "shop.cart.v1": _shop_cart,
    "review.open.v1": _review_open,
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
    {"id": "shop.cart.v1", "kind": "goal", "args": {"required": ["string"], "banned": ["string"], "maxPrice": 40}},
    {"id": "review.open.v1", "kind": "goal", "args": {"paths": ["string"]}},
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
        raise ValueError(f"acceptableInteractions must be from 1 to {LIMITS['routeActions']}, or empty.")
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
    if mode == "shop":
        draft = {
            **draft,
            "mode": "supplied",
            "url": draft.get("url") or (orbit_origin.rstrip("/") + "/shop"),
            "targetName": draft.get("targetName") or "Cart ready",
            "restoration": draft.get("restoration") or "fresh_context",
            "objective": draft.get("objective") or "Add a notebook, a ballpoint pen, and a ceramic mug. Do not sign in or order.",
            "task": draft.get("task") or SHOP_TASK,
            "queries": draft.get("queries") or ["notebook"],
        }
        mode = "supplied"
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
    target = (draft.get("targetName") or draft.get("heading") or "").strip()
    restoration = draft.get("restoration") or "unknown"
    if restoration not in {"fresh_context", "unknown"}:
        raise ValueError("Restoration must be fresh_context or unknown.")
    origin = f"{parts.scheme}://{parts.netloc}"
    task = _base({**draft, "model": model}, "supplied")
    if not task["objective"]:
        task["objective"] = f"Reach a page where {target} is visible."
    if not task["task"]:
        task["task"] = task["objective"]
    persona = (draft.get("persona") or "").strip()
    profile = (draft.get("personaProfile") or "").strip()[:1200]
    if persona and persona not in PERSONAS and not profile:
        raise ValueError("Unknown persona.")
    queries = []
    for raw in draft.get("queries") or []:
        text = str(raw).strip()[:80]
        if text:
            queries.append(text)
    if len(queries) > 3:
        raise ValueError("At most 3 search queries.")
    if not profile and persona in PERSONAS:
        profile = PERSONAS[persona]
    if profile:
        task["task"] = f"{task['task']}\n\nPersona profile:\n{profile}"
    shop = parts.path.rstrip("/") == "/shop" and (parts.hostname or "").lower() in {"127.0.0.1", "localhost"}
    check = str(draft.get("check") or "").strip()
    if check not in {"shop", "heading", "explore"}:
        check = "shop" if shop else "heading"
    if check == "shop" and not shop:
        check = "explore"
    paths = []
    for raw_path in draft.get("paths") or []:
        text = str(raw_path).strip()[:120]
        if text:
            paths.append(text)
        if len(paths) >= 8:
            break
    heading = (draft.get("heading") or target).strip()
    if check == "heading" and not heading:
        raise ValueError("A visible target name is required.")
    if check == "shop" and not target:
        target = "Cart ready"
    goal_args = {"urlIncludes": parts.path or "/", "targets": [{"role": "heading", "name": heading or target}]}
    if draft.get("cartIncludes"):
        goal_args["cartIncludes"] = [str(item) for item in draft["cartIncludes"]][:6]
    if check == "shop":
        goal = {
            "id": "shop.cart.v1",
            "version": 1,
            "args": {
                "required": ["Field notebook $4", "Basic ballpoint pen $2", "Ceramic mug $6"],
                "banned": ["Leather notebook $18", "Gel pen $9", "Travel mug $22"],
                "maxPrice": 40,
            },
        }
        initial_args = {"urlIncludes": parts.path or "/", "absentNames": ["Cart ready"]}
        checks = [
            {"id": "browser.start.v1", "label": "Fresh shop page, cart not ready"},
            {"id": "shop.cart.v1", "label": "Cheaper notebook, ballpoint, and ceramic mug under the price ceiling"},
        ]
    elif check == "explore":
        goal = {"id": "review.open.v1", "version": 1, "args": {"paths": paths}}
        initial_args = {"urlIncludes": parts.path or "/"}
        checks = [
            {"id": "browser.start.v1", "label": "Starting page opened"},
            {"id": "review.open.v1", "label": "Coverage comes from visited URLs"},
        ]
        if not task["objective"]:
            task["objective"] = (task["task"] or "Review the pages relevant to the request.")[:240]
    else:
        goal = {"id": "visible_milestone.v1", "version": 1, "args": goal_args}
        initial_args = {"urlIncludes": parts.path or "/", "absentNames": [heading or target]}
        checks = [
            {"id": "browser.start.v1", "label": "Fresh page without the milestone"},
            {"id": "visible_milestone.v1", "label": f"{heading or target} is visible"},
        ]
    task.update(
        {
            "url": url,
            "allowedOrigins": [origin],
            "restoration": "browser_context" if restoration == "fresh_context" else "unknown",
            "strictReplay": restoration == "fresh_context",
            "actionPolicy": {"id": "browser.activate.v1", "version": 1},
            "initial": [{"id": "browser.start.v1", "version": 1, "args": initial_args}],
            "goal": [goal],
            "invariants": [{"id": "browser.invariant.v1", "version": 1, "args": {}}],
            "reset": {"id": "browser.reset.v1", "version": 1, "args": {"mode": "fresh_context"}},
            "checks": checks,
            "datasetVersion": None,
            "persona": persona or None,
            "personaProfile": profile,
            "personaName": (draft.get("personaName") or "").strip()[:80],
            "personaPriorities": (draft.get("personaPriorities") or "").strip()[:800],
            "queries": queries,
            "check": check,
            "coveragePaths": paths,
            "namespaceHeader": (str(draft.get("namespaceHeader")).strip() if draft.get("namespaceHeader") else None),
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
