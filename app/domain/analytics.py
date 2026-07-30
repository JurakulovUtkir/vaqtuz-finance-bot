"""Analitika: kanallar va mijozlar bo'yicha kesim, kanal narxlari dinamikasi."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from app.db.models import PaymentRequest
from app.domain.formatting import format_resurs


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
