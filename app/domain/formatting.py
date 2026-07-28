"""Foydalanuvchiga ko'rinadigan matn formatlari."""

from __future__ import annotations


def format_sum(value: int) -> str:
    """60000 -> "60 000 so'm" """
    return f"{value:,}".replace(",", " ") + " so'm"
