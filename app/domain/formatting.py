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


def format_percent(change: float) -> str:
    """0.2 -> "+20%"; -0.15 -> "-15%"."""
    percent = round(change * 100)
    if percent > 0:
        return f"+{percent}%"
    if percent < 0:
        return f"{percent}%"
    return "o'zgarmadi"
