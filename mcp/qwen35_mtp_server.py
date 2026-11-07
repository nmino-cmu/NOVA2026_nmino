"""MCP → local Qwen 3.6 35B 6-bit + MTP-4bit speculative server (loopback HTTP)."""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from mcp.server.mcpserver.server import MCPServer

HOST = "127.0.0.1"
PORT = int(os.environ.get("QWEN35_MTP_PORT", "18092"))
BASE = f"http://{HOST}:{PORT}/v1"
MODEL_DIR = Path.home() / ".lmstudio/models/mlx-community/Qwen3.6-35B-A3B-6bit"
DRAFT_DIR = Path.home() / ".lmstudio/models/mlx-community/Qwen3.6-35B-A3B-MTP-4bit"
START_SH = Path(__file__).resolve().parents[1] / "scripts" / "qwen35_mtp_server.sh"


def _get(path: str, timeout: float = 5.0) -> tuple[int | None, dict | list | None]:
    try:
        with urllib.request.urlopen(f"{BASE}{path}", timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode())
        except Exception:
            body = {"error": str(e)}
        return e.code, body
    except Exception as e:
        return None, {"error": str(e)}


def _post_chat(body: dict, timeout: float) -> tuple[float, dict]:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE}/chat/completions",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        out = json.loads(r.read().decode())
    return time.perf_counter() - t0, out


def _weights_ready() -> dict:
    def _ok(d: Path) -> bool:
        if not d.is_dir():
            return False
        if list(d.glob("model-*.safetensors")):
            return True
        if (d / "model.safetensors").is_file():
            return True
        return not list(d.glob("*.part")) and (d / "model.safetensors.index.json").is_file()

    return {
        "body_dir": str(MODEL_DIR),
        "draft_dir": str(DRAFT_DIR),
        "body_ready": _ok(MODEL_DIR),
        "draft_ready": _ok(DRAFT_DIR),
    }


def build_server() -> MCPServer:
    server = MCPServer(
        name="qwen35-mtp",
        instructions=(
            "Local Qwen3.6 35B-A3B 6-bit with MTP-4bit speculative decoding "
            f"at {BASE}. Call ensure_server before complete/benchmark if models are loaded."
        ),
        log_level="INFO",
    )

    @server.tool()
    async def qwen35_mtp_status() -> str:
        """Weights on disk, HTTP /v1/models, and active generation count."""
        st, models = _get("/models")
        st2, status = _get("/status")
        payload = {
            **_weights_ready(),
            "base_url": BASE,
            "models_http": st,
            "models": models,
            "status_http": st2,
            "status": status,
        }
        return json.dumps(payload, ensure_ascii=False)

    @server.tool()
    async def ensure_qwen35_mtp_server() -> str:
        """Start mlx_vlm MTP sidecar if weights are present (background, loopback)."""
        w = _weights_ready()
        if not w["body_ready"] or not w["draft_ready"]:
            return json.dumps({"ok": False, "reason": "weights_incomplete", **w})
        st, _ = _get("/models")
        if st == 200:
            return json.dumps({"ok": True, "action": "already_up", "base_url": BASE})
        if not START_SH.is_file():
            return json.dumps({"ok": False, "error": f"missing {START_SH}"})
        START_SH.chmod(0o755)
        proc = subprocess.Popen(
            [str(START_SH)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        deadline = time.time() + float(os.environ.get("QWEN35_BOOT_TIMEOUT", "600"))
        while time.time() < deadline:
            await asyncio.sleep(2)
            st, models = _get("/models", timeout=3.0)
            if st == 200:
                return json.dumps({"ok": True, "pid": proc.pid, "models": models})
        err = proc.stderr.read(4000).decode() if proc.stderr else ""
        return json.dumps({"ok": False, "pid": proc.pid, "stderr_tail": err[-2000:]})

    @server.tool()
    async def qwen35_mtp_complete(
        prompt: str,
        max_tokens: int = 256,
        temperature: float = 0.0,
    ) -> str:
        """One-shot chat completion through MTP speculative decode."""
        _, models = _get("/models")
        model_id = "qwen35-mtp"
        if isinstance(models, dict):
            data = models.get("data") or []
            if data:
                model_id = str(data[0].get("id", model_id))
        body = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": "Answer directly in assistant content. /no_think"},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max(1, min(int(max_tokens), 4096)),
            "temperature": float(temperature),
            "stream": False,
        }
        wall, out = await asyncio.to_thread(_post_chat, body, 600.0)
        msg = (out.get("choices") or [{}])[0].get("message") or {}
        usage = out.get("usage") or {}
        comp = int(usage.get("completion_tokens") or 0)
        text = (msg.get("content") or msg.get("reasoning_content") or "").strip()
        return json.dumps(
            {
                "text": text[:12000],
                "wall_s": round(wall, 3),
                "completion_tokens": comp,
                "tok_s": round(comp / wall, 2) if wall > 0 and comp else None,
                "usage": usage,
            },
            ensure_ascii=False,
        )

    @server.tool()
    async def qwen35_mtp_benchmark(max_tokens: int = 256) -> str:
        """Warmup + timed decode for speculative MTP tok/s (reasoning off)."""
        prompt = (
            "List 40 short English nouns, one per line, numbered 1) through 40). "
            "No preamble."
        )
        body = {
            "model": "qwen35-mtp",
            "messages": [
                {"role": "system", "content": "Direct list only. /no_think"},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max(64, min(int(max_tokens), 512)),
            "temperature": 0.0,
            "stream": False,
        }
        await asyncio.to_thread(_post_chat, {**body, "max_tokens": 32}, 600.0)
        wall, out = await asyncio.to_thread(_post_chat, body, 600.0)
        usage = out.get("usage") or {}
        comp = int(usage.get("completion_tokens") or 0)
        return json.dumps(
            {
                "wall_s": round(wall, 3),
                "completion_tokens": comp,
                "tok_s": round(comp / wall, 2) if wall > 0 and comp else None,
                "draft_block": int(os.environ.get("QWEN35_MTP_BLOCK", "2")),
                "base_url": BASE,
            },
            ensure_ascii=False,
        )

    return server


def main() -> None:
    server = build_server()
    asyncio.run(server.run_stdio_async())


if __name__ == "__main__":
    main()
