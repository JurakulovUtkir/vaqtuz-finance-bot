"""Hisobot davrlarini hisoblash.

Barcha funksiyalar [start, end) oralig'ini qaytaradi va `now` ning
vaqt zonasini saqlab qoladi.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from datetime import time as dtime


def _start_of_day(day: date, tz) -> datetime:
    return datetime.combine(day, dtime.min, tzinfo=tz)


def day_range(now: datetime) -> tuple[datetime, datetime]:
    start = _start_of_day(now.date(), now.tzinfo)
    return start, start + timedelta(days=1)


def week_range(now: datetime) -> tuple[datetime, datetime]:
    """Dushanbadan yakshanbagacha bo'lgan joriy hafta."""
    monday = now.date() - timedelta(days=now.weekday())
    start = _start_of_day(monday, now.tzinfo)
    return start, start + timedelta(days=7)


def previous_week_range(now: datetime) -> tuple[datetime, datetime]:
    """O'tgan hafta — narx dinamikasini solishtirish uchun."""
    start, end = week_range(now)
    return start - timedelta(days=7), start


def month_range(now: datetime) -> tuple[datetime, datetime]:
    """Joriy oy."""
    first = now.date().replace(day=1)
    start = _start_of_day(first, now.tzinfo)
    if first.month == 12:
        next_first = first.replace(year=first.year + 1, month=1)
    else:
        next_first = first.replace(month=first.month + 1)
    return start, _start_of_day(next_first, now.tzinfo)


def previous_month_range(now: datetime) -> tuple[datetime, datetime]:
    """O'tgan oy — oylik hisobot har oyning 1-sanasida shuning uchun yuboriladi."""
    first_of_this_month = now.date().replace(day=1)
    last_day_prev_month = first_of_this_month - timedelta(days=1)
    start = _start_of_day(last_day_prev_month.replace(day=1), now.tzinfo)
    return start, _start_of_day(first_of_this_month, now.tzinfo)
