"""Ordinary model policy. It may only return a candidate id from the supplied list."""

from __future__ import annotations

import json

from ghost.ids import new_id
from ghost.providers.compatible import choose as compatible_choose
from ghost.providers.openrouter import complete_json


def prompt_payload(task: dict, observation: dict, candidates: list[dict], history: list[dict]) -> dict:
    return {
        "task": task["task"],
        "objective": task["objective"],
        "url": observation.get("url"),
        "visibleText": (observation.get("text") or "")[:1800],
        "recentActions": history[-8:],
        "candidates": [
            {
                "id": item["id"],
                "kind": item["kind"],
                "role": item["target"]["role"],
                "name": item["target"]["name"],
            }
            for item in candidates
        ],
        "constraints": [
            "Choose one candidate_id from candidates.",
            "Do not write code.",
            "Do not place an order.",
        ],
    }


class ModelChooser:
    needs_model = True
    force_verify = False

    def __init__(self, settings, store, ledger, run_id: str, task: dict):
        self.settings = settings
        self.store = store
        self.ledger = ledger
        self.run_id = run_id
        self.task = task
        self.reason = ""
        self.missing = None
        self.last_ok = True
        self._prompt = (settings.repo_root / "prompts/planner/v1.txt").read_text(encoding="utf-8")

    async def choose(self, observation: dict, candidates: list[dict], history: list[dict]) -> str | None:
        self.last_ok = False
        if self.ledger.unknown_tokens or self.ledger.used_requests >= self.ledger.requests:
            self.reason = "The model budget is exhausted."
            return None
        completion = await complete_json(
            self.settings,
            purpose="browser_plan",
            system=self._prompt,
            user=json.dumps(prompt_payload(self.task, observation, candidates, history)),
            required=["candidate_id", "rationale"],
            schema_name="candidate_choice",
        )
        for attempt in completion.attempts:
            usage_id = new_id("use")
            self.store.apply(
                self.run_id,
                records=[("usage", usage_id, attempt)],
                event_type="usage_updated",
                entity_id=usage_id,
                summary="Model request settled" if not attempt.get("error") else "Model request unresolved",
            )
            self.ledger.used_requests += 1
            if attempt.get("totalTokens") is None:
                self.ledger.unknown_tokens = True
            elif not self.ledger.unknown_tokens:
                self.ledger.used_tokens += int(attempt["totalTokens"])
        if not completion.ok or not completion.data:
            self.reason = "The model did not return a usable choice."
            return None
        self.last_ok = True
        self.reason = str(completion.data["rationale"])[:500]
        return str(completion.data["candidate_id"])


class CompatibleChooser:
    """Choices come from a loopback OpenAI-compatible endpoint, not from a hidden route."""

    needs_model = True
    force_verify = False

    def __init__(self, base_url: str, store, ledger, run_id: str, task: dict):
        self.base_url = base_url
        self.store = store
        self.ledger = ledger
        self.run_id = run_id
        self.task = task
        self.reason = ""
        self.missing = None
        self.last_ok = True

    async def choose(self, observation: dict, candidates: list[dict], history: list[dict]) -> str | None:
        self.last_ok = False
        result = await compatible_choose(self.base_url, json.dumps(prompt_payload(self.task, observation, candidates, history)))
        self.ledger.used_requests += 1
        total = (result.get("usage") or {}).get("total_tokens")
        if total is None:
            self.ledger.unknown_tokens = True
        elif not self.ledger.unknown_tokens:
            self.ledger.used_tokens += int(total)
        usage_id = new_id("use")
        self.store.apply(
            self.run_id,
            records=[("usage", usage_id, {"channel": "model", "purpose": "browser_plan", "totalTokens": total, "spendingUSD": None})],
            event_type="usage_updated",
            entity_id=usage_id,
            summary="Compatible endpoint request settled" if result.get("ok") else "Compatible endpoint request failed",
        )
        data = result.get("data") or {}
        if not result.get("ok") or "candidate_id" not in data:
            self.reason = result.get("detail") or "The endpoint did not name a candidate."
            return None
        self.last_ok = True
        self.reason = str(data.get("rationale") or "Chosen by the configured endpoint.")[:500]
        return str(data["candidate_id"])
