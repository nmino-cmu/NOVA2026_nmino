"""Canonical hashes for routes and fixture state."""

from __future__ import annotations

import hashlib
import json


def canonical(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(payload: object) -> str:
    return hashlib.sha256(canonical(payload).encode()).hexdigest()


def action_sequence_hash(actions: list[dict], policy_version: str) -> str:
    canon = []
    for action in actions:
        target = action.get("target") or {}
        cost = action["cost"]
        canon.append(
            {
                "kind": action["kind"],
                "role": target.get("role") or "",
                "name": target.get("name") or "",
                "region": target.get("region") or "",
                "dataIdentity": action.get("dataIdentity") or "",
                "interactions": cost["interactions"],
                "clicks": cost["clicks"],
                "keyEvents": cost["keyEvents"],
                "fieldFills": cost["fieldFills"],
                "scrolls": cost["scrolls"],
            }
        )
    return sha256_text({"policy": policy_version, "actions": canon})
