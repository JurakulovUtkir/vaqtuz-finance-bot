"""Qo'lda chaqiriladigan buyruqlar."""

from __future__ import annotations

import logging
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.deps import get_deps
from app.bot.reporting import compose_report, daily_title, monthly_title, weekly_title
from app.domain.periods import day_range, month_range, week_range
from app.domain.reports import build_pending_text

logger = logging.getLogger(__name__)

START_TEXT = (
    "🤖 To'lov nazorati boti ishga tushdi.\n\n"
    "Guruhda quyidagi formatdagi xabarlarni kuzataman:\n"
    "Resurs: ...\nProyekt: ...\nSumma: ...\nKarta: ...\n\n"
    "Buyruqlar:\n"
    "/bugun - bugungi hisobot\n"
    "/hafta - shu haftalik hisobot\n"
    "/oy - shu oylik hisobot\n"
    "/kutilmoqda - hali to'lanmagan so'rovlar"
)

COMMANDS = (
    ("bugun", "Bugungi hisobot"),
    ("hafta", "Shu haftalik hisobot"),
    ("oy", "Shu oylik hisobot"),
    ("kutilmoqda", "Hali to'lanmagan so'rovlar"),
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(START_TEXT)


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    deps = get_deps(context)
    now = datetime.now(deps.settings.timezone)
    start, end = day_range(now)
    text = await compose_report(deps, daily_title(now), start, end)
    if update.message:
        await update.message.reply_text(text)


async def cmd_week(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    deps = get_deps(context)
    now = datetime.now(deps.settings.timezone)
    start, end = week_range(now)
    text = await compose_report(deps, weekly_title(start, end), start, end)
    if update.message:
        await update.message.reply_text(text)


async def cmd_month(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    deps = get_deps(context)
    now = datetime.now(deps.settings.timezone)
    start, end = month_range(now)
    text = await compose_report(deps, monthly_title(start), start, end)
    if update.message:
        await update.message.reply_text(text)


async def cmd_pending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    deps = get_deps(context)
    text = build_pending_text(deps.db.get_pending())
    if update.message:
        await update.message.reply_text(text)
