"""Frontier order for adaptive search. Estimates never become a lower bound."""

from __future__ import annotations

import re

_STOP = {
    "the", "a", "to", "with", "and", "do", "not", "an", "exactly", "one",
    "for", "out", "on", "is", "of", "in", "or", "from", "your", "start",
}


def _same(word: str, task_words: set[str]) -> bool:
    for other in task_words:
        if word == other:
            return True
        short, long = (word, other) if len(word) <= len(other) else (other, word)
        if len(short) >= 3 and long.startswith(short):
            return True
    return False


def relevance(name: str, text: str) -> int:
    words = {word for word in re.findall(r"[a-z0-9]+", name.lower()) if word not in _STOP and len(word) > 2}
    task_words = {word for word in re.findall(r"[a-z0-9]+", text.lower()) if word not in _STOP and len(word) > 2}
    if words and any(_same(word, task_words) for word in words):
        return 0
    return 1


def partition(candidates: list[dict], incumbent_u: int | None) -> tuple[list[dict], list[dict]]:
    ready, excluded = [], []
    for item in candidates:
        if item.get("status") in {"done", "invalid"}:
            continue
        bound = int(item["g"]) + int(item.get("h") or 0)
        if incumbent_u is not None and bound >= incumbent_u:
            excluded.append(item)
        else:
            ready.append(item)
    return ready, excluded


def claim_exact(seen: set[str], key: str) -> bool:
    """A completed exact action is not dispatched again. A new attempt is a new key."""
    if key in seen:
        return False
    seen.add(key)
    return True


def choose(ready: list[dict], picks_already: int) -> tuple[dict, str]:
    """Every fifth non-verification selection is the oldest eligible candidate."""
    if (picks_already + 1) % 5 == 0:
        return min(ready, key=lambda item: (item["creation"], item["id"])), "fairness"
    return min(
        ready,
        key=lambda item: (
            item["relevance"],
            item["g"] + item["actionCost"],
            item["restore"],
            item["tokens"],
            item["creation"],
            item["id"],
        ),
    ), "heuristic"
