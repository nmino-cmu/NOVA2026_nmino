"""SQLite store. Record changes and their outbox event commit together."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ghost.ids import new_id

_ID = re.compile(r"ev_[0-9a-f]{16}")


def now() -> str:
    return datetime.now(ZoneInfo("America/New_York")).isoformat()


class Store:
    def __init__(self, data_dir: Path):
        self.root = Path(data_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.root / "ghost.sqlite3", check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.isolation_level = None
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._lock = threading.RLock()
        self._migrate()

    def _migrate(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS tasks (
              id TEXT PRIMARY KEY,
              version INTEGER NOT NULL,
              payload TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS runs (
              id TEXT PRIMARY KEY,
              task_id TEXT NOT NULL,
              status TEXT NOT NULL,
              idempotency_key TEXT NOT NULL UNIQUE,
              through_seq INTEGER NOT NULL DEFAULT 0,
              stop_requested INTEGER NOT NULL DEFAULT 0,
              payload TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
              run_id TEXT NOT NULL,
              seq INTEGER NOT NULL,
              type TEXT NOT NULL,
              entity_id TEXT NOT NULL,
              entity_revision INTEGER NOT NULL,
              payload TEXT NOT NULL,
              created_at TEXT NOT NULL,
              PRIMARY KEY (run_id, seq)
            );
            CREATE TABLE IF NOT EXISTS evidence (
              id TEXT PRIMARY KEY,
              run_id TEXT NOT NULL,
              kind TEXT NOT NULL,
              relative_path TEXT NOT NULL,
              sha256 TEXT NOT NULL,
              media_type TEXT NOT NULL,
              captured_at TEXT NOT NULL,
              label TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS records (
              kind TEXT NOT NULL,
              id TEXT NOT NULL,
              run_id TEXT NOT NULL,
              payload TEXT NOT NULL,
              PRIMARY KEY (kind, id)
            );
            """
        )

    @contextmanager
    def transaction(self):
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                yield
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    def create_task(self, spec: dict) -> dict:
        task_id = spec.get("id") or new_id("task")
        stored = {**spec, "id": task_id, "version": 1}
        with self.transaction():
            self._conn.execute(
                "INSERT INTO tasks(id, version, payload, created_at) VALUES(?,?,?,?)",
                (task_id, 1, json.dumps(stored), now()),
            )
        return stored

    def get_task(self, task_id: str) -> dict:
        with self._lock:
            row = self._conn.execute("SELECT payload FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not row:
            raise KeyError(task_id)
        return json.loads(row["payload"])

    def create_run(self, *, task_id: str, policy_id: str, idempotency_key: str, discovery: bool, label: str) -> dict:
        with self.transaction():
            existing = self._conn.execute(
                "SELECT id FROM runs WHERE idempotency_key=?", (idempotency_key,)
            ).fetchone()
            if existing:
                return self._run(existing["id"])
            run_id = new_id("run")
            payload = {
                "taskId": task_id,
                "policyId": policy_id,
                "discovery": discovery,
                "label": label,
                "phase": "setup",
                "stopReason": None,
                "error": None,
                "buildId": None,
                "checks": [
                    {"id": "initial", "name": "Initial conditions", "status": "pending", "detail": ""},
                    {"id": "invariants", "name": "Invariants", "status": "pending", "detail": ""},
                    {"id": "goal", "name": "Goal", "status": "pending", "detail": ""},
                ],
                "limitations": [],
                "currentAction": None,
                "startedEpoch": __import__("time").time(),
                "elapsedMs": None,
                "namespace": None,
                "restoration": None,
                "finished": False,
                "versions": {
                    "schema": 1,
                    "task": 1,
                    "app": "",
                    "environment": "local",
                    "policy": policy_id,
                    "observer": "observer-v1",
                    "graph": 1,
                    "promptSet": "planner-v1",
                },
            }
            self._conn.execute(
                """INSERT INTO runs(id, task_id, status, idempotency_key, through_seq, stop_requested, payload, created_at)
                   VALUES(?,?,?,?,0,0,?,?)""",
                (run_id, task_id, "queued", idempotency_key, json.dumps(payload), now()),
            )
            return self._run(run_id)

    def _run(self, run_id: str) -> dict:
        row = self._conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            raise KeyError(run_id)
        payload = json.loads(row["payload"])
        payload.update(
            {
                "id": row["id"],
                "taskId": row["task_id"],
                "status": row["status"],
                "throughSeq": row["through_seq"],
                "stopRequested": bool(row["stop_requested"]),
                "createdAt": row["created_at"],
            }
        )
        return payload

    def get_run(self, run_id: str) -> dict:
        with self._lock:
            return self._run(run_id)

    def list_runs(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute("SELECT id FROM runs ORDER BY created_at DESC").fetchall()
            return [self._run(row["id"]) for row in rows]

    def update_run(self, run_id: str, **fields) -> dict:
        with self.transaction():
            current = self._run(run_id)
            status = fields.get("status", current["status"])
            payload = {key: value for key, value in current.items() if key not in {"id", "status", "throughSeq", "stopRequested", "createdAt"}}
            payload.update(fields)
            payload.pop("status", None)
            self._conn.execute(
                "UPDATE runs SET status=?, payload=? WHERE id=?",
                (status, json.dumps(payload), run_id),
            )
            return self._run(run_id)

    def request_stop(self, run_id: str) -> None:
        with self.transaction():
            self._conn.execute("UPDATE runs SET stop_requested=1 WHERE id=?", (run_id,))

    def finish(self, run_id: str, **fields) -> dict:
        with self.transaction():
            current = self._run(run_id)
            if current.get("finished"):
                return current
            started = float(current.get("startedEpoch") or __import__("time").time())
            fields["finished"] = True
            fields["phase"] = "done"
            fields["elapsedMs"] = int((__import__("time").time() - started) * 1000)
            status = fields.get("status", current["status"])
            payload = {key: value for key, value in current.items() if key not in {"id", "status", "throughSeq", "stopRequested", "createdAt"}}
            payload.update(fields)
            payload.pop("status", None)
            self._conn.execute(
                "UPDATE runs SET status=?, payload=? WHERE id=?",
                (status, json.dumps(payload), run_id),
            )
            self._event(run_id, "task_finished", run_id, {"summary": fields.get("stopReason") or status, "stopReason": fields.get("stopReason"), "status": status})
            return self._run(run_id)

    def recover(self) -> int:
        with self._lock:
            rows = self._conn.execute("SELECT id FROM runs WHERE status IN ('queued','running')").fetchall()
            ids = [row["id"] for row in rows]
        for run_id in ids:
            current = self.get_run(run_id)
            limits = list(current.get("limitations") or [])
            limits.append("Server restarted before the run finished. Browser work was not resumed.")
            self.finish(
                run_id,
                status="error",
                stopReason="infrastructure_failure",
                error="Server restarted before the run finished. Browser work was not resumed.",
                limitations=limits,
            )
        return len(ids)

    def apply(self, run_id: str, *, records: list[tuple[str, str, dict]], event_type: str, entity_id: str, summary: str, extra: dict | None = None) -> int:
        with self.transaction():
            for kind, record_id, payload in records:
                self._conn.execute(
                    "INSERT INTO records(kind, id, run_id, payload) VALUES(?,?,?,?)",
                    (kind, record_id, run_id, json.dumps(payload)),
                )
            body = {"summary": summary, **(extra or {})}
            return self._event(run_id, event_type, entity_id, body)

    def add_event(self, run_id: str, event_type: str, entity_id: str, payload: dict) -> int:
        with self.transaction():
            return self._event(run_id, event_type, entity_id, payload)

    def _event(self, run_id: str, event_type: str, entity_id: str, payload: dict) -> int:
        row = self._conn.execute(
            "SELECT COALESCE(MAX(seq), 0) + 1 AS n FROM events WHERE run_id=?", (run_id,)
        ).fetchone()
        seq = int(row["n"])
        self._conn.execute(
            """INSERT INTO events(run_id, seq, type, entity_id, entity_revision, payload, created_at)
               VALUES(?,?,?,?,1,?,?)""",
            (run_id, seq, event_type, entity_id, json.dumps(payload), now()),
        )
        self._conn.execute("UPDATE runs SET through_seq=? WHERE id=?", (seq, run_id))
        return seq

    def events_after(self, run_id: str, after: int) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT seq, type, entity_id, payload, created_at FROM events WHERE run_id=? AND seq>? ORDER BY seq",
                (run_id, after),
            ).fetchall()
        return [
            {
                "seq": row["seq"],
                "type": row["type"],
                "entityId": row["entity_id"],
                "payload": json.loads(row["payload"]),
                "at": row["created_at"],
            }
            for row in rows
        ]

    def find(self, kind: str, record_id: str) -> dict:
        with self._lock:
            row = self._conn.execute(
                "SELECT payload, run_id FROM records WHERE kind=? AND id=?", (kind, record_id)
            ).fetchone()
        if not row:
            raise KeyError(record_id)
        payload = json.loads(row["payload"])
        payload["runId"] = row["run_id"]
        return payload

    def records(self, run_id: str, kind: str) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT payload FROM records WHERE run_id=? AND kind=? ORDER BY rowid",
                (run_id, kind),
            ).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def save_evidence(self, run_id: str, kind: str, data: bytes, media_type: str, label: str) -> dict:
        evidence_id = new_id("ev")
        suffix = {"image/jpeg": ".jpg", "application/json": ".json", "application/zip": ".zip"}.get(media_type, ".bin")
        relative = f"evidence/{run_id}/{evidence_id}{suffix}"
        path = (self.root / relative).resolve()
        bounded = (self.root / "evidence").resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        if bounded != path and bounded not in path.parents:
            raise ValueError("evidence path escaped the data directory")
        path.write_bytes(data)
        captured = now()
        digest = hashlib.sha256(data).hexdigest()
        with self.transaction():
            self._conn.execute(
                """INSERT INTO evidence(id, run_id, kind, relative_path, sha256, media_type, captured_at, label)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (evidence_id, run_id, kind, relative, digest, media_type, captured, label),
            )
        return {
            "id": evidence_id,
            "runId": run_id,
            "kind": kind,
            "relativePath": relative,
            "sha256": digest,
            "mediaType": media_type,
            "capturedAt": captured,
            "label": label,
            "redactions": [],
        }

    def evidence_list(self, run_id: str) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, kind, media_type, captured_at, label, sha256, relative_path FROM evidence WHERE run_id=? ORDER BY captured_at",
                (run_id,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "kind": row["kind"],
                "mediaType": row["media_type"],
                "capturedAt": row["captured_at"],
                "label": row["label"],
                "sha256": row["sha256"],
                "relativePath": row["relative_path"],
            }
            for row in rows
        ]

    def evidence_file(self, evidence_id: str) -> tuple[Path, str]:
        if not _ID.fullmatch(evidence_id or ""):
            raise KeyError(evidence_id)
        with self._lock:
            row = self._conn.execute(
                "SELECT relative_path, media_type FROM evidence WHERE id=?", (evidence_id,)
            ).fetchone()
        if not row:
            raise KeyError(evidence_id)
        path = (self.root / row["relative_path"]).resolve()
        root = self.root.resolve()
        if root != path and root not in path.parents:
            raise KeyError(evidence_id)
        return path, row["media_type"]

    def save_trace(self, run_id: str, source: Path, label: str) -> dict | None:
        if not source.is_file():
            return None
        data = source.read_bytes()
        try:
            source.unlink()
        except OSError:
            pass
        return self.save_evidence(run_id, "trace", data, "application/zip", label)
