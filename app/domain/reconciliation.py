"""Chekdagi summani so'ralgan summa bilan solishtirish.

Bank odatda so'ralgan summadan biroz ko'proq yechadi — bu komissiya.
Undan tashqari har qanday farq nomuvofiqlik deb qaraladi va ogohlantiriladi.
"""

from __future__ import annotations

from enum import Enum

from app.domain.formatting import format_sum

# So'ralgan summaning shu ulushigacha bo'lgan ortiqcha — normal komissiya
MAX_COMMISSION_RATIO = 0.05


class Source(str, Enum):
    CAPTION = "izoh"  # admin rasm izohiga qo'lda yozgan
    AI = "ai"  # chekdan avtomatik o'qilgan
    NONE = "yoq"  # aniqlanmadi — so'ralgan summa ishlatildi


class Match(str, Enum):
    EXACT = "aniq"
    COMMISSION = "komissiya"
    MISMATCH = "nomuvofiq"


def classify(requested: int, actual: int) -> Match:
    """So'ralgan va haqiqatda o'tkazilgan summa nisbatini aniqlaydi."""
    if actual == requested:
        return Match.EXACT

    difference = actual - requested
    if 0 < difference <= requested * MAX_COMMISSION_RATIO:
        return Match.COMMISSION

    return Match.MISMATCH


def build_confirmation_text(
    *,
    request_id: int,
    proyekt: str,
    requested: int,
    actual: int,
    komissiya: int,
    source: Source,
    ai_note: str | None = None,
    was_paid: bool = False,
) -> str:
    """Admin chek tashlaganda yuboriladigan qisqa tasdiq matni."""
    header = f"♻️ #{request_id} cheki yangilandi" if was_paid else f"👌 #{request_id} to'landi"
    lines = [f"{header} — {proyekt}"]

    match = classify(requested, actual)
    if match is Match.EXACT and source is Source.NONE:
        lines[0] += f" — {format_sum(requested)}"
        lines.append("ℹ️ Chekdan summa o'qilmadi — so'ralgan summa yozildi.")
        lines.append("Aniq summani rasm izohiga yozib qayta tashlashingiz mumkin.")
        return "\n".join(lines)

    lines.append(f"So'ralgan: {format_sum(requested)}")

    read_from = "izohdan" if source is Source.CAPTION else "chekdan o'qildi"
    detail = f"Chekda: {format_sum(actual)} ({read_from}"
    if source is Source.AI and ai_note:
        detail += f", {ai_note}"
    lines.append(detail + ")")

    if match is Match.COMMISSION:
        lines.append(f"💸 Komissiya: {format_sum(komissiya)}")
    elif match is Match.MISMATCH:
        lines.append("")
        lines.append("⚠️ Summalar mos kelmayapti — tekshiring!")
        lines.append(f"Farq: {format_sum(abs(komissiya))} {'ortiqcha' if komissiya > 0 else 'kam'}")

    return "\n".join(lines)
