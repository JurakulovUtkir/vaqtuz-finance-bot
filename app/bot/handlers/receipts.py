"""Admin chek (rasm) tashlaganda to'lovni tasdiqlash."""

from __future__ import annotations

import logging
from datetime import datetime

from telegram import Message, Update
from telegram.ext import ContextTypes

from app.ai.vision import ReceiptData
from app.bot.deps import Deps, get_deps
from app.bot.net import send_with_retry
from app.domain.parsing import parse_amount
from app.domain.reconciliation import Source, build_confirmation_text

logger = logging.getLogger(__name__)


async def _read_receipt(deps: Deps, message: Message) -> ReceiptData | None:
    """Chek rasmini yuklab olib AI'ga o'qitadi. Xatolikda None."""
    if not deps.receipt_reader.enabled or not message.photo:
        return None
    try:
        photo_file = await message.photo[-1].get_file()
        image_bytes = bytes(await photo_file.download_as_bytearray())
    except Exception as error:  # noqa: BLE001 - rasm yuklanmasa qo'lda kiritish qoladi
        logger.warning("Chek rasmini yuklab bo'lmadi: %s", error)
        return None
    return await deps.receipt_reader.read(image_bytes)


async def handle_admin_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    deps = get_deps(context)
    message = update.effective_message
    user = update.effective_user
    if message is None:
        return

    if not deps.settings.is_admin(user.id if user else None):
        return  # faqat adminlar to'lovni tasdiqlay oladi

    replied = message.reply_to_message
    if replied is None:
        return  # so'rovga javob tariqasida yuborilmagan

    request = deps.db.find_by_message(message.chat_id, replied.message_id)
    if request is None:
        await send_with_retry(
            lambda: message.reply_text(
                "⚠️ Bu rasm qaysi so'rovga tegishli ekanini topa olmadim.\n"
                "Iltimos, ORIGINAL so'rov xabariga (Resurs/Proyekt/Summa/Karta "
                "yozilgan xabarga) to'g'ridan-to'g'ri javob (reply) qilib "
                "chekni yuboring."
            ),
            attempts=deps.settings.send_retries,
            description="so'rov topilmadi xabari",
        )
        return

    was_paid = request.is_paid  # qayta tashlansa oldingi chek almashtiriladi
    photo_file_id = message.photo[-1].file_id if message.photo else None

    # 1) Rasm izohidagi raqam — adminning qo'lda kiritgani, eng yuqori ustuvorlik
    actual_summa = parse_amount(message.caption)
    source = Source.CAPTION if actual_summa is not None else Source.NONE
    ai_summa: int | None = None
    ai_note: str | None = None

    # 2) Izoh bo'lmasa — chekni AI o'qiydi
    if actual_summa is None:
        receipt = await _read_receipt(deps, message)
        if receipt is not None:
            ai_note = receipt.summary()
            ai_summa = receipt.summa
            if receipt.is_reliable:
                actual_summa = receipt.summa
                source = Source.AI
            else:
                logger.info("Chek o'qildi, lekin ishonchsiz: %s", ai_note)

    komissiya = deps.db.mark_paid(
        request_id=request.id,
        photo_file_id=photo_file_id,
        actual_summa=actual_summa,
        paid_at=datetime.now(deps.settings.timezone),
        ai_summa=ai_summa,
        ai_izoh=ai_note,
    )
    logger.info(
        "So'rov #%s to'landi (manba: %s, komissiya: %s, qayta: %s)",
        request.id,
        source.value,
        komissiya,
        was_paid,
    )

    # So'rov xabaridagi 👀 reaksiyasi 👌 ga almashadi
    await send_with_retry(
        lambda: replied.set_reaction(deps.settings.reaction_paid),
        attempts=deps.settings.send_retries,
        description=f"#{request.id} uchun to'landi reaksiyasi",
    )

    text = build_confirmation_text(
        request_id=request.id,
        proyekt=request.proyekt,
        requested=request.summa_value,
        actual=actual_summa if actual_summa is not None else request.summa_value,
        komissiya=komissiya,
        source=source,
        ai_note=ai_note,
        was_paid=was_paid,
    )
    await send_with_retry(
        lambda: message.reply_text(text),
        attempts=deps.settings.send_retries,
        description=f"#{request.id} tasdiq xabari",
    )
