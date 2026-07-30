"""Belgilangan vaqtda avtomatik yuboriladigan hisobotlar."""

from __future__ import annotations

import logging
from datetime import datetime

from telegram.ext import Application, ContextTypes

from app.bot.deps import get_deps
from app.bot.net import send_with_retry
from app.bot.reporting import compose_report, daily_title, monthly_title, weekly_title
from app.config import WEEKLY_REPORT_WEEKDAY, Settings
from app.domain.periods import (
    day_range,
    previous_month_range,
    previous_week_range,
    week_range,
)

logger = logging.getLogger(__name__)


async def _deliver(context: ContextTypes.DEFAULT_TYPE, text: str, label: str) -> None:
    deps = get_deps(context)
    sent = await send_with_retry(
        lambda: context.bot.send_message(chat_id=deps.settings.report_chat_id, text=text),
        attempts=deps.settings.send_retries,
        description=label,
    )
    if sent is None:
        logger.error("%s yuborilmadi — tarmoq muammosi", label)


async def send_daily_report(context: ContextTypes.DEFAULT_TYPE) -> None:
    deps = get_deps(context)
    now = datetime.now(deps.settings.timezone)
    start, end = day_range(now)
    text = await compose_report(deps, daily_title(now), start, end)
    await _deliver(context, text, "Kunlik hisobot")


async def send_weekly_report(context: ContextTypes.DEFAULT_TYPE) -> None:
    deps = get_deps(context)
    now = datetime.now(deps.settings.timezone)
    start, end = week_range(now)
    text = await compose_report(
        deps, weekly_title(start, end), start, end, previous=previous_week_range(now)
    )
    await _deliver(context, text, "Haftalik hisobot")


async def send_monthly_report_if_due(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Har kuni ishlaydi, lekin faqat oyning 1-sanasida o'tgan oy hisobotini yuboradi."""
    deps = get_deps(context)
    now = datetime.now(deps.settings.timezone)
    if now.day != 1:
        return
    start, end = previous_month_range(now)
    # O'tgan oyni undan ham oldingi oy bilan solishtiramiz
    previous = previous_month_range(start.replace(day=1))
    text = await compose_report(deps, monthly_title(start), start, end, previous=previous)
    await _deliver(context, text, "Oylik hisobot")


def register_jobs(application: Application, settings: Settings) -> None:
    job_queue = application.job_queue
    if job_queue is None:
        raise RuntimeError(
            "JobQueue mavjud emas. `python-telegram-bot[job-queue]` o'rnatilganini tekshiring."
        )

    job_queue.run_daily(send_daily_report, time=settings.daily_report_time, name="daily_report")
    job_queue.run_daily(
        send_weekly_report,
        time=settings.weekly_report_time,
        days=(WEEKLY_REPORT_WEEKDAY,),
        name="weekly_report",
    )
    job_queue.run_daily(
        send_monthly_report_if_due,
        time=settings.monthly_check_time,
        name="monthly_report_check",
    )
    logger.info(
        "Hisobot jadvali: kunlik %s, haftalik %s (yakshanba), oylik tekshiruv %s",
        settings.daily_report_time.strftime("%H:%M"),
        settings.weekly_report_time.strftime("%H:%M"),
        settings.monthly_check_time.strftime("%H:%M"),
    )
