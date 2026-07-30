"""Hisobotni bazadan yig'ib, AI izohi bilan to'ldirish.

Buyruqlar ham, avtomatik job'lar ham shu yerdan foydalanadi.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.bot.deps import Deps
from app.domain.reports import build_report_text


async def compose_report(
    deps: Deps,
    title: str,
    start: datetime,
    end: datetime,
    previous: tuple[datetime, datetime] | None = None,
) -> str:
    """`previous` berilsa, kanal narxlari o'sha davr bilan solishtiriladi."""
    requests = deps.db.get_between(start, end)
    previous_requests = deps.db.get_between(*previous) if previous else None

    text = build_report_text(title, requests, previous_requests)
    insight = await deps.insight.analyse(text)
    if insight:
        text += f"\n\n🤖 AI tahlili:\n{insight}"
    return text


def daily_title(now: datetime) -> str:
    return f"Kunlik hisobot — {now.strftime('%d.%m.%Y')}"


def weekly_title(start: datetime, end: datetime) -> str:
    last_day = end.date() - timedelta(days=1)
    return f"Haftalik hisobot — {start.strftime('%d.%m')} dan {last_day.strftime('%d.%m.%Y')} gacha"


def monthly_title(start: datetime) -> str:
    return f"Oylik hisobot — {start.strftime('%B %Y')}"
