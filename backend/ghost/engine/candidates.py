"""Eligible activations from one observation. Place order is never offered."""

from __future__ import annotations

import re

ACTIVATE_COST = {"interactions": 1, "clicks": 1, "keyEvents": 0, "fieldFills": 0, "scrolls": 0}
FILL_COST = {"interactions": 1, "clicks": 0, "keyEvents": 0, "fieldFills": 1, "scrolls": 0}
DRAG_COST = {"interactions": 1, "clicks": 0, "keyEvents": 0, "fieldFills": 0, "scrolls": 0}
QUERY_LIMIT = 3


def tried_name(target: dict) -> str:
    extra = target.get("value") or target.get("onto") or ""
    name = target.get("name") or ""
    return f"{name}={extra}" if extra else name


def offered_queries(queries: list[str] | None, persona: str | None) -> list[str]:
    """Every persona may fill the searches the task supplied, including browse."""
    if persona == "browse" and not queries:
        return []
    values = []
    for raw in queries or []:
        text = str(raw).strip()
        if text and text not in values:
            values.append(text)
        if len(values) == QUERY_LIMIT:
            break
    return values


def _family(name: str) -> str | None:
    folded = name.casefold()
    if "$" not in folded:
        return None
    if "notebook" in folded:
        return "notebook"
    if "mug" in folded:
        return "mug"
    if "pen" in folded:
        return "pen"
    return None


def _price(name: str) -> int | None:
    match = re.search(r"\$(\d+)", name)
    return int(match.group(1)) if match else None


def keep_cheaper(found: list[dict]) -> list[dict]:
    """When priced alternatives are visible, offer the cheaper one in that family."""
    best: dict[str, int] = {}
    for item in found:
        family = _family(item["target"]["name"])
        price = _price(item["target"]["name"])
        if family is None or price is None:
            continue
        best[family] = price if family not in best else min(best[family], price)
    kept = []
    for item in found:
        family = _family(item["target"]["name"])
        price = _price(item["target"]["name"])
        if family is not None and price is not None and price > best[family]:
            continue
        kept.append(item)
    for index, item in enumerate(kept, start=1):
        item["id"] = f"c{index}"
    return kept


def build(
    controls: list[dict],
    tried: set[tuple[str, str, str]],
    forbidden: list[str],
    page: str,
    queries: list[str] | None = None,
    persona: str | None = None,
) -> list[dict]:
    blocked = {name.casefold() for name in forbidden}
    blocked.add("place order")
    found = []
    seen = set()
    drops = [item for item in controls if item.get("role") == "drop" and item.get("name")]
    queries_offered = offered_queries(queries, persona)

    def add(kind: str, role: str, name: str, cost: dict, **extra: str) -> None:
        if len(found) >= 64:
            return
        identity = extra.get("value") or extra.get("onto") or ""
        key = (page, role, tried_name({"name": name, **extra}))
        if key in tried or key in seen:
            return
        seen.add(key)
        target = {"role": role, "name": name, "region": ""}
        target.update(extra)
        found.append({"id": f"c{len(found) + 1}", "kind": kind, "target": target, "dataIdentity": identity, "cost": dict(cost)})

    for control in controls:
        if not control.get("enabled"):
            continue
        role = control.get("role")
        name = (control.get("name") or "").strip()
        if not name or name.casefold() in blocked:
            continue
        if role in {"link", "button"}:
            add("activate", role, name, ACTIVATE_COST)
        elif role in {"searchbox", "textbox"} and queries_offered:
            for query in queries_offered:
                add("fill", role, name, FILL_COST, value=query)
        elif role == "slider":
            add("drag", role, name, DRAG_COST)
        elif role == "draggable":
            for drop in drops[:2]:
                add("drag", role, name, DRAG_COST, onto=drop["name"])
    return keep_cheaper(found)
