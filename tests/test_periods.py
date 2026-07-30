from datetime import datetime
from zoneinfo import ZoneInfo

from app.domain.periods import (
    day_range,
    month_range,
    previous_month_range,
    previous_week_range,
    week_range,
)

TZ = ZoneInfo("Asia/Tashkent")


def _dt(year, month, day, hour=12):
    return datetime(year, month, day, hour, tzinfo=TZ)


def test_day_range():
    start, end = day_range(_dt(2026, 7, 28))
    assert start == _dt(2026, 7, 28, 0)
    assert end == _dt(2026, 7, 29, 0)


def test_week_range_starts_on_monday():
    # 2026-07-28 — seshanba
    start, end = week_range(_dt(2026, 7, 28))
    assert start == _dt(2026, 7, 27, 0)  # dushanba
    assert end == _dt(2026, 8, 3, 0)


def test_week_range_on_sunday_covers_current_week():
    """Haftalik hisobot yakshanba yuboriladi — o'sha kunning o'zi ham kirishi kerak."""
    sunday = _dt(2026, 8, 2, 23)
    start, end = week_range(sunday)
    assert start == _dt(2026, 7, 27, 0)
    assert start <= sunday < end


def test_previous_week_range():
    start, end = previous_week_range(_dt(2026, 7, 28))  # seshanba
    assert start == _dt(2026, 7, 20, 0)  # o'tgan dushanba
    assert end == _dt(2026, 7, 27, 0)  # joriy dushanba


def test_previous_week_is_adjacent_to_current():
    now = _dt(2026, 7, 28)
    prev_start, prev_end = previous_week_range(now)
    cur_start, _ = week_range(now)
    assert prev_end == cur_start


def test_month_range():
    start, end = month_range(_dt(2026, 7, 15))
    assert start == _dt(2026, 7, 1, 0)
    assert end == _dt(2026, 8, 1, 0)


def test_month_range_december_rolls_over():
    start, end = month_range(_dt(2026, 12, 15))
    assert start == _dt(2026, 12, 1, 0)
    assert end == _dt(2027, 1, 1, 0)


def test_previous_month_range():
    start, end = previous_month_range(_dt(2026, 8, 1, 23))
    assert start == _dt(2026, 7, 1, 0)
    assert end == _dt(2026, 8, 1, 0)


def test_previous_month_range_january_rolls_back():
    start, end = previous_month_range(_dt(2026, 1, 1, 23))
    assert start == _dt(2025, 12, 1, 0)
    assert end == _dt(2026, 1, 1, 0)
