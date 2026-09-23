from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


JST = timezone(timedelta(hours=9))


class Storage:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS stream_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    stream_url TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS execution_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message TEXT NOT NULL,
                    executed_at TEXT NOT NULL
                );
                """
            )

    def get_stream_url(self) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT stream_url FROM stream_state WHERE id = 1"
            ).fetchone()
        return row[0] if row else None

    def save_stream_url(self, stream_url: str, now: datetime | None = None) -> None:
        timestamp = _timestamp(now)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO stream_state (id, stream_url, updated_at)
                VALUES (1, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    stream_url = excluded.stream_url,
                    updated_at = excluded.updated_at
                """,
                (stream_url, timestamp),
            )

    def save_log(self, message: str, now: datetime | None = None) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO execution_logs (message, executed_at) VALUES (?, ?)",
                (message, _timestamp(now)),
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection


def _timestamp(now: datetime | None) -> str:
    return (now or datetime.now(JST)).isoformat(timespec="seconds")
