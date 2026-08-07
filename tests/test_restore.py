import io
import sqlite3
import tarfile
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.backup import create_archive
from app.db.database import Database
from app.restore import RestoreError, build_result_text, restore_from_payload

TZ = ZoneInfo("Asia/Tashkent")
NOW = datetime(2026, 8, 7, 22, 30, tzinfo=TZ)


def _make_db(path, count, paid=0):
    db = Database(str(path))
    db.init()
    for i in range(count):
        rid = db.add_request(
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
        if i < paid:
            db.mark_paid(rid, "photo", 1000, NOW)
    return db


@pytest.fixture
def live_db(tmp_path):
    """Ishlab turgan baza — 3 yozuv."""
    path = tmp_path / "live" / "payments.db"
    path.parent.mkdir()
    _make_db(path, 3)
    return path


def _archive_of(tmp_path, count, paid=0) -> bytes:
    source = tmp_path / "source" / "payments.db"
    source.parent.mkdir(exist_ok=True)
    _make_db(source, count, paid)
    archive = create_archive(str(source), NOW)
    try:
        return archive.path.read_bytes()
    finally:
        archive.cleanup()


def test_restores_from_targz(tmp_path, live_db):
    payload = _archive_of(tmp_path, 31, paid=13)
    result = restore_from_payload(payload, str(live_db), NOW)

    assert result.records_before == 3
    assert result.records_after == 31
    assert result.paid_after == 13
    assert len(Database(str(live_db)).get_all()) == 31


def test_restores_from_raw_db_file(tmp_path, live_db):
    """Admin .db faylni to'g'ridan-to'g'ri yuborsa ham ishlashi kerak."""
    source = tmp_path / "raw" / "payments.db"
    source.parent.mkdir()
    _make_db(source, 7)

    result = restore_from_payload(source.read_bytes(), str(live_db), NOW)
    assert result.records_after == 7


def test_keeps_safety_copy_of_previous_database(tmp_path, live_db):
    result = restore_from_payload(_archive_of(tmp_path, 10), str(live_db), NOW)

    assert result.safety_copy.exists()
    assert result.safety_copy.name.startswith("pre-restore-")
    # Eski nusxa hali ham 3 yozuvli bo'lishi kerak
    assert len(Database(str(result.safety_copy)).get_all()) == 3


def test_rejects_garbage_without_touching_database(live_db):
    with pytest.raises(RestoreError, match="Fayl tanilmadi"):
        restore_from_payload(b"bu zaxira emas", str(live_db), NOW)
    assert len(Database(str(live_db)).get_all()) == 3


def test_rejects_foreign_sqlite(tmp_path, live_db):
    """Boshqa loyihaning bazasi — `requests` jadvali yo'q."""
    foreign = tmp_path / "foreign.db"
    conn = sqlite3.connect(foreign)
    conn.execute("CREATE TABLE users (id INTEGER)")
    conn.commit()
    conn.close()

    with pytest.raises(RestoreError, match="requests"):
        restore_from_payload(foreign.read_bytes(), str(live_db), NOW)
    assert len(Database(str(live_db)).get_all()) == 3


def test_rejects_table_missing_columns(tmp_path, live_db):
    broken = tmp_path / "broken.db"
    conn = sqlite3.connect(broken)
    conn.execute("CREATE TABLE requests (id INTEGER, boshqa TEXT)")
    conn.commit()
    conn.close()

    with pytest.raises(RestoreError, match="ustunlar yo'q"):
        restore_from_payload(broken.read_bytes(), str(live_db), NOW)
    assert len(Database(str(live_db)).get_all()) == 3


def test_rejects_archive_without_db(tmp_path, live_db):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        info = tarfile.TarInfo("readme.txt")
        data = b"salom"
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))

    with pytest.raises(RestoreError, match=".db fayli topilmadi"):
        restore_from_payload(buffer.getvalue(), str(live_db), NOW)
    assert len(Database(str(live_db)).get_all()) == 3


def test_rejects_oversized_payload(live_db):
    with pytest.raises(RestoreError, match="juda katta"):
        restore_from_payload(b"x" * (51 * 1024 * 1024), str(live_db), NOW)


def test_works_when_no_database_exists_yet(tmp_path):
    """Yangi serverda baza hali yo'q bo'lishi mumkin."""
    target = tmp_path / "yangi" / "payments.db"
    result = restore_from_payload(_archive_of(tmp_path, 5), str(target), NOW)

    assert result.records_before == 0
    assert result.records_after == 5
    assert target.exists()


def test_restored_database_is_writable(tmp_path, live_db):
    """Tiklangandan keyin bot ishlashda davom eta olishi kerak."""
    restore_from_payload(_archive_of(tmp_path, 4), str(live_db), NOW)

    db = Database(str(live_db))
    db.add_request(
        chat_id=-1,
        message_id=999,
        resurs="https://t.me/yangi",
        proyekt="Yangi",
        summa_raw="5000",
        summa_value=5000,
        karta="8600",
        requested_by="Tester",
        created_at=NOW,
    )
    assert len(db.get_all()) == 5


def test_result_text_mentions_counts(tmp_path, live_db):
    result = restore_from_payload(_archive_of(tmp_path, 31, paid=13), str(live_db), NOW)
    text = build_result_text(result)
    assert "Avval: 3 yozuv" in text
    assert "Hozir: 31 yozuv (13 tasi to'langan)" in text
    assert "pre-restore-" in text
