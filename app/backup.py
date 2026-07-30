"""Bazaning .tar.gz zaxirasini tayyorlash.

Zaxira serverning o'zida ham saqlanadi (cron), lekin server yo'qolsa u ham
yo'qoladi. Shuning uchun kunlik nusxa adminlarga Telegram orqali yuboriladi —
bu haqiqiy off-site zaxira bo'ladi.
"""

from __future__ import annotations

import logging
import sqlite3
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BackupArchive:
    path: Path
    filename: str
    size_bytes: int
    record_count: int
    created_at: datetime

    @property
    def size_kb(self) -> int:
        return round(self.size_bytes / 1024)

    def cleanup(self) -> None:
        """Yuborilgandan keyin vaqtinchalik fayllarni o'chiradi."""
        try:
            self.path.unlink(missing_ok=True)
            self.path.parent.rmdir()
        except OSError as error:
            logger.warning("Vaqtinchalik zaxira fayli o'chmadi: %s", error)


def create_archive(db_path: str, created_at: datetime) -> BackupArchive:
    """Bazani xavfsiz nusxalab .tar.gz ga o'raydi.

    sqlite'ning online backup API'si ishlatiladi — bot ayni damda yozayotgan
    bo'lsa ham nusxa yaxlit chiqadi (faylni oddiy copy qilish buni kafolatlamaydi).
    """
    stamp = created_at.strftime("%Y%m%d-%H%M")
    workdir = Path(tempfile.mkdtemp(prefix="vaqtuz-backup-"))
    snapshot = workdir / f"payments-{stamp}.db"

    source = sqlite3.connect(db_path)
    try:
        destination = sqlite3.connect(snapshot)
        try:
            source.backup(destination)
        finally:
            destination.close()
        record_count = source.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
    finally:
        source.close()

    filename = f"vaqtuz-backup-{stamp}.tar.gz"
    archive_path = workdir / filename
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(snapshot, arcname=snapshot.name)
    snapshot.unlink()

    return BackupArchive(
        path=archive_path,
        filename=filename,
        size_bytes=archive_path.stat().st_size,
        record_count=record_count,
        created_at=created_at,
    )


def build_caption(archive: BackupArchive) -> str:
    return (
        f"💾 Kunlik zaxira — {archive.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"Yozuvlar: {archive.record_count} ta\n"
        f"Hajmi: {archive.size_kb} KB\n\n"
        f"Faylni saqlab qo'ying. Ichida `payments.db` — SQLite bazasi."
    )
