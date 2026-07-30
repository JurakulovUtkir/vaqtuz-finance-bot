"""Qo'lda chaqiriladigan buyruqlar. Hisobot buyruqlari faqat admin uchun."""

from __future__ import annotations

import logging
from datetime import datetime
from functools import wraps
from typing import Awaitable, Callable

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.deps import get_deps
from app.bot.handlers.menu import show_menu
from app.bot.net import send_with_retry
from app.bot.reporting import compose_report, daily_title, monthly_title, weekly_title
from app.domain.formatting import format_resurs, format_sum
from app.domain.periods import (
    day_range,
    month_range,
    previous_month_range,
    previous_week_range,
    week_range,
)
from app.domain.reports import build_pending_text

logger = logging.getLogger(__name__)

Handler = Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]

START_TEXT = (
    "🤖 To'lov nazorati boti.\n\n"
    "Guruhda quyidagi formatdagi xabarlarni kuzataman:\n"
    "Resurs: ...\nProyekt: ...\nSumma: ...\nKarta: ...\n\n"
    "So'rovni ko'rganimda 👀 qo'yaman, to'lov tasdiqlangach 👌 ga almashtiraman.\n\n"
    "Hisobot buyruqlari faqat admin uchun ishlaydi."
)

DENIED_TEXT = "⛔️ Bu buyruq faqat admin uchun."

COMMANDS = (
    ("menu", "Tugmali menyu"),
    ("bugun", "Bugungi hisobot"),
    ("hafta", "Shu haftalik hisobot"),
    ("oy", "Shu oylik hisobot"),
    ("kutilmoqda", "Hali to'lanmagan so'rovlar"),
    ("chek", "Chek rasmini qayta ko'rsatish: /chek 14"),
)


async def _reply(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    message = update.message
    if message is None:
        return
    await send_with_retry(
        lambda: message.reply_text(text),
        attempts=get_deps(context).settings.send_retries,
        description="buyruqqa javob",
    )


def admin_only(handler: Handler) -> Handler:
    """Faqat .env dagi ADMIN_ID buyruqni bajara oladi."""

    @wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        deps = get_deps(context)
        user = update.effective_user
        if not deps.settings.is_admin(user.id if user else None):
            logger.info(
                "Ruxsatsiz buyruq: %s (id=%s)",
                user.full_name if user else "noma'lum",
                user.id if user else "-",
            )
            await _reply(update, context, DENIED_TEXT)
            return
        await handler(update, context)

    return wrapper


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin bo'lsa tugmali menyu, aks holda qisqa tanishtiruv."""
    deps = get_deps(context)
    user = update.effective_user
    if deps.settings.is_admin(user.id if user else None):
        await show_menu(update, context)
        return
    await _reply(update, context, START_TEXT)


@admin_only
async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await show_menu(update, context)


@admin_only
async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    deps = get_deps(context)
    now = datetime.now(deps.settings.timezone)
    start, end = day_range(now)
    await _reply(update, context, await compose_report(deps, daily_title(now), start, end))


@admin_only
async def cmd_week(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    deps = get_deps(context)
    now = datetime.now(deps.settings.timezone)
    start, end = week_range(now)
    text = await compose_report(
        deps, weekly_title(start, end), start, end, previous=previous_week_range(now)
    )
    await _reply(update, context, text)


@admin_only
async def cmd_month(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    deps = get_deps(context)
    now = datetime.now(deps.settings.timezone)
    start, end = month_range(now)
    text = await compose_report(
        deps, monthly_title(start), start, end, previous=previous_month_range(now)
    )
    await _reply(update, context, text)


@admin_only
async def cmd_pending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    deps = get_deps(context)
    await _reply(update, context, build_pending_text(deps.db.get_pending()))


@admin_only
async def cmd_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """`/chek 14` — o'sha so'rovning chek rasmini qayta yuboradi.

    Guruh supergroup emas, shuning uchun xabarga to'g'ridan-to'g'ri havola
    yasab bo'lmaydi — rasmni qaytadan yuborish shu muammoni yopadi.
    """
    deps = get_deps(context)
    message = update.message
    if message is None:
        return

    args = context.args or []
    if not args or not args[0].lstrip("#").isdigit():
        await _reply(update, context, "Ishlatish: /chek 14")
        return

    request = deps.db.get_by_id(int(args[0].lstrip("#")))
    if request is None:
        await _reply(update, context, f"So'rov #{args[0]} topilmadi.")
        return
    if not request.paid_photo_file_id:
        await _reply(update, context, f"#{request.id} uchun chek rasmi saqlanmagan.")
        return

    caption = (
        f"🧾 #{request.id} — {request.proyekt}\n"
        f"{format_resurs(request.resurs)}\n"
        f"So'ralgan: {format_sum(request.summa_value)}\n"
        f"O'tkazilgan: {format_sum(request.effective_paid)}"
    )
    await send_with_retry(
        lambda: message.reply_photo(request.paid_photo_file_id, caption=caption),
        attempts=deps.settings.send_retries,
        description=f"#{request.id} chek rasmi",
    )
