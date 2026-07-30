import tarfile
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.backup import build_caption, create_archive
from app.db.database import Database

TZ = ZoneInfo("Asia/Tashkent")
NOW = datetime(2026, 7, 31, 2, 0, tzinfo=TZ)


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "payments.db")
    db = Database(path)
    db.init()
    for i in range(3):
        db.add_request(
            chat_id=-1,
            message_id=i,
            resurs="https://t.me/kanal",
            proyekt="Test",
            summa_raw="1000",
            summa_value=1000,
            karta="8600",
            requested_by="Tester",
            created_at=NOW,
        )
    return path


def test_archive_is_a_valid_targz(db_path):
    archive = create_archive(db_path, NOW)
    try:
        assert archive.filename == "vaqtuz-backup-20260731-0200.tar.gz"
        assert archive.path.exists()
        assert tarfile.is_tarfile(archive.path)
        with tarfile.open(archive.path, "r:gz") as tar:
            names = tar.getnames()
        assert names == ["payments-20260731-0200.db"]
    finally:
        archive.cleanup()


def test_archive_reports_record_count(db_path):
    archive = create_archive(db_path, NOW)
    try:
        assert archive.record_count == 3
        assert archive.size_bytes > 0
    finally:
        archive.cleanup()


def test_archive_content_is_a_usable_database(db_path, tmp_path):
    """Zaxira ochilganda haqiqiy, o'qiladigan baza chiqishi kerak."""
    archive = create_archive(db_path, NOW)
    try:
        with tarfile.open(archive.path, "r:gz") as tar:
            tar.extractall(tmp_path / "restored", filter="data")
        restored = Database(str(tmp_path / "restored" / "payments-20260731-0200.db"))
        assert len(restored.get_all()) == 3
    finally:
        archive.cleanup()


def test_cleanup_removes_temp_files(db_path):
    archive = create_archive(db_path, NOW)
    workdir = archive.path.parent
    archive.cleanup()
    assert not archive.path.exists()
    assert not workdir.exists()


def test_caption_mentions_counts_and_size(db_path):
    archive = create_archive(db_path, NOW)
    try:
        caption = build_caption(archive)
        assert "31.07.2026 02:00" in caption
        assert "3 ta" in caption
        assert "KB" in caption
    finally:
        archive.cleanup()
