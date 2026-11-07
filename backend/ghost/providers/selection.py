"""Saved provider choice. The key never lands in this file."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit


def _path(data_dir: Path) -> Path:
    return Path(data_dir) / "provider.json"


def describe(kind: str, model: str, base_url: str) -> dict:
    if model == "echo-local" or kind == "echo-fixture":
        return {
            "kind": "compatible",
            "fixture": "echo-local",
            "baseUrl": base_url.rstrip("/"),
            "model": "echo-local",
            "label": "Deterministic echo fixture",
            "honest": "This fixture picks an id from the candidate list it is shown. It is not a general model.",
        }
    if kind == "openrouter":
        return {
            "kind": "openrouter",
            "baseUrl": "https://openrouter.ai/api/v1",
            "model": model,
            "label": "OpenRouter",
            "honest": "The server holds the key. This page never receives it.",
        }
    return {
        "kind": "compatible",
        "baseUrl": base_url.rstrip("/"),
        "model": model,
        "label": "Loopback endpoint",
        "honest": "Requests stay on this machine. The product key is not attached.",
    }


def load_selection(data_dir: Path) -> dict | None:
    path = _path(data_dir)
    if not path.is_file():
        return None
    try:
        body = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not body.get("model") or not body.get("kind"):
        return None
    return body


def save_selection(data_dir: Path, base_url: str, model: str, kind: str) -> dict:
    model = model.strip()
    base_url = base_url.strip()
    if not model:
        raise ValueError("Name the model.")
    if kind == "openrouter":
        saved = describe("openrouter", model, base_url)
    elif kind == "echo-fixture" or model == "echo-local":
        if not base_url:
            base_url = "http://127.0.0.1:8791/v1"
        saved = describe("echo-fixture", "echo-local", base_url)
    else:
        parts = urlsplit(base_url)
        if parts.scheme not in {"http", "https"} or parts.hostname not in {"127.0.0.1", "localhost"}:
            raise ValueError("A saved custom endpoint has to be on this machine, or choose OpenRouter.")
        saved = describe("compatible", model, base_url)
    path = _path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(saved), encoding="utf-8")
    return saved
