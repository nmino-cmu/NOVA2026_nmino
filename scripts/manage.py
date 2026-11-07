#!/usr/bin/env python3
"""Setup, start, stop, reset, and playback for a local Ghost Users checkout."""

from __future__ import annotations

import os
import secrets
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv" / "bin" / "python"


def _reexec() -> None:
    if os.environ.get("GHOST_NO_REEXEC") == "1" or not VENV.exists():
        return
    if Path(sys.executable).resolve() != VENV.resolve():
        os.environ["GHOST_NO_REEXEC"] = "1"
        os.execv(VENV, [str(VENV), *sys.argv])


def _data() -> Path:
    raw = os.environ.get("GHOST_DATA_DIR")
    path = Path(raw) if raw else ROOT / ".data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _token(data: Path) -> str:
    path = data / "orbit.token"
    if not path.exists():
        path.write_text(secrets.token_urlsafe(24), encoding="utf-8")
        path.chmod(0o600)
    return path.read_text(encoding="utf-8").strip()


def _listening(port: int) -> bool:
    with socket.socket() as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _ports() -> tuple[int, int]:
    return int(os.environ.get("GHOST_PORT", "8787")), int(os.environ.get("ORBIT_PORT", "8788"))


def _pid_dir(data: Path) -> Path:
    path = data / "run"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _command(pid: int) -> str:
    try:
        return subprocess.check_output(["ps", "-p", str(pid), "-o", "command="], text=True).strip()
    except subprocess.CalledProcessError:
        return ""


def setup() -> int:
    print(f"python {sys.version.split()[0]}")
    if sys.version_info < (3, 11):
        print("Python 3.11 or newer is required.")
        return 1
    if not (ROOT / "requirements.txt").exists():
        print("requirements.txt is missing.")
        return 1
    try:
        import fastapi  # noqa: F401
        import playwright  # noqa: F401
    except Exception:
        print("Dependencies are not installed in this interpreter.")
        print("Install with: uv sync   or   python -m venv .venv && .venv/bin/pip install -r requirements.txt")
        return 1
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
    data = _data()
    _token(data)
    print(f"data directory: {data}")
    print("setup ok")
    return 0


def _spawn(name: str, args: list[str], env: dict, data: Path) -> None:
    log = _pid_dir(data) / f"{name}.log"
    handle = log.open("ab")
    proc = subprocess.Popen(args, cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT)
    (_pid_dir(data) / f"{name}.pid").write_text(str(proc.pid), encoding="utf-8")
    (_pid_dir(data) / f"{name}.cmd").write_text(" ".join(args), encoding="utf-8")


def _wait(url: str) -> bool:
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=0.5) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.2)
    return False


def start() -> int:
    data = _data()
    token = _token(data)
    ghost_port, orbit_port = _ports()
    for port in (ghost_port, orbit_port):
        if _listening(port):
            print(f"127.0.0.1:{port} is already in use. Ghost Users will not stop that process.")
            return 1
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + str(ROOT / "backend") + os.pathsep + env.get("PYTHONPATH", "")
    env["GHOST_DATA_DIR"] = str(data)
    env["ORBIT_CONTROL_TOKEN"] = token
    env["ORBIT_DB"] = str(data / "orbit.sqlite3")
    env["ORBIT_BUILD"] = env.get("ORBIT_BUILD", "orbit-buggy-v1")
    env["ORBIT_PORT"] = str(orbit_port)
    env["GHOST_PORT"] = str(ghost_port)
    py = sys.executable
    _spawn("orbit", [py, "-m", "uvicorn", "fixtures.orbit.app:app", "--host", "127.0.0.1", "--port", str(orbit_port)], env, data)
    _spawn("ghost", [py, "-m", "uvicorn", "ghost.api:app", "--app-dir", str(ROOT / "backend"), "--host", "127.0.0.1", "--port", str(ghost_port)], env, data)
    orbit_ok = _wait(f"http://127.0.0.1:{orbit_port}/health")
    ghost_ok = _wait(f"http://127.0.0.1:{ghost_port}/api/health")
    if not orbit_ok or not ghost_ok:
        print("startup failed; stopping the processes this command started")
        stop()
        return 1
    print(f"Orbit Supply  http://127.0.0.1:{orbit_port}/")
    print(f"Ghost Users   http://127.0.0.1:{ghost_port}/")
    print("UI dev server http://127.0.0.1:5173/  (npm run dev inside frontend)")
    return 0


def stop() -> int:
    data = _data()
    for name, marker in (("ghost", "ghost.api:app"), ("orbit", "fixtures.orbit.app:app")):
        pid_path = _pid_dir(data) / f"{name}.pid"
        if not pid_path.exists():
            continue
        pid = int(pid_path.read_text(encoding="utf-8").strip() or "0")
        command = _command(pid)
        if not command:
            pid_path.unlink(missing_ok=True)
            continue
        if marker not in command:
            print(f"refusing to stop pid {pid}; it is not the {name} process this checkout started")
            continue
        os.kill(pid, 15)
        deadline = time.time() + 5
        while time.time() < deadline and _command(pid):
            time.sleep(0.1)
        if _command(pid):
            print(f"{name} pid {pid} did not exit")
            return 1
        pid_path.unlink(missing_ok=True)
    return 0


def reset_fixture() -> int:
    import json

    data = _data()
    token = _token(data)
    _ghost, orbit_port = _ports()
    body = json.dumps({"namespace": "manual"}).encode()
    request = urllib.request.Request(
        f"http://127.0.0.1:{orbit_port}/control/reset",
        data=body,
        headers={"Content-Type": "application/json", "X-Orbit-Control": token},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        payload = json.loads(response.read().decode())
    print(f"reset {payload.get('resetInstanceId')} hash {payload.get('initialStateHash')} ok={payload.get('ok')}")
    return 0 if payload.get("ok") else 1


def playback(run_id: str) -> int:
    ghost_port, _orbit = _ports()
    print(f"http://127.0.0.1:{ghost_port}/playback/{run_id}")
    print("Playback reads the recorded run. It does not start a browser investigation.")
    return 0


def main(argv: list[str]) -> int:
    _reexec()
    if len(argv) < 2 or argv[1] not in {"setup", "start", "stop", "reset-fixture", "playback"}:
        print("usage: python scripts/manage.py setup|start|stop|reset-fixture|playback RUN_ID")
        return 2
    command = argv[1]
    if command == "setup":
        return setup()
    if command == "start":
        return start()
    if command == "stop":
        return stop()
    if command == "reset-fixture":
        return reset_fixture()
    if len(argv) < 3:
        print("playback needs a run id")
        return 2
    return playback(argv[2])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
