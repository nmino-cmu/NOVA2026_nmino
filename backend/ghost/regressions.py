"""Declared fixture checks. This is not the investigator and it is not a hint to the model."""

from __future__ import annotations

from fixtures.orbit.checks import ROUTES

POLICIES = {
    "ordinary-model-v1": ("Investigation", True, None),
    "regression.ordinary.v1": ("Fixture regression check", False, "ordinary"),
    "regression.shortcut.v1": ("Fixture regression check", False, "shortcut"),
    "regression.express.v1": ("Fixture regression check", False, "express"),
}


class Scripted:
    needs_model = False
    force_verify = True

    def __init__(self, actions: list[dict]):
        self.actions = actions
        self.index = 0
        self.reason = "Declared fixture check."
        self.missing = None
        self.last_ok = True

    async def choose(self, observation: dict, candidates: list[dict], history: list[dict]) -> str | None:
        if self.index >= len(self.actions):
            return None
        want = self.actions[self.index]["target"]
        self.index += 1
        for candidate in candidates:
            target = candidate["target"]
            if target["role"] == want["role"] and target["name"] == want["name"]:
                return candidate["id"]
        self.missing = want["name"]
        self.last_ok = False
        self.reason = f"{want['name']} was not available."
        return None


def scripted_for(policy_id: str) -> Scripted:
    _label, _discovery, kind = POLICIES[policy_id]
    if kind is None:
        raise ValueError(policy_id)
    return Scripted(ROUTES[kind])
