"""Belgilangan vaqtda avtomatik yuboriladigan hisobotlar."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from telegram.ext import Application, ContextTypes

from app.backup import build_caption, create_archive
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
    """Hisobotni barcha qabul qiluvchilarga yuboradi; biri yiqilsa qolganiga davom etadi."""
    deps = get_deps(context)
    for chat_id in deps.settings.report_chat_ids:
        sent = await send_with_retry(
            lambda cid=chat_id: context.bot.send_message(chat_id=cid, text=text),
            attempts=deps.settings.send_retries,
            description=f"{label} -> {chat_id}",
        )
        if sent is None:
            logger.error("%s %s ga yuborilmadi", label, chat_id)


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


async def send_backup(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bazani .tar.gz qilib barcha adminlarga yuboradi.

    Serverdagi cron zaxirasi serverning o'zida yotadi — server yo'qolsa u ham
    yo'qoladi. Telegram orqali yuborilgani esa off-site nusxa bo'ladi.
    """
    deps = get_deps(context)
    now = datetime.now(deps.settings.timezone)

    try:
        archive = await asyncio.to_thread(create_archive, deps.settings.db_path, now)
    except Exception:
        logger.exception("Zaxira tayyorlanmadi")
        return

    logger.info(
        "Zaxira tayyor: %s (%s KB, %s yozuv)",
        archive.filename,
        archive.size_kb,
        archive.record_count,
    )
    caption = build_caption(archive)
    content = archive.path.read_bytes()

    delivered = 0
    for admin_id in deps.settings.admin_ids:
        sent = await send_with_retry(
            lambda aid=admin_id: context.bot.send_document(
                chat_id=aid,
                document=content,
                filename=archive.filename,
                caption=caption,
            ),
            attempts=deps.settings.send_retries,
            description=f"zaxira -> {admin_id}",
        )
        if sent is None:
            logger.error("Zaxira %s ga yetkazilmadi", admin_id)
        else:
            delivered += 1

    archive.cleanup()
    logger.info("Zaxira %s/%s adminga yuborildi", delivered, len(deps.settings.admin_ids))


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
    job_queue.run_daily(send_backup, time=settings.backup_time, name="backup")
    logger.info(
        "Jadval: kunlik %s, haftalik %s (yakshanba), oylik tekshiruv %s, zaxira %s",
        settings.daily_report_time.strftime("%H:%M"),
        settings.weekly_report_time.strftime("%H:%M"),
        settings.monthly_check_time.strftime("%H:%M"),
        settings.backup_time.strftime("%H:%M"),
    )
    logger.info(
        "Adminlar: %s | hisobot manzili: %s",
        ", ".join(str(i) for i in settings.admin_ids),
        ", ".join(str(i) for i in settings.report_chat_ids),
    )
