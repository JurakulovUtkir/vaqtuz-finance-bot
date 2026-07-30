"""Foydalanuvchiga ko'rinadigan matn formatlari."""

from __future__ import annotations

import re

TME_PATTERN = re.compile(r"(?:https?://)?t\.me/(?:s/)?(@?[A-Za-z0-9_]+)", re.IGNORECASE)


def format_sum(value: int) -> str:
    """60000 -> "60 000 so'm" """
    return f"{value:,}".replace(",", " ") + " so'm"


def format_resurs(resurs: str | None) -> str:
    """`https://t.me/segmentuz` -> `@segmentuz`. Link bo'lmasa o'zini qaytaradi."""
    if not resurs:
        return "—"
    match = TME_PATTERN.search(resurs)
    if match:
        name = match.group(1)
        return name if name.startswith("@") else f"@{name}"
    return resurs.strip()


def chunk_text(text: str, limit: int = 3900) -> list[str]:
    """Telegram bitta xabarda 4096 belgidan ko'pini qabul qilmaydi.

    Qatorlar chegarasida bo'lamiz — hisobot o'rtasidan kesilib qolmasin.
    """
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    length = 0

    for line in text.split("\n"):
        while len(line) > limit:  # bitta qator ham uzun bo'lsa majburan kesamiz
            if current:
                chunks.append("\n".join(current))
                current, length = [], 0
            chunks.append(line[:limit])
            line = line[limit:]
        if length + len(line) + 1 > limit and current:
            chunks.append("\n".join(current))
            current, length = [], 0
        current.append(line)
        length += len(line) + 1

    if current:
        chunks.append("\n".join(current))
    return chunks


def format_percent(change: float) -> str:
    """0.2 -> "+20%"; -0.15 -> "-15%"."""
    percent = round(change * 100)
    if percent > 0:
        return f"+{percent}%"
    if percent < 0:
        return f"{percent}%"
    return "o'zgarmadi"
