"""Guruhdagi so'rov xabarlarini tahlil qilish."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Har bir maydon uchun o'zbekcha va ruscha yorliqlar
LABEL_PATTERNS = {
    "resurs": r"(?:resurs|ресурс)",
    "proyekt": r"(?:proyekt|loyiha|проект)",
    "summa": r"(?:summa|сумма)",
    "karta": r"(?:karta|карта)",
}

REQUIRED_FIELDS = ("resurs", "proyekt", "summa", "karta")


@dataclass(frozen=True)
class ParsedRequest:
    resurs: str
    proyekt: str
    summa_raw: str
    summa_value: int
    karta: str


def _digits(text: str) -> str:
    return re.sub(r"[^\d]", "", text)


def parse_amount(text: str | None) -> int | None:
    """Matndan summani ajratadi (chek izohi uchun). Raqam bo'lmasa None."""
    if not text:
        return None
    digits = _digits(text)
    return int(digits) if digits else None


def parse_request(text: str | None) -> ParsedRequest | None:
    """Xabar matnidan resurs/proyekt/summa/karta maydonlarini ajratib oladi.

    Qiymat yorliq bilan bir qatorda ("Karta: 123...") yoki keyingi qatorda
    bo'lishi mumkin. To'rttala maydon topilmasa None qaytaradi — bunda
    xabar oddiy suhbat deb hisoblanadi va e'tiborsiz qoldiriladi.
    """
    if not text:
        return None

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    values: dict[str, str] = {}

    index = 0
    while index < len(lines):
        line = lines[index]
        matched_field = None
        remainder = ""
        for field, pattern in LABEL_PATTERNS.items():
            match = re.match(rf"^{pattern}\s*:?\s*(.*)$", line, re.IGNORECASE)
            if match:
                matched_field = field
                remainder = match.group(1).strip()
                break

        if matched_field:
            if remainder:
                values[matched_field] = remainder
            elif index + 1 < len(lines):
                values[matched_field] = lines[index + 1]  # qiymat keyingi qatorda
                index += 1
        index += 1

    if not all(field in values for field in REQUIRED_FIELDS):
        return None

    summa_raw = values["summa"]
    summa_digits = _digits(summa_raw)
    karta_digits = _digits(values["karta"])

    return ParsedRequest(
        resurs=values["resurs"],
        proyekt=values["proyekt"],
        summa_raw=summa_raw,
        summa_value=int(summa_digits) if summa_digits else 0,
        karta=karta_digits or values["karta"],
    )
