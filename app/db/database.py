"""SQLite bilan ishlash qatlami."""

from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator, Sequence

from app.db.models import STATUS_PAID, STATUS_PENDING, PaymentRequest

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    resurs TEXT,
    proyekt TEXT,
    summa_raw TEXT,
    summa_value INTEGER,
    karta TEXT,
    status TEXT DEFAULT 'kutilmoqda',
    requested_by TEXT,
    created_at TEXT NOT NULL,
    paid_at TEXT,
    paid_photo_file_id TEXT,
    actual_summa INTEGER DEFAULT 0,
    komissiya INTEGER DEFAULT 0,
    ai_summa INTEGER,
    ai_izoh TEXT
)
"""

# Eski bazalarda bu ustunlar bo'lmasligi mumkin — xavfsiz qo'shamiz
MIGRATIONS = (
    "ALTER TABLE requests ADD COLUMN actual_summa INTEGER DEFAULT 0",
    "ALTER TABLE requests ADD COLUMN komissiya INTEGER DEFAULT 0",
    "ALTER TABLE requests ADD COLUMN ai_summa INTEGER",
    "ALTER TABLE requests ADD COLUMN ai_izoh TEXT",
)

INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_requests_lookup ON requests (chat_id, message_id)",
    "CREATE INDEX IF NOT EXISTS idx_requests_created_at ON requests (created_at)",
    "CREATE INDEX IF NOT EXISTS idx_requests_status ON requests (status)",
)


class Database:
    def __init__(self, path: str) -> None:
        self.path = path

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init(self) -> None:
        """Jadval va indekslarni yaratadi, eski bazani yangi ustunlar bilan to'ldiradi."""
        directory = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(directory, exist_ok=True)

        with self._connect() as conn:
            conn.execute(SCHEMA)
            for statement in MIGRATIONS:
                try:
                    conn.execute(statement)
                except sqlite3.OperationalError:
                    pass  # ustun allaqachon mavjud
            for statement in INDEXES:
                conn.execute(statement)
        logger.info("Baza tayyor: %s", self.path)

    def add_request(
        self,
        *,
        chat_id: int,
        message_id: int,
        resurs: str,
        proyekt: str,
        summa_raw: str,
        summa_value: int,
        karta: str,
        requested_by: str,
        created_at: datetime,
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO requests (chat_id, message_id, resurs, proyekt, summa_raw,
                                      summa_value, karta, requested_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chat_id,
                    message_id,
                    resurs,
                    proyekt,
                    summa_raw,
                    summa_value,
                    karta,
                    requested_by,
                    created_at.isoformat(),
                ),
            )
            return int(cursor.lastrowid)

    def find_by_message(self, chat_id: int, message_id: int) -> PaymentRequest | None:
        """Reply qilingan xabar bo'yicha so'rovni topadi."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM requests WHERE chat_id = ? AND message_id = ?",
                (chat_id, message_id),
            ).fetchone()
        return PaymentRequest.from_row(row) if row else None

    def get_by_id(self, request_id: int) -> PaymentRequest | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM requests WHERE id = ?", (request_id,)).fetchone()
        return PaymentRequest.from_row(row) if row else None

    def mark_paid(
        self,
        request_id: int,
        photo_file_id: str | None,
        actual_summa: int | None,
        paid_at: datetime,
        ai_summa: int | None = None,
        ai_izoh: str | None = None,
    ) -> int:
        """To'lovni tasdiqlaydi va hisoblangan komissiyani qaytaradi.

        Qayta chaqirilsa oldingi chekni almashtiradi — bitta so'rovga bir necha
        rasm tashlansa, oxirgisi kuchda qoladi.

        actual_summa — komissiya bilan birga haqiqiy o'tkazilgan summa.
        Berilmasa, so'ralgan summaning o'zi ishlatiladi (komissiya = 0).
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT summa_value FROM requests WHERE id = ?", (request_id,)
            ).fetchone()
            requested = (row["summa_value"] or 0) if row else 0

            if actual_summa is None:
                actual_summa = requested
            komissiya = actual_summa - requested

            conn.execute(
                """
                UPDATE requests
                SET status = ?, paid_at = ?, paid_photo_file_id = ?,
                    actual_summa = ?, komissiya = ?, ai_summa = ?, ai_izoh = ?
                WHERE id = ?
                """,
                (
                    STATUS_PAID,
                    paid_at.isoformat(),
                    photo_file_id,
                    actual_summa,
                    komissiya,
                    ai_summa,
                    ai_izoh,
                    request_id,
                ),
            )
        return komissiya

    def get_between(self, start: datetime, end: datetime) -> Sequence[PaymentRequest]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM requests WHERE created_at >= ? AND created_at < ? ORDER BY created_at",
                (start.isoformat(), end.isoformat()),
            ).fetchall()
        return [PaymentRequest.from_row(row) for row in rows]

    def get_pending(self) -> Sequence[PaymentRequest]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM requests WHERE status = ? ORDER BY created_at",
                (STATUS_PENDING,),
            ).fetchall()
        return [PaymentRequest.from_row(row) for row in rows]
