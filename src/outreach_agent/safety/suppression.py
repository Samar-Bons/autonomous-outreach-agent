# ABOUTME: Suppression stores: the append-only do-not-send list behind the SuppressionStore type.
# ABOUTME: An in-memory store for tests and a sqlite-backed store for durable, persistent state.
from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import datetime

from ..domain import SuppressionEntry, normalize_email
from ..domain.enums import SuppressionReason

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS suppressions (
    email TEXT NOT NULL,
    reason TEXT NOT NULL,
    source TEXT NOT NULL,
    added_at TEXT NOT NULL
)
"""


class InMemorySuppressionStore:
    """List-backed, append-only suppression store implementing ``SuppressionStore``.

    Emails are normalized on insert and on query so case and surrounding
    whitespace never let a suppressed address slip through.
    """

    def __init__(self) -> None:
        self._entries: list[SuppressionEntry] = []

    def is_suppressed(self, email: str) -> bool:
        target = normalize_email(email)
        return any(normalize_email(e.email) == target for e in self._entries)

    def add(self, entry: SuppressionEntry) -> None:
        self._entries.append(entry)

    def all(self) -> Sequence[SuppressionEntry]:
        return list(self._entries)


class SqliteSuppressionStore:
    """Sqlite-backed, append-only suppression store implementing ``SuppressionStore``.

    Opens a persistent connection at ``db_path`` (use ``:memory:`` for tests) and
    creates the table if it does not exist. Emails are normalized consistently on
    insert and query so suppression decisions are immune to case/whitespace.
    """

    def __init__(self, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(_CREATE_TABLE)
        self._conn.commit()

    def is_suppressed(self, email: str) -> bool:
        target = normalize_email(email)
        cur = self._conn.execute("SELECT 1 FROM suppressions WHERE email = ? LIMIT 1", (target,))
        return cur.fetchone() is not None

    def add(self, entry: SuppressionEntry) -> None:
        self._conn.execute(
            "INSERT INTO suppressions (email, reason, source, added_at) VALUES (?, ?, ?, ?)",
            (
                normalize_email(entry.email),
                entry.reason.value,
                entry.source,
                entry.added_at.isoformat(),
            ),
        )
        self._conn.commit()

    def all(self) -> Sequence[SuppressionEntry]:
        cur = self._conn.execute("SELECT email, reason, source, added_at FROM suppressions")
        return [
            SuppressionEntry(
                email=email,
                reason=SuppressionReason(reason),
                source=source,
                added_at=datetime.fromisoformat(added_at),
            )
            for email, reason, source, added_at in cur.fetchall()
        ]

    def close(self) -> None:
        self._conn.close()
