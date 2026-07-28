"""Ushlanmagan xatoliklarni log'ga yozish."""

from __future__ import annotations

import logging

from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Xatolik yuz berdi: %s", context.error, exc_info=context.error)
