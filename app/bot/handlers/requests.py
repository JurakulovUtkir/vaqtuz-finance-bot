"""Guruhdagi to'lov so'rovlarini qabul qilish."""

from __future__ import annotations

import logging
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.deps import get_deps
from app.domain.formatting import format_sum
from app.domain.parsing import parse_request

logger = logging.getLogger(__name__)


async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    deps = get_deps(context)
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return

    if deps.settings.group_chat_id and str(chat.id) != deps.settings.group_chat_id:
        return  # faqat belgilangan guruhni tinglaymiz

    parsed = parse_request(message.text)
    if parsed is None:
        return  # bu xabar so'rov formatida emas

    requested_by = message.from_user.full_name if message.from_user else "noma'lum"

    request_id = deps.db.add_request(
        chat_id=chat.id,
        message_id=message.message_id,
        resurs=parsed.resurs,
        proyekt=parsed.proyekt,
        summa_raw=parsed.summa_raw,
        summa_value=parsed.summa_value,
        karta=parsed.karta,
        requested_by=requested_by,
        created_at=datetime.now(deps.settings.timezone),
    )
    # chat_id ham yoziladi — GROUP_CHAT_ID ni shu log'dan olib .env ga qo'yasiz
    logger.info(
        "Yangi so'rov #%s: %s — %s (%s) | chat_id=%s",
        request_id,
        parsed.proyekt,
        parsed.summa_value,
        requested_by,
        chat.id,
    )

    await message.reply_text(
        f"✅ So'rov qabul qilindi (#{request_id})\n"
        f"Proyekt: {parsed.proyekt}\n"
        f"Summa: {format_sum(parsed.summa_value)}\n"
        f"Karta: {parsed.karta}\n\n"
        f"To'lov amalga oshirilgach, shu xabarga javob (reply) qilib "
        f"chekni rasm sifatida tashlang.\n"
        f"Agar komissiya yechilgan bo'lsa, rasmning izohiga (caption) "
        f"haqiqiy o'tkazilgan summani yozing (masalan: 606000)."
    )
