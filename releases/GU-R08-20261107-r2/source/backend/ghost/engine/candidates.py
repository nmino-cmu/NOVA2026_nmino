"""Eligible activations from one observation. Place order is never offered."""

from __future__ import annotations

ACTIVATE_COST = {"interactions": 1, "clicks": 1, "keyEvents": 0, "fieldFills": 0, "scrolls": 0}


def build(controls: list[dict], tried: set[tuple[str, str, str]], forbidden: list[str], page: str) -> list[dict]:
    blocked = {name.casefold() for name in forbidden}
    blocked.add("place order")
    found = []
    seen = set()
    for control in controls:
        if not control.get("enabled"):
            continue
        if control.get("role") not in {"link", "button"}:
            continue
        name = (control.get("name") or "").strip()
        if not name or name.casefold() in blocked:
            continue
        key = (page, control["role"], name)
        if key in tried or key in seen:
            continue
        seen.add(key)
        found.append(
            {
                "id": f"c{len(found) + 1}",
                "kind": "activate",
                "target": {"role": control["role"], "name": name, "region": ""},
                "dataIdentity": "",
                "cost": dict(ACTIVATE_COST),
            }
        )
        if len(found) >= 64:
            break
    return found
