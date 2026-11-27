from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


ACTIVE_STATUSES = ("queued", "running")


class JobDatabase:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    dedupe_key TEXT,
                    status TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    progress INTEGER NOT NULL DEFAULT 0,
                    message TEXT NOT NULL DEFAULT '',
                    url TEXT NOT NULL,
                    instruction TEXT NOT NULL,
                    settings_json TEXT NOT NULL,
                    source_path TEXT,
                    transcript_path TEXT,
                    clips_json TEXT NOT NULL DEFAULT '[]',
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS jobs_created_idx ON jobs(created_at DESC)"
            )

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def create_job(self, job: dict[str, Any]) -> bool:
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT id FROM jobs WHERE dedupe_key = ? AND status IN ('queued', 'running')",
                (job["dedupe_key"],),
            ).fetchone()
            if existing:
                return False
            now = self.now()
            connection.execute(
                """
                INSERT INTO jobs (
                    id, dedupe_key, status, stage, progress, message, url,
                    instruction, settings_json, created_at, updated_at
                ) VALUES (?, ?, 'queued', 'queued', 0, 'Waiting to start', ?, ?, ?, ?, ?)
                """,
                (
                    job["id"],
                    job["dedupe_key"],
                    job["url"],
                    job["instruction"],
                    json.dumps(job["settings"]),
                    now,
                    now,
                ),
            )
        return True

    def update(self, job_id: str, **values: Any) -> None:
        values["updated_at"] = self.now()
        assignments = ", ".join(f"{key} = ?" for key in values)
        with self.connect() as connection:
            connection.execute(
                f"UPDATE jobs SET {assignments} WHERE id = ?",
                (*values.values(), job_id),
            )

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return self._decode(row) if row else None

    def get_active_by_dedupe_key(self, dedupe_key: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM jobs
                WHERE dedupe_key = ? AND status IN ('queued', 'running')
                ORDER BY created_at DESC LIMIT 1
                """,
                (dedupe_key,),
            ).fetchone()
        return self._decode(row) if row else None

    def list_jobs(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._decode(row) for row in rows]

    @staticmethod
    def _decode(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["settings"] = json.loads(item.pop("settings_json"))
        item["clips"] = json.loads(item.pop("clips_json"))
        return item
