"""Evidence-linked review, a bounded brief, and a same-route retest."""

from __future__ import annotations

import hashlib
import json

from ghost.ids import new_id


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


def recommendation_for(verification: dict, evidence_ids: list[str]) -> dict:
    return {
        "id": new_id("rec"),
        "verificationId": verification["id"],
        "status": "proposed",
        "evidenceIds": evidence_ids[:8],
        "claim": "Express opened checkout before the cart commit was authoritative.",
        "impact": "A shopper can see a ready checkout while the cart is still empty.",
        "proposed": "Wait until the cart commit succeeds, then open checkout. Keep the same Express control and the same checkout check.",
        "acceptance": ["orbit.initial.v1", "orbit.invariants.v1", "orbit.checkout.v1"],
        "source": "witnessed-failure",
    }


def brief_markdown(recommendation: dict, build_id: str) -> str:
    evidence = ", ".join(recommendation.get("evidenceIds") or []) or "none"
    return "\n".join(
        [
            "# Orbit Supply brief",
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
