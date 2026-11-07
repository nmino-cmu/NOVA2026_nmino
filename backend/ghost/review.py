"""Evidence-linked review, a bounded brief, and a same-route retest."""

from __future__ import annotations

import hashlib
import json

from ghost.ids import new_id


def comparability(before_build: str, after_build: str, before_fingerprint: str, after_fingerprint: str) -> str:
    if before_fingerprint != after_fingerprint:
        return "not_comparable"
    if before_build == after_build:
        return "same_build"
    return "comparable_build_change"


def freshness(recorded_build: str | None, current_build: str | None) -> str:
    if not recorded_build or not current_build or recorded_build == current_build:
        return "current"
    return "stale"


def fingerprint(task: dict, action_hash: str) -> str:
    payload = {
        "goal": task.get("goal"),
        "initial": task.get("initial"),
        "invariants": task.get("invariants"),
        "actionPolicy": task.get("actionPolicy"),
        "actionSequenceHash": action_hash,
        "viewport": {"width": 1440, "height": 900},
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def recommendation_for(verification: dict, evidence_ids: list[str], task: dict | None = None) -> dict:
    detail = (verification.get("detail") or "The check failed.").strip()
    names = []
    for action in verification.get("actions") or []:
        name = (action.get("target") or {}).get("name")
        if name:
            names.append(str(name))
    route = " → ".join(names) if names else "the witnessed actions"
    objective = ((task or {}).get("objective") or "").strip()
    claim = detail
    impact = f"The task did not hold after {route}."
    if objective:
        impact = f"“{objective}” did not hold after {route}."
    proposed = f"Change the application so this check can pass: {detail}"
    acceptance = [item.get("id") for item in (task or {}).get("checks") or [] if item.get("id")] or ["the failed check"]
    return {
        "id": new_id("rec"),
        "verificationId": verification["id"],
        "status": "proposed",
        "evidenceIds": evidence_ids[:8],
        "observation": detail,
        "claim": claim,
        "impact": impact,
        "unknowns": [] if verification.get("detail") else ["The failure detail was not recorded."],
        "proposed": proposed,
        "acceptance": acceptance,
        "source": "witnessed-failure",
    }


def brief_markdown(recommendation: dict, build_id: str) -> str:
    evidence = ", ".join(recommendation.get("evidenceIds") or []) or "none"
    return "\n".join(
        [
            "# Implementation brief",
            "",
            "This brief describes a behavior change. It is not permission to edit a repository.",
            "",
            f"Build under review: {build_id}",
            "",
            "## Observed",
            "",
            recommendation["claim"],
            "",
            "## Desired behavior",
            "",
            recommendation["proposed"],
            "",
            "## Acceptance",
            "",
            *[f"- {item}" for item in recommendation["acceptance"]],
            "",
            f"Evidence: {evidence}",
            "",
        ]
    )
