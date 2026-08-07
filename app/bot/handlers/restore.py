"""Zaxiradan tiklash: admin faylni yuboradi, bot bazani almashtiradi.

Bu vaqtinchalik imkoniyat — loyihani boshqa serverga ko'chirish uchun.
Ko'chirish tugagach olib tashlanadi.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.deps import get_deps
from app.bot.net import send_with_retry
from app.restore import RestoreError, build_result_text, restore_from_payload

logger = logging.getLogger(__name__)

AWAITING_KEY = "awaiting_restore"

PROMPT_TEXT = (
    "♻️ Zaxiradan tiklash\n\n"
    "Endi zaxira faylini shu chatga yuboring — botning o'zi yuborgan\n"
    "`.tar.gz` faylni forward qilsangiz ham bo'ladi, `payments.db` ni\n"
    "to'g'ridan-to'g'ri yuborsangiz ham.\n\n"
    "⚠️ Joriy baza almashtiriladi. Almashtirishdan oldin uning nusxasi\n"
    "saqlab qo'yiladi.\n\n"
    "Bekor qilish uchun /bekor yozing."
)

CANCELLED_TEXT = "Bekor qilindi. Baza tegilmadi."
NOT_WAITING_TEXT = (
    "Faylni qabul qilishim uchun avval menyudan "
    "«♻️ Zaxiradan tiklash» tugmasini bosing."
)


async def _reply(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    message = update.message
    if message is None:
        return
    await send_with_retry(
        lambda: message.reply_text(text),
        attempts=get_deps(context).settings.send_retries,
        description="tiklash javobi",
    )


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data is not None:
        context.user_data.pop(AWAITING_KEY, None)
    await _reply(update, context, CANCELLED_TEXT)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    deps = get_deps(context)
    message = update.message
    user = update.effective_user
    if message is None or message.document is None:
        return

    if not deps.settings.is_admin(user.id if user else None):
        return

    if not (context.user_data or {}).get(AWAITING_KEY):
        await _reply(update, context, NOT_WAITING_TEXT)
        return

    # Bayroqni darrov tushiramiz — ikkinchi fayl tasodifan qayta tiklab yubormasin
    context.user_data.pop(AWAITING_KEY, None)

    await _reply(update, context, "Fayl olindi, tekshiryapman…")

    try:
        telegram_file = await message.document.get_file()
        payload = bytes(await telegram_file.download_as_bytearray())
    except Exception as error:  # noqa: BLE001 - yuklab bo'lmasa baza tegilmaydi
        logger.warning("Zaxira faylini yuklab bo'lmadi: %s", error)
        await _reply(update, context, "⚠️ Faylni yuklab bo'lmadi. Qaytadan urinib ko'ring.")
        return

    try:
        result = await asyncio.to_thread(
            restore_from_payload,
            payload,
            deps.settings.db_path,
            datetime.now(deps.settings.timezone),
        )
    except RestoreError as error:
        logger.info("Tiklash rad etildi: %s", error)
        await _reply(update, context, f"❌ {error}\n\nBaza o'zgarmadi.")
        return
    except Exception:
        logger.exception("Tiklashda kutilmagan xatolik")
        await _reply(update, context, "❌ Tiklashda xatolik yuz berdi. Baza o'zgarmagan bo'lishi mumkin.")
        return

    logger.info(
        "Bazani %s tikladi: %s -> %s yozuv",
        user.full_name if user else "?",
        result.records_before,
        result.records_after,
    )
    await _reply(update, context, build_result_text(result))
