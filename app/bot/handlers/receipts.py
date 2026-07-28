"""Admin chek (rasm) tashlaganda to'lovni tasdiqlash."""

from __future__ import annotations

import logging
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.deps import get_deps
from app.domain.formatting import format_sum
from app.domain.parsing import parse_amount

logger = logging.getLogger(__name__)


async def handle_admin_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    deps = get_deps(context)
    message = update.effective_message
    user = update.effective_user
    if message is None:
        return

    if user is None or user.id != deps.settings.admin_id:
        return  # faqat admin to'lovni tasdiqlay oladi

    if message.reply_to_message is None:
        return  # so'rovga javob tariqasida yuborilmagan

    request = deps.db.find_by_message(message.chat_id, message.reply_to_message.message_id)
    if request is None:
        await message.reply_text(
            "⚠️ Bu rasm qaysi so'rovga tegishli ekanini topa olmadim.\n"
            "Iltimos, ORIGINAL so'rov xabariga (Resurs/Proyekt/Summa/Karta "
            "yozilgan xabarga) to'g'ridan-to'g'ri javob (reply) qilib "
            "chekni yuboring."
        )
        return

    if request.is_paid:
        await message.reply_text(
            f"ℹ️ So'rov #{request.id} allaqachon to'langan deb belgilangan."
        )
        return

    photo_file_id = message.photo[-1].file_id if message.photo else None

    # Rasm izohidagi (caption) raqam — komissiya bilan birga
    # o'tkazilgan HAQIQIY summa deb qabul qilinadi.
    actual_summa = parse_amount(message.caption)

    komissiya = deps.db.mark_paid(
        request_id=request.id,
        photo_file_id=photo_file_id,
        actual_summa=actual_summa,
        paid_at=datetime.now(deps.settings.timezone),
    )
    logger.info("So'rov #%s to'landi, komissiya: %s", request.id, komissiya)

    lines = [
        f"✅ So'rov #{request.id} \"to'landi\" deb belgilandi.",
        f"Proyekt: {request.proyekt} | So'ralgan: {format_sum(request.summa_value)}",
    ]
    if komissiya:
        lines.append(f"Haqiqiy o'tkazilgan: {format_sum(actual_summa or 0)}")
        lines.append(f"Komissiya: {format_sum(komissiya)}")
    await message.reply_text("\n".join(lines))
