"""Admin uchun tugmali menyu.

Buyruqlarni eslab qolish shart emas — shaxsiy chatda tugmalarni bosish yetadi.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.backup import build_caption, create_archive
from app.bot.deps import Deps, get_deps
from app.bot.net import send_with_retry
from app.bot.reporting import compose_report, daily_title, monthly_title, weekly_title
from app.domain.formatting import chunk_text
from app.domain.periods import (
    day_range,
    month_range,
    previous_month_range,
    previous_week_range,
    week_range,
)
from app.domain.reports import build_pending_text
from app.export import build_workbook

logger = logging.getLogger(__name__)

MENU_TEXT = (
    "📊 *To'lov nazorati*\n\n"
    "Kerakli tugmani bosing — hisobot shu yerga keladi.\n"
    "Excel faylini kompyuterda ochib, kanallar va oylar kesimida ko'rishingiz mumkin."
)


def build_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📅 Bugun", callback_data="rep:today"),
                InlineKeyboardButton("🗓 Hafta", callback_data="rep:week"),
                InlineKeyboardButton("📆 Oy", callback_data="rep:month"),
            ],
            [InlineKeyboardButton("⏳ Kutilayotgan to'lovlar", callback_data="rep:pending")],
            [InlineKeyboardButton("— Excel yuklab olish —", callback_data="noop")],
            [
                InlineKeyboardButton("📥 Joriy oy", callback_data="xls:month"),
                InlineKeyboardButton("📥 O'tgan oy", callback_data="xls:prev"),
            ],
            [InlineKeyboardButton("📥 Butun tarix", callback_data="xls:all")],
            [InlineKeyboardButton("💾 Hozir zaxira olish", callback_data="bak:now")],
        ]
    )


async def _send_text(query, deps: Deps, text: str) -> None:
    """Uzun hisobotni bo'laklarga bo'lib yuboradi."""
    for part in chunk_text(text):
        await send_with_retry(
            lambda p=part: query.message.reply_text(p),
            attempts=deps.settings.send_retries,
            description="menyu javobi",
        )


async def _handle_report(query, deps: Deps, action: str) -> None:
    now = datetime.now(deps.settings.timezone)

    if action == "today":
        start, end = day_range(now)
        text = await compose_report(deps, daily_title(now), start, end)
    elif action == "week":
        start, end = week_range(now)
        text = await compose_report(
            deps, weekly_title(start, end), start, end, previous=previous_week_range(now)
        )
    elif action == "month":
        start, end = month_range(now)
        text = await compose_report(
            deps, monthly_title(start), start, end, previous=previous_month_range(now)
        )
    else:  # pending
        text = build_pending_text(deps.db.get_pending())

    await _send_text(query, deps, text)


async def _handle_excel(query, deps: Deps, action: str) -> None:
    now = datetime.now(deps.settings.timezone)

    if action == "month":
        start, end = month_range(now)
        label = f"joriy-oy-{start.strftime('%Y-%m')}"
        title = f"Joriy oy — {start.strftime('%B %Y')}"
    elif action == "prev":
        start, end = previous_month_range(now)
        label = f"otgan-oy-{start.strftime('%Y-%m')}"
        title = f"O'tgan oy — {start.strftime('%B %Y')}"
    else:  # all
        start, end, label, title = None, None, "butun-tarix", "Butun tarix"

    requests = deps.db.get_all() if start is None else deps.db.get_between(start, end)
    if not requests:
        await _send_text(query, deps, "Bu davrda ma'lumot yo'q.")
        return

    content = build_workbook(requests, title)
    filename = f"vaqtuz-{label}.xlsx"
    caption = f"📊 {title}\n{len(requests)} ta so'rov"

    sent = await send_with_retry(
        lambda: query.message.reply_document(
            document=content, filename=filename, caption=caption
        ),
        attempts=deps.settings.send_retries,
        description=f"Excel {label}",
    )
    if sent is None:
        await _send_text(query, deps, "⚠️ Faylni yuborib bo'lmadi, qaytadan urinib ko'ring.")


async def _handle_backup(query, deps: Deps) -> None:
    """Tugma bosilganda shu zahotiyoq zaxira tayyorlab yuboradi.

    Loyihani boshqa serverga ko'chirishda ham shu ishlatiladi — jadvaldagi
    02:00 ni kutish shart emas.
    """
    now = datetime.now(deps.settings.timezone)
    try:
        archive = await asyncio.to_thread(create_archive, deps.settings.db_path, now)
    except Exception:
        logger.exception("Zaxira tayyorlanmadi")
        await _send_text(query, deps, "⚠️ Zaxira tayyorlanmadi. Qaytadan urinib ko'ring.")
        return

    logger.info(
        "Qo'lda zaxira: %s (%s KB, %s yozuv)",
        archive.filename,
        archive.size_kb,
        archive.record_count,
    )
    try:
        sent = await send_with_retry(
            lambda: query.message.reply_document(
                document=archive.path.read_bytes(),
                filename=archive.filename,
                caption=build_caption(archive),
            ),
            attempts=deps.settings.send_retries,
            description="qo'lda zaxira",
        )
        if sent is None:
            await _send_text(query, deps, "⚠️ Faylni yuborib bo'lmadi, qaytadan urinib ko'ring.")
    finally:
        archive.cleanup()


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """`/menu` yoki admin `/start` bosganda chiqadi."""
    message = update.message
    if message is None:
        return
    await send_with_retry(
        lambda: message.reply_text(
            MENU_TEXT, reply_markup=build_menu(), parse_mode="Markdown"
        ),
        attempts=get_deps(context).settings.send_retries,
        description="menyu",
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    deps = get_deps(context)
    query = update.callback_query
    if query is None:
        return

    user = update.effective_user
    if not deps.settings.is_admin(user.id if user else None):
        await query.answer("Bu menyu faqat admin uchun.", show_alert=True)
        return

    data = query.data or ""
    if data == "noop":
        await query.answer()
        return

    kind, _, action = data.partition(":")
    await query.answer("Tayyorlanmoqda…")
    logger.info("Menyu: %s:%s (%s)", kind, action, user.id if user else "-")

    try:
        if kind == "rep":
            await _handle_report(query, deps, action)
        elif kind == "xls":
            await _handle_excel(query, deps, action)
        elif kind == "bak":
            await _handle_backup(query, deps)
    except Exception:
        logger.exception("Menyu buyrug'ida xatolik: %s", data)
        await _send_text(query, deps, "⚠️ Xatolik yuz berdi. Qaytadan urinib ko'ring.")
