"""Zaxira faylidan bazani tiklash.

Admin botning o'zi yuborgan `.tar.gz` faylni qaytarib forward qiladi yoki
tayyor `.db` faylni yuboradi — shu modul uni tekshirib, joriy bazani
almashtiradi.

Almashtirish qaytarib bo'lmaydigan amal, shuning uchun:
  1) fayl haqiqiy SQLite va bizning tuzilishda ekani tekshiriladi
  2) joriy baza chetga nusxalanadi (pre-restore-...)
  3) almashtirish atomar (os.replace) — yarim yozilgan holat bo'lmaydi
"""

from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Zaxiramiz bir necha KB; bundan kattasi xato fayl degani
MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
REQUIRED_COLUMNS = {"id", "status", "summa_value", "created_at"}


class RestoreError(Exception):
    """Fayl yaroqsiz — baza tegilmadi."""


@dataclass(frozen=True)
class RestoreResult:
    records_before: int
    records_after: int
    paid_after: int
    safety_copy: Path


def _extract_database(payload: bytes, workdir: Path) -> Path:
    """`.tar.gz` ichidan .db ni chiqaradi yoki xom .db ni qabul qiladi."""
    raw = workdir / "yuklangan.bin"
    raw.write_bytes(payload)

    if not tarfile.is_tarfile(raw):
        # Xom .db bo'lishi mumkin — SQLite fayllari shu imzo bilan boshlanadi
        if payload[:16].startswith(b"SQLite format 3"):
            return raw
        raise RestoreError(
            "Fayl tanilmadi. Botning o'zi yuborgan .tar.gz zaxirasini yoki "
            "payments.db faylini yuboring."
        )

    with tarfile.open(raw, "r:gz") as tar:
        members = [m for m in tar.getmembers() if m.isfile() and m.name.endswith(".db")]
        if not members:
            raise RestoreError("Arxiv ichida .db fayli topilmadi.")
        if len(members) > 1:
            raise RestoreError("Arxiv ichida bir nechta .db fayli bor — qaysi biri kerakligi noaniq.")
        target = workdir / "chiqarilgan"
        tar.extract(members[0], target, filter="data")
        return target / members[0].name


def _validate(db_file: Path) -> tuple[int, int]:
    """Bizning tuzilishdagi baza ekanini tekshirib, yozuvlar sonini qaytaradi."""
    try:
        conn = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
    except sqlite3.Error as error:
        raise RestoreError(f"Faylni SQLite sifatida ocholmadim: {error}") from None

    try:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "requests" not in tables:
            raise RestoreError("Bu bizning baza emas — ichida `requests` jadvali yo'q.")

        columns = {row[1] for row in conn.execute("PRAGMA table_info(requests)")}
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise RestoreError(f"Jadvalda kerakli ustunlar yo'q: {', '.join(sorted(missing))}")

        total = conn.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
        paid = conn.execute("SELECT COUNT(*) FROM requests WHERE status = 'tolandi'").fetchone()[0]
    except sqlite3.DatabaseError as error:
        raise RestoreError(f"Fayl buzilgan ko'rinadi: {error}") from None
    finally:
        conn.close()

    return total, paid


def _count_current(db_path: str) -> int:
    if not Path(db_path).exists():
        return 0
    try:
        conn = sqlite3.connect(db_path)
        try:
            return conn.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
        finally:
            conn.close()
    except sqlite3.Error:
        return 0


def restore_from_payload(payload: bytes, db_path: str, now: datetime) -> RestoreResult:
    if len(payload) > MAX_ARCHIVE_BYTES:
        raise RestoreError("Fayl juda katta — zaxira fayli emasga o'xshaydi.")

    records_before = _count_current(db_path)
    workdir = Path(tempfile.mkdtemp(prefix="vaqtuz-restore-"))
    try:
        db_file = _extract_database(payload, workdir)
        records_after, paid_after = _validate(db_file)

        # Joriy bazani chetga olib qo'yamiz — xato tiklashdan qaytish uchun
        target = Path(db_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        safety_copy = target.parent / f"pre-restore-{now.strftime('%Y%m%d-%H%M%S')}.db"
        if target.exists():
            shutil.copy2(target, safety_copy)

        # Bir xil fayl tizimiga ko'chirib, atomar almashtiramiz
        staged = target.parent / f".restore-{now.strftime('%Y%m%d-%H%M%S')}.db"
        shutil.copy2(db_file, staged)
        os.replace(staged, target)

        # WAL/journal qoldiqlari eski bazaga tegishli — ular qolsa baza buziladi
        for suffix in ("-wal", "-shm", "-journal"):
            leftover = Path(str(target) + suffix)
            if leftover.exists():
                leftover.unlink()

        logger.info(
            "Baza tiklandi: %s -> %s yozuv (zaxira: %s)",
            records_before,
            records_after,
            safety_copy.name,
        )
        return RestoreResult(
            records_before=records_before,
            records_after=records_after,
            paid_after=paid_after,
            safety_copy=safety_copy,
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def build_result_text(result: RestoreResult) -> str:
    return (
        "✅ Baza tiklandi.\n\n"
        f"Avval: {result.records_before} yozuv\n"
        f"Hozir: {result.records_after} yozuv ({result.paid_after} tasi to'langan)\n\n"
        f"Eski baza saqlab qo'yildi: {result.safety_copy.name}\n"
        "Xato tiklagan bo'lsangiz shundan qaytarish mumkin."
    )
