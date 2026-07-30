"""Analitika: kanallar va mijozlar bo'yicha kesim, kanal narxlari dinamikasi."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Callable, Sequence

from app.db.models import PaymentRequest
from app.domain.formatting import format_resurs

UNKNOWN = "—"


@dataclass(frozen=True)
class GroupStat:
    key: str
    count: int
    total: int

    @property
    def average(self) -> int:
        return round(self.total / self.count) if self.count else 0


def group_by(
    requests: Sequence[PaymentRequest], key: Callable[[PaymentRequest], str]
) -> list[GroupStat]:
    """Summasi bo'yicha kamayish tartibida guruhlaydi."""
    buckets: dict[str, list[int]] = {}
    for request in requests:
        buckets.setdefault(key(request), []).append(request.summa_value)

    stats = [
        GroupStat(key=name, count=len(values), total=sum(values))
        for name, values in buckets.items()
    ]
    stats.sort(key=lambda stat: (-stat.total, stat.key))
    return stats


def by_project(requests: Sequence[PaymentRequest]) -> list[GroupStat]:
    return group_by(requests, lambda r: r.proyekt or "—")


def by_channel(requests: Sequence[PaymentRequest]) -> list[GroupStat]:
    return group_by(requests, lambda r: format_resurs(r.resurs))


def month_key(request: PaymentRequest) -> str:
    """`2026-07` — saralanadigan va Excel'da tushunarli."""
    created = request.created
    return created.strftime("%Y-%m") if created else UNKNOWN


def week_key(request: PaymentRequest) -> str:
    """Haftaning dushanbasi: `2026-07-27`."""
    created = request.created
    if not created:
        return UNKNOWN
    monday = created.date() - timedelta(days=created.weekday())
    return monday.isoformat()


def week_label(key: str) -> str:
    """`2026-07-27` -> `27.07 - 02.08.2026`."""
    if key == UNKNOWN:
        return key
    from datetime import date

    try:
        monday = date.fromisoformat(key)
    except ValueError:
        return key
    sunday = monday + timedelta(days=6)
    return f"{monday.strftime('%d.%m')} - {sunday.strftime('%d.%m.%Y')}"


def by_month(requests: Sequence[PaymentRequest]) -> list[GroupStat]:
    stats = group_by(requests, month_key)
    stats.sort(key=lambda stat: stat.key)  # vaqt bo'yicha, summa bo'yicha emas
    return stats


def by_week(requests: Sequence[PaymentRequest]) -> list[GroupStat]:
    stats = group_by(requests, week_key)
    stats.sort(key=lambda stat: stat.key)
    return stats


@dataclass(frozen=True)
class ChannelMatrix:
    """Kanallar x oylar jadvali — qaysi kanalga qaysi oyda o'rtacha qancha to'langani."""

    channels: list[str]
    months: list[str]
    averages: dict[tuple[str, str], int]  # (kanal, oy) -> o'rtacha
    counts: dict[tuple[str, str], int]  # (kanal, oy) -> nechta post

    def average(self, channel: str, month: str) -> int | None:
        return self.averages.get((channel, month))

    def count(self, channel: str, month: str) -> int:
        return self.counts.get((channel, month), 0)


def channel_month_matrix(requests: Sequence[PaymentRequest]) -> ChannelMatrix:
    """Kanal narxining oydan-oyga o'zgarishini ko'rsatadigan jadval."""
    buckets: dict[tuple[str, str], list[int]] = {}
    for request in requests:
        key = (format_resurs(request.resurs), month_key(request))
        buckets.setdefault(key, []).append(request.summa_value)

    months = sorted({month for _, month in buckets})
    # Kanallarni jami sarf bo'yicha tartiblaymiz — eng qimmati yuqorida
    totals: dict[str, int] = {}
    for (channel, _), values in buckets.items():
        totals[channel] = totals.get(channel, 0) + sum(values)
    channels = sorted(totals, key=lambda name: (-totals[name], name))

    return ChannelMatrix(
        channels=channels,
        months=months,
        averages={key: round(sum(v) / len(v)) for key, v in buckets.items()},
        counts={key: len(v) for key, v in buckets.items()},
    )


@dataclass(frozen=True)
class PriceChange:
    channel: str
    previous_average: int | None  # None — kanal o'tgan davrda bo'lmagan
    current_average: int

    @property
    def is_new(self) -> bool:
        return self.previous_average is None

    @property
    def ratio(self) -> float:
        """Nisbiy o'zgarish: 0.2 = 20% qimmatlashgan."""
        if not self.previous_average:
            return 0.0
        return (self.current_average - self.previous_average) / self.previous_average


def price_dynamics(
    current: Sequence[PaymentRequest], previous: Sequence[PaymentRequest]
) -> list[PriceChange]:
    """Har bir kanal uchun o'rtacha post narxini o'tgan davr bilan solishtiradi.

    Eng ko'p qimmatlashgan kanal birinchi turadi — muzokara uchun shu kerak.
    """
    previous_avg = {stat.key: stat.average for stat in by_channel(previous)}

    changes = [
        PriceChange(
            channel=stat.key,
            previous_average=previous_avg.get(stat.key),
            current_average=stat.average,
        )
        for stat in by_channel(current)
    ]
    # Avval o'zgarganlar (qimmatlashgani yuqorida), keyin yangi kanallar
    changes.sort(key=lambda change: (change.is_new, -change.ratio, change.channel))
    return changes
