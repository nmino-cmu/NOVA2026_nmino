"""Runtime settings. Secrets stay in the environment or the data directory."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    data_dir: Path
    repo_root: Path
    model: str
    fallback_model: str
    orbit_origin: str
    control_token: str
    planner_images: bool
    public_demo: bool

    @classmethod
    def from_env(cls) -> Settings:
        root = _root()
        data = Path(os.environ.get("GHOST_DATA_DIR") or (root / ".data"))
        token = os.environ.get("ORBIT_CONTROL_TOKEN", "")
        token_file = data / "orbit.token"
        if not token and token_file.is_file():
            token = token_file.read_text(encoding="utf-8").strip()
        origin = os.environ.get("ORBIT_ORIGIN") or (
            f"http://{os.environ.get('ORBIT_HOST', '127.0.0.1')}:"
            f"{os.environ.get('ORBIT_PORT', '8788')}"
        )
        return cls(
            host=os.environ.get("GHOST_HOST", "127.0.0.1"),
            port=int(os.environ.get("GHOST_PORT", "8787")),
            data_dir=data,
            repo_root=root,
            model=os.environ.get("GHOST_MODEL", "anthropic/claude-sonnet-4.6"),
            fallback_model=os.environ.get("GHOST_FALLBACK_MODEL", "anthropic/claude-opus-4.6"),
            orbit_origin=origin.rstrip("/"),
            control_token=token,
            planner_images=os.environ.get("GHOST_PLANNER_IMAGES") == "1",
            public_demo=os.environ.get("GHOST_PUBLIC_DEMO") == "1",
        )
