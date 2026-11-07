#!/usr/bin/env python3
"""Publish the live Ghost Users demo onto the personal site.

Starts a public-demo API on 127.0.0.1:8792 with its own empty data directory,
keeps an HTTPS tunnel in front of it, and builds the frontend into the website's
public/nova2026 folder. Commit and push that folder to update nickmino.com.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(os.environ.get("SITE_ROOT", ROOT.parent.parent / "Personal_Website"))
OUT = SITE / "public" / "nova2026"
DATA = ROOT / ".data-live-demo"
PORT = int(os.environ.get("GHOST_PUBLIC_PORT", "8792"))
TUNNEL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
CORS = "https://nickmino.com,https://www.nickmino.com"


def load_env(path: Path, env: dict) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env.setdefault(key.strip(), value.strip().strip("'\""))


def get(url: str, timeout: float = 3) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except Exception:
        return 0, b""


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def read_pid(path: Path) -> int | None:
    if not path.is_file():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def stop_pid(path: Path) -> None:
    pid = read_pid(path)
    if pid is None or not pid_alive(pid):
        return
    os.kill(pid, signal.SIGTERM)
    for _ in range(30):
        if not pid_alive(pid):
            return
        time.sleep(0.2)
    os.kill(pid, signal.SIGKILL)


def python() -> str:
    candidate = ROOT / ".venv" / "bin" / "python"
    return str(candidate if candidate.is_file() else Path(sys.executable))


def ghost_env() -> dict:
    env = os.environ.copy()
    load_env(ROOT / ".env", env)
    env["GHOST_PUBLIC_DEMO"] = "1"
    env["GHOST_DATA_DIR"] = str(DATA)
    env["GHOST_PORT"] = str(PORT)
    env["GHOST_HOST"] = "127.0.0.1"
    env["GHOST_CORS_ORIGINS"] = CORS
    env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT), str(ROOT / "backend"), env.get("PYTHONPATH", "")]
    )
    return env


def start_ghost() -> None:
    status, body = get(f"http://127.0.0.1:{PORT}/api/health")
    if status == 200 and json.loads(body).get("publicDemo") is True:
        return
    stop_pid(DATA / "ghost.pid")
    DATA.mkdir(parents=True, exist_ok=True)
    log = open(DATA / "ghost.log", "ab")
    proc = subprocess.Popen(
        [python(), "-m", "uvicorn", "ghost.api:app", "--app-dir", str(ROOT / "backend"), "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=ROOT,
        env=ghost_env(),
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    (DATA / "ghost.pid").write_text(str(proc.pid), encoding="utf-8")
    deadline = time.time() + 40
    while time.time() < deadline:
        status, body = get(f"http://127.0.0.1:{PORT}/api/health")
        if status == 200 and json.loads(body).get("publicDemo") is True:
            return
        if proc.poll() is not None:
            raise SystemExit(f"Public demo API exited. See {DATA / 'ghost.log'}")
        time.sleep(0.4)
    raise SystemExit(f"Public demo API did not become ready. See {DATA / 'ghost.log'}")


def tunnel_url() -> str:
    saved = DATA / "tunnel.url"
    if saved.is_file():
        url = saved.read_text(encoding="utf-8").strip()
        status, body = get(f"{url}/api/health", timeout=8)
        if status == 200 and json.loads(body).get("publicDemo") is True:
            return url
    stop_pid(DATA / "tunnel.pid")
    DATA.mkdir(parents=True, exist_ok=True)
    log_path = DATA / "tunnel.log"
    log = open(log_path, "ab")
    proc = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", f"http://127.0.0.1:{PORT}", "--no-autoupdate"],
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    (DATA / "tunnel.pid").write_text(str(proc.pid), encoding="utf-8")
    deadline = time.time() + 75
    while time.time() < deadline:
        text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.is_file() else ""
        match = TUNNEL_RE.search(text)
        if match and proc.poll() is None:
            url = match.group(0)
            status, body = get(f"{url}/api/health", timeout=15)
            if status == 200 and json.loads(body).get("publicDemo") is True:
                saved.write_text(url + "\n", encoding="utf-8")
                return url
        if proc.poll() is not None:
            break
        time.sleep(0.5)
    raise SystemExit(f"HTTPS tunnel did not come up. See {log_path}")


def build(origin: str) -> None:
    if not (SITE / "public").is_dir():
        raise SystemExit(f"Personal site not found at {SITE}")
    if OUT.is_dir():
        shutil.rmtree(OUT)
    env = os.environ.copy()
    env.update(
        {
            "VITE_BASE": "/nova2026/",
            "VITE_HASH_ROUTER": "1",
            "VITE_LIVE_DEMO": "1",
            "VITE_API_ORIGIN": origin,
            "VITE_OUT_DIR": str(OUT),
        }
    )
    env.pop("VITE_STATIC_DEMO", None)
    env.pop("VITE_DEMO_CONVERSATION", None)
    subprocess.check_call(["npm", "run", "build"], cwd=ROOT / "frontend", env=env)


def main() -> None:
    start_ghost()
    origin = tunnel_url()
    build(origin)
    marker = {"api": origin, "mode": "live", "update": "python3 scripts/publish_live_demo.py"}
    (OUT / "demo.json").write_text(json.dumps(marker, indent=2) + "\n", encoding="utf-8")
    html = (OUT / "index.html").read_text(encoding="utf-8")
    scripts = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in (OUT / "assets").glob("*.js"))
    if "/nova2026/" not in html:
        raise SystemExit("Built index is not rooted at /nova2026/")
    if origin not in scripts:
        raise SystemExit("Built app is missing the live API origin.")
    if "conv_" in scripts or "Orbit Supply" in scripts or "Amazon, all five" in scripts:
        raise SystemExit("Built app still contains a canned demo.")
    if (OUT / "snapshot").exists():
        raise SystemExit("Built demo still contains a recorded snapshot.")
    print(json.dumps(marker))


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)
