#!/usr/bin/env python3
"""Smoke-test OpenRouter: auth, models, and chat."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import openrouter

# Router picks a free/cheap model — good for smoke tests without pinning slugs.
CHAT_MODEL = "openrouter/free"


def main() -> int:
    openrouter.load_dotenv()
    key = openrouter.api_key()
    print("1) key loaded:", "yes" if len(key) >= 20 else "no")

    models = openrouter.list_models()
    raw = models.get("data", models if isinstance(models, list) else [])
    count = len(raw) if isinstance(raw, list) else 0
    print(f"2) models: {count} listed")
    if not count:
        print("   warn: empty model list", file=sys.stderr)
        return 1

    sample_id = raw[0].get("id", "?") if isinstance(raw[0], dict) else "?"
    print(f"   sample model id: {sample_id}")

    chat = openrouter.chat_completion(
        model=CHAT_MODEL,
        messages=[
            {"role": "user", "content": "Reply with exactly one word: ok"},
        ],
        max_tokens=8,
    )
    choice = (chat.get("choices") or [{}])[0]
    text = (choice.get("message") or {}).get("content", "").strip()
    usage = chat.get("usage") or {}
    print(f"3) chat ({CHAT_MODEL}): {text!r}")
    print(f"   usage: {usage}")

    chat2 = openrouter.chat_completion(
        model="google/gemma-3-4b-it",
        messages=[
            {"role": "user", "content": "What is 2+2? Reply with just the number."},
        ],
        max_tokens=8,
    )
    text2 = ((chat2.get("choices") or [{}])[0].get("message") or {}).get(
        "content", ""
    ).strip()
    routed = chat.get("model") or chat2.get("model") or "?"
    print(f"4) named model chat: {text2!r}")
    print(f"   routed model (test 3): {routed}")

    key_info = openrouter.request("GET", "auth/key")
    data = key_info.get("data") or {}
    remaining = data.get("limit_remaining", data.get("effective_budget", {}).get("remaining_usd"))
    print(f"5) key/budget: limit_remaining={remaining!r}, usage={data.get('usage')!r}")

    print("\nOpenRouter smoke tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
