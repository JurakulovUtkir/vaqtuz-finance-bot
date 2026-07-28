"""Telegram Application'ni yig'ish: bog'liqliklar, handler'lar, job'lar."""

from __future__ import annotations

import logging

from telegram import BotCommand
from telegram.ext import Application, ApplicationBuilder, CommandHandler, MessageHandler, filters

from app.ai.insight import InsightProvider
from app.bot.deps import DEPS_KEY, Deps
from app.bot.handlers import commands, errors, receipts, requests
from app.bot.jobs import register_jobs
from app.config import Settings
from app.db.database import Database

logger = logging.getLogger(__name__)


async def _post_init(application: Application) -> None:
    """Telegram menyusida buyruqlar ro'yxatini ko'rsatamiz."""
    await application.bot.set_my_commands(
        [BotCommand(name, description) for name, description in commands.COMMANDS]
    )
    me = await application.bot.get_me()
    logger.info("Bot ulandi: @%s (id=%s)", me.username, me.id)


def build_application(settings: Settings, db: Database) -> Application:
    application = ApplicationBuilder().token(settings.bot_token).post_init(_post_init).build()

    application.bot_data[DEPS_KEY] = Deps(
        settings=settings,
        db=db,
        insight=InsightProvider(settings.anthropic_api_key, settings.ai_model),
    )

    application.add_handler(CommandHandler("start", commands.cmd_start))
    application.add_handler(CommandHandler("bugun", commands.cmd_today))
    application.add_handler(CommandHandler("hafta", commands.cmd_week))
    application.add_handler(CommandHandler("oy", commands.cmd_month))
    application.add_handler(CommandHandler("kutilmoqda", commands.cmd_pending))

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS,
            requests.handle_group_message,
        )
    )
    application.add_handler(MessageHandler(filters.PHOTO, receipts.handle_admin_photo))

    application.add_error_handler(errors.handle_error)

    register_jobs(application, settings)
    return application
