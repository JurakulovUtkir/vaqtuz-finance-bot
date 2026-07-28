from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.db.database import Database
from app.db.models import STATUS_PAID, STATUS_PENDING

TZ = ZoneInfo("Asia/Tashkent")


@pytest.fixture
def db(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    database.init()
    return database


def _add(db, *, summa=60000, proyekt="Garant Bank", message_id=101, created_at=None):
    return db.add_request(
        chat_id=-1001,
        message_id=message_id,
        resurs="t.me/x",
        proyekt=proyekt,
        summa_raw=f"{summa}",
        summa_value=summa,
        karta="8600123412341234",
        requested_by="Tester",
        created_at=created_at or datetime(2026, 7, 28, 10, tzinfo=TZ),
    )


def test_add_and_find(db):
    request_id = _add(db)
    found = db.find_by_message(-1001, 101)
    assert found is not None
    assert found.id == request_id
    assert found.status == STATUS_PENDING
    assert found.summa_value == 60000
    assert found.komissiya == 0


def test_find_returns_none_for_unknown_message(db):
    _add(db)
    assert db.find_by_message(-1001, 999) is None


def test_mark_paid_without_commission(db):
    request_id = _add(db)
    komissiya = db.mark_paid(request_id, "photo1", None, datetime.now(TZ))
    assert komissiya == 0

    found = db.find_by_message(-1001, 101)
    assert found.status == STATUS_PAID
    assert found.is_paid
    assert found.actual_summa == 60000
    assert found.paid_photo_file_id == "photo1"


def test_mark_paid_computes_commission(db):
    request_id = _add(db, summa=60000)
    komissiya = db.mark_paid(request_id, "photo1", 60600, datetime.now(TZ))
    assert komissiya == 600

    found = db.find_by_message(-1001, 101)
    assert found.actual_summa == 60600
    assert found.effective_paid == 60600


def test_get_pending_excludes_paid(db):
    first = _add(db, message_id=101)
    _add(db, message_id=102, summa=5000)
    db.mark_paid(first, "photo", None, datetime.now(TZ))

    pending = db.get_pending()
    assert len(pending) == 1
    assert pending[0].message_id == 102


def test_get_between_filters_by_created_at(db):
    day = datetime(2026, 7, 28, 10, tzinfo=TZ)
    _add(db, message_id=101, created_at=day)
    _add(db, message_id=102, created_at=day + timedelta(days=2))

    start = datetime(2026, 7, 28, 0, tzinfo=TZ)
    rows = db.get_between(start, start + timedelta(days=1))
    assert [r.message_id for r in rows] == [101]


def test_init_is_idempotent(tmp_path):
    path = str(tmp_path / "twice.db")
    Database(path).init()
    database = Database(path)
    database.init()  # migratsiyalar qayta ishlaganda yiqilmasligi kerak
    assert database.get_pending() == []
