"""Guarded product adapter. It has no tools and it does not implement source changes."""

from __future__ import annotations

import asyncio
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from ghost.config import Settings
from ghost.providers.guard import ALLOWED_PURPOSES, find_violation

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import openrouter  # noqa: E402

_KEY = re.compile(r"sk-or-[A-Za-z0-9_\-]+")


def redact(text: str) -> str:
    return _KEY.sub("sk-or-REDACTED", text)[:500]


@dataclass
class Completion:
    ok: bool
    data: dict | None
    attempts: list[dict]
    error: str | None


def _usage(raw: dict | None, *, model: str, purpose: str, attempt: int, error: str | None = None) -> dict:
    usage = (raw or {}).get("usage") if isinstance(raw, dict) else None
    usage = usage or {}
    prompt = usage.get("prompt_tokens")
    completion = usage.get("completion_tokens")
    total = usage.get("total_tokens")
    if total is None and isinstance(prompt, int) and isinstance(completion, int):
        total = prompt + completion
    details = usage.get("prompt_tokens_details") if isinstance(usage.get("prompt_tokens_details"), dict) else {}
    output_details = usage.get("completion_tokens_details") if isinstance(usage.get("completion_tokens_details"), dict) else {}
    cost = usage.get("cost")
    known = raw is not None and error is None and total is not None
    return {
        "channel": "model",
        "purpose": purpose,
        "attempt": attempt,
        "status": "settled" if error is None else "unresolved",
        "inputTokens": prompt if isinstance(prompt, int) else None,
        "outputTokens": completion if isinstance(completion, int) else None,
        "totalTokens": total if isinstance(total, int) else None,
        "cachedInputTokens": details.get("cached_tokens"),
        "reasoningTokens": output_details.get("reasoning_tokens"),
        "spendingUSD": cost if isinstance(cost, (int, float)) else None,
        "browserActions": 0,
        "resets": 0,
        "modelRequested": model,
        "modelObserved": (raw or {}).get("model") if isinstance(raw, dict) else None,
        "accounting": "reported" if known else "unknown",
        "error": error,
    }


def _content(raw: dict) -> str:
    choice = (raw.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content") or ""
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    return str(content).strip()


def _parse(content: str) -> tuple[dict | None, str | None]:
    violation = find_violation(content)
    if violation:
        return None, violation
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return None, "malformed_json"
    if not isinstance(data, dict):
        return None, "malformed_json"
    found = find_violation(data)
    if found:
        return None, found
    return data, None


def _schema(name: str) -> dict:
    fields = {
        "candidate_choice": ("candidate_id", "rationale"),
        "probe": ("word",),
    }.get(name, ("task",))
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {field: {"type": "string"} for field in fields},
        "required": list(fields),
    }


def _call(model: str, messages: list[dict], schema_name: str | None, max_tokens: int = 768, timeout: float = 45) -> dict:
    extra = {}
    if schema_name:
        extra["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "strict": True,
                "schema": _schema(schema_name),
            },
        }
    try:
        return openrouter.chat_completion(model=model, messages=messages, max_tokens=max_tokens, timeout=timeout, **extra)
    except RuntimeError as exc:
        if schema_name and ("response_format" in str(exc) or "json_schema" in str(exc)):
            return openrouter.chat_completion(model=model, messages=messages, max_tokens=max_tokens, timeout=timeout)
        raise


def _quarantine(settings: Settings, purpose: str, content: str, violation: str) -> None:
    folder = settings.data_dir / "audit"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"rejected-{purpose}.json"
    path.write_text(
        json.dumps({"purpose": purpose, "violation": violation, "content": redact(content)[:4000]}),
        encoding="utf-8",
    )


async def complete_json(
    settings: Settings,
    *,
    purpose: str,
    system: str,
    user: str,
    required: list[str],
    schema_name: str,
) -> Completion:
    if purpose not in ALLOWED_PURPOSES:
        raise ValueError(f"purpose {purpose} is not allowed")
    openrouter.load_dotenv()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user[:12000]},
    ]
    attempts: list[dict] = []

    async def once(model: str, use_schema: bool, attempt: int) -> tuple[dict | None, str | None]:
        try:
            raw = await asyncio.to_thread(_call, model, messages, schema_name if use_schema else None)
        except Exception as exc:
            attempts.append(_usage(None, model=model, purpose=purpose, attempt=attempt, error=redact(str(exc))))
            return None, "transport"
        content = _content(raw)
        data, violation = _parse(content)
        attempts.append(_usage(raw, model=model, purpose=purpose, attempt=attempt, error=violation))
        if violation:
            _quarantine(settings, purpose, content, violation)
            return None, violation
        if data is None or any(key not in data or not isinstance(data[key], str) for key in required):
            return None, "malformed_json"
        return data, None

    data, problem = await once(settings.model, True, 1)
    if data is not None:
        return Completion(True, data, attempts, None)
    if problem == "transport" and settings.fallback_model != settings.model:
        data, problem = await once(settings.fallback_model, True, 2)
    else:
        data, problem = await once(settings.model, False, 2)
    if data is not None:
        return Completion(True, data, attempts, None)
    return Completion(False, None, attempts, problem or "model_failed")


def _strip_fence(content: str) -> str:
    text = content.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _parse_document(content: str) -> tuple[dict | None, str | None]:
    content = _strip_fence(content)
    violation = find_violation(content)
    if violation:
        return None, violation
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        start, end = content.find("{"), content.rfind("}")
        if start < 0 or end <= start:
            return None, "malformed_json"
        snippet = content[start : end + 1]
        violation = find_violation(snippet)
        if violation:
            return None, violation
        try:
            data = json.loads(snippet)
        except json.JSONDecodeError:
            return None, "malformed_json"
    if not isinstance(data, dict):
        return None, "malformed_json"
    found = find_violation(data)
    if found:
        return None, found
    return data, None


async def complete_document(
    settings: Settings,
    *,
    purpose: str,
    system: str,
    user: str,
    images: list[str] | None = None,
    max_tokens: int = 1800,
) -> Completion:
    """Nested JSON for plans and reports. Images are evidence, not repository source."""
    if purpose not in ALLOWED_PURPOSES:
        raise ValueError(f"purpose {purpose} is not allowed")
    openrouter.load_dotenv()
    if images:
        content: str | list = [{"type": "text", "text": user[:28000]}]
        content.extend({"type": "image_url", "image_url": {"url": image}} for image in images[:4])
    else:
        content = user[:28000]
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": content},
    ]
    attempts: list[dict] = []

    async def once(model: str, attempt: int) -> tuple[dict | None, str | None]:
        try:
            raw = await asyncio.to_thread(_call, model, messages, None, max_tokens, 90)
        except Exception as exc:
            attempts.append(_usage(None, model=model, purpose=purpose, attempt=attempt, error=redact(str(exc))))
            return None, "transport"
        text = _content(raw)
        data, violation = _parse_document(text)
        attempts.append(_usage(raw, model=model, purpose=purpose, attempt=attempt, error=violation))
        if violation:
            _quarantine(settings, purpose, text, violation)
            return None, violation
        if data is None:
            return None, "malformed_json"
        return data, None

    data, problem = await once(settings.model, 1)
    if data is not None:
        return Completion(True, data, attempts, None)
    fallback = settings.fallback_model if problem == "transport" and settings.fallback_model != settings.model else settings.model
    data, problem = await once(fallback, 2)
    if data is not None:
        return Completion(True, data, attempts, None)
    return Completion(False, None, attempts, problem or "model_failed")
