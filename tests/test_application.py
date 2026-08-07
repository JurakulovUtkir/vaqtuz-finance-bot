"""Application to'g'ri yig'ilishini tekshiruvchi smoke-test (tarmoqqa chiqmaydi)."""

from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler

from app.bot.application import build_application
from app.bot.deps import DEPS_KEY
from app.config import load_settings
from app.db.database import Database

ENV = {
    "TELEGRAM_BOT_TOKEN": "123456789:AAHtestTokenValue",
    "ADMIN_ID": "555000111",
    "GROUP_CHAT_ID": "-1001234567890",
}


def _build(tmp_path):
    settings = load_settings({**ENV, "DB_PATH": str(tmp_path / "smoke.db")})
    db = Database(settings.db_path)
    db.init()
    return build_application(settings, db)


def test_handlers_registered(tmp_path):
    application = _build(tmp_path)
    handlers = application.handlers[0]

    command_names = {
        name
        for handler in handlers
        if isinstance(handler, CommandHandler)
        for name in handler.commands
    }
    assert command_names == {"start", "menu", "bugun", "hafta", "oy", "kutilmoqda", "chek"}
    # matn (guruh) va rasm (chek). Hujjat handleri — tiklash bilan birga o'chirilgan.
    assert sum(isinstance(handler, MessageHandler) for handler in handlers) == 2
    assert sum(isinstance(handler, CallbackQueryHandler) for handler in handlers) == 1
    assert application.error_handlers


def test_jobs_registered(tmp_path):
    application = _build(tmp_path)
    job_names = {job.name for job in application.job_queue.jobs()}
    assert job_names == {"daily_report", "weekly_report", "monthly_report_check", "backup"}


def test_deps_available_in_bot_data(tmp_path):
    application = _build(tmp_path)
    deps = application.bot_data[DEPS_KEY]
    assert deps.settings.admin_id == 555000111
    assert deps.insight.enabled is False  # ANTHROPIC_API_KEY berilmagan
    assert deps.receipt_reader.enabled is False


def test_network_timeouts_applied(tmp_path):
    """Standart 5 soniya beqaror tarmoqda yetmaydi — kengaytirilgani tekshiriladi."""
    application = _build(tmp_path)
    request = application.bot.request
    assert request._client.timeout.connect >= 30
    assert request._client.timeout.write >= 30
