"""Reject obvious code-shaped model text. This is a guard, not a proof."""

from __future__ import annotations

import re

ALLOWED_PURPOSES = {
    "task_draft",
    "browser_plan",
    "relevance",
    "ui_review",
    "recommendation",
    "prompt_eval",
    "investigation_plan",
    "persona_report",
    "followup",
}

_CODE = re.compile(
    r"```|^\s*#!|diff --git|\b(?:import|export)\s+[A-Za-z_]|\bdef\s+[A-Za-z_]+\s*\(|\bfunction\s+[A-Za-z_]+\s*\(|\bclass\s+[A-Za-z_]+\s*[:{]|<\?php|\bsubprocess\b",
    re.M,
)


def find_violation(value: object) -> str | None:
    if isinstance(value, str):
        if _CODE.search(value):
            return "code_like_text"
        return None
    if isinstance(value, dict):
        for item in value.values():
            found = find_violation(item)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = find_violation(item)
            if found:
                return found
    return None
