"""Minimal OpenRouter client (OpenAI-compatible API, stdlib only)."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
_REPO_ROOT = Path(__file__).resolve().parent


def load_dotenv(path: Path | None = None) -> None:
    env_path = path or (_REPO_ROOT / ".env")
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def api_key() -> str:
    load_dotenv()
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "OPENROUTER_API_KEY missing — set in .env or the environment "
            "(see .env.example)"
        )
    return key


def _headers() -> dict[str, str]:
    h: dict[str, str] = {
        "Authorization": f"Bearer {api_key()}",
        "Content-Type": "application/json",
    }
    site = os.environ.get("OPENROUTER_SITE_URL", "").strip()
    app = os.environ.get("OPENROUTER_APP_NAME", "").strip()
    if site:
        h["HTTP-Referer"] = site
    if app:
        h["X-Title"] = app
    return h


def request(
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    timeout: float = 60.0,
) -> Any:
    url = f"{OPENROUTER_BASE}/{path.lstrip('/')}"
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=_headers(), method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        detail = re.sub(r"sk-or-[A-Za-z0-9_\-]+", "sk-or-REDACTED", detail)
        raise RuntimeError(f"OpenRouter HTTP {e.code}: {detail[:500]}") from e


def list_models() -> Any:
    return request("GET", "models")


def key_info() -> Any:
    return request("GET", "auth/key")


def chat_completion(
    *,
    model: str,
    messages: list[dict[str, Any]],
    max_tokens: int = 256,
    timeout: float = 60.0,
    **extra: Any,
) -> Any:
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        **extra,
    }
    return request("POST", "chat/completions", body=body, timeout=timeout)


def _self_check() -> None:
    load_dotenv()
    key = api_key()
    if len(key) < 20:
        raise SystemExit("openrouter: key missing or too short")


if __name__ == "__main__":
    _self_check()
    print("openrouter: env + key OK")
