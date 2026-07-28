"""Kirish nuqtasi: `python -m app`."""

from __future__ import annotations

import logging
import sys

from app.bot.application import build_application
from app.config import ConfigError, load_settings
from app.db.database import Database
from app.logging_config import setup_logging

logger = logging.getLogger(__name__)


def main() -> int:
    try:
        settings = load_settings()
    except ConfigError as error:
        print(f"❌ Sozlamada xatolik: {error}", file=sys.stderr)
        print("   .env.example faylidan nusxa olib .env yarating.", file=sys.stderr)
        return 1

    setup_logging(settings.log_level)
    logger.info("Vaqt zonasi: %s | Baza: %s", settings.timezone, settings.db_path)
    if settings.group_chat_id:
        logger.info("Faqat shu guruh tinglanadi: %s", settings.group_chat_id)
    else:
        logger.warning("GROUP_CHAT_ID sozlanmagan — bot qo'shilgan HAR QANDAY guruhni tinglaydi.")

    db = Database(settings.db_path)
    db.init()

    application = build_application(settings, db)
    logger.info("Bot ishga tushmoqda (polling)...")
    application.run_polling()
    return 0


if __name__ == "__main__":
    sys.exit(main())
