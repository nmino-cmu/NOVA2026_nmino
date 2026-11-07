"""Exploration keeps a replay reservation. Unknown model usage is not zero."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class Ledger:
    wall_ms: int
    requests: int
    total_tokens: int
    browser_actions: int
    resets: int
    route_actions: int
    started: float = field(default_factory=time.monotonic)
    used_requests: int = 0
    used_browser: int = 0
    used_resets: int = 0
    used_tokens: int = 0
    unknown_tokens: bool = False
    choices: int = 0

    @classmethod
    def from_task(cls, task: dict) -> Ledger:
        budget = task["budget"]
        return cls(
            wall_ms=budget["wallMs"],
            requests=budget["requests"],
            total_tokens=budget["totalTokens"],
            browser_actions=budget["browserActions"],
            resets=budget["resets"],
            route_actions=task["limits"]["routeActions"],
        )

    def elapsed_ms(self) -> int:
        return int((time.monotonic() - self.started) * 1000)

    def can_start(self) -> bool:
        return self.resets >= 2 and self.browser_actions >= 2 and self.wall_ms >= 40_000

    def explore_block(self, route_len: int, needs_model: bool) -> str | None:
        if self.choices >= 24 or route_len + 1 > self.route_actions:
            return "search_envelope_exhausted"
        replay_need = route_len + 2  # next route click, later setup navigation
        if self.used_browser + 1 + replay_need > self.browser_actions:
            return "budget_exhausted"
        if self.used_resets + 1 > self.resets:
            return "budget_exhausted"
        if self.elapsed_ms() + 40_000 > self.wall_ms:
            return "budget_exhausted"
        if needs_model and self.used_requests >= self.requests:
            return "budget_exhausted"
        if needs_model and not self.unknown_tokens and self.used_tokens + 4_768 > self.total_tokens:
            return "budget_exhausted"
        return None

    def can_verify(self, route_len: int) -> bool:
        needed = route_len + 1
        return (
            self.elapsed_ms() + 40_000 <= self.wall_ms
            and self.used_resets + 1 <= self.resets
            and self.used_browser + needed <= self.browser_actions
        )
