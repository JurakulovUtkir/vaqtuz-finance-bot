"""Handler'lar va job'lar uchun umumiy bog'liqliklar."""

from __future__ import annotations

from dataclasses import dataclass

from telegram.ext import ContextTypes

from app.ai.insight import InsightProvider
from app.ai.vision import ReceiptReader
from app.config import Settings
from app.db.database import Database

DEPS_KEY = "deps"


@dataclass(frozen=True)
class Deps:
    settings: Settings
    db: Database
    insight: InsightProvider
    receipt_reader: ReceiptReader


def get_deps(context: ContextTypes.DEFAULT_TYPE) -> Deps:
    return context.bot_data[DEPS_KEY]
