from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def orbit_server(tmp_path_factory):
    db = tmp_path_factory.mktemp("orbit") / "orbit.sqlite3"
    port = _port()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO) + os.pathsep + env.get("PYTHONPATH", "")
    env["ORBIT_DB"] = str(db)
    env["ORBIT_CONTROL_TOKEN"] = "test-token"
    env["ORBIT_BUILD"] = "orbit-buggy-v1"
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "fixtures.orbit.app:app", "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=REPO,
        env=env,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(base + "/health", timeout=0.5) as response:
                if response.status == 200:
                    break
        except Exception:
            if proc.poll() is not None:
                raise RuntimeError("Orbit Supply exited during startup")
            time.sleep(0.1)
    else:
        proc.terminate()
        raise RuntimeError("Orbit Supply did not become healthy")
    yield {"url": base, "token": "test-token"}
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
