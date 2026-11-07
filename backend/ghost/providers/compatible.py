"""OpenAI-compatible endpoint. The product key is not sent to an arbitrary host."""

from __future__ import annotations

import json
from urllib.parse import urlsplit

import httpx


def _allowed(base_url: str, openrouter_key: str) -> str | None:
    parts = urlsplit(base_url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return None
    if parts.hostname in {"127.0.0.1", "localhost"}:
        return None
    if parts.hostname == "openrouter.ai":
        return openrouter_key or None
    return None


async def complete(base_url: str, model: str, openrouter_key: str) -> dict:
    parts = urlsplit(base_url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return {"ok": False, "detail": "The endpoint must be an http or https URL."}
    headers = {"Content-Type": "application/json"}
    key = _allowed(base_url, openrouter_key)
    if parts.hostname not in {"127.0.0.1", "localhost", "openrouter.ai"}:
        return {"ok": False, "detail": "This release tests loopback and OpenRouter. Other hosts are refused so the key stays put."}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    payload = {
        "model": model or "echo-local",
        "messages": [
            {"role": "system", "content": "Return JSON only. Do not write code."},
            {"role": "user", "content": '{"word":"ok"}'},
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            listed = await client.get(base_url.rstrip("/") + "/models", headers=headers)
            response = await client.post(base_url.rstrip("/") + "/chat/completions", headers=headers, json=payload)
    except httpx.HTTPError:
        return {"ok": False, "detail": "The endpoint did not respond."}
    if response.status_code >= 400:
        return {"ok": False, "detail": "The endpoint rejected the completion."}
    body = response.json()
    content = ((body.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    if "word" not in content:
        return {"ok": False, "detail": "The endpoint did not return the expected data."}
    observed = body.get("model")
    models = []
    if listed.status_code == 200:
        models = [item.get("id") for item in (listed.json().get("data") or []) if item.get("id")]
    return {"ok": True, "modelObserved": observed, "models": models, "usage": body.get("usage")}


async def choose(base_url: str, user: str) -> dict:
    """Ask a loopback compatible endpoint to pick a candidate. No product key is attached."""
    parts = urlsplit(base_url)
    if parts.scheme not in {"http", "https"} or parts.hostname not in {"127.0.0.1", "localhost"}:
        return {"ok": False, "detail": "A custom investigation endpoint has to be on this machine."}
    payload = {"model": "echo-local", "messages": [{"role": "user", "content": user}]}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(base_url.rstrip("/") + "/chat/completions", json=payload)
    except httpx.HTTPError:
        return {"ok": False, "detail": "The endpoint did not respond."}
    if response.status_code >= 400:
        return {"ok": False, "detail": "The endpoint rejected the choice."}
    content = ((response.json().get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    start, end = content.find("{"), content.rfind("}")
    if start < 0 or end < start:
        return {"ok": False, "detail": "The endpoint did not return JSON."}
    try:
        data = json.loads(content[start : end + 1])
    except json.JSONDecodeError:
        return {"ok": False, "detail": "The endpoint returned malformed JSON."}
    return {"ok": True, "data": data, "usage": response.json().get("usage") or {}}
