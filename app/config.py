"""Sozlamalar: muhit o'zgaruvchilarini o'qish va ishga tushishdan oldin tekshirish."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import time as dtime
from typing import Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_AI_MODEL = "claude-haiku-4-5"
DEFAULT_TIMEZONE = "Asia/Tashkent"
DEFAULT_DB_PATH = "/data/payments.db"
DEFAULT_LOG_LEVEL = "INFO"

DEFAULT_DAILY_TIME = "23:00"
DEFAULT_WEEKLY_TIME = "23:05"
DEFAULT_MONTHLY_TIME = "23:10"

# python-telegram-bot v20+ da 0-6 = dushanba-yakshanba
WEEKLY_REPORT_WEEKDAY = 6  # yakshanba

# Telegram reaksiya emojilari cheklangan ro'yxatdan tanlanadi — ✅ va ⏳ mavjud emas
DEFAULT_REACTION_RECEIVED = "👀"
DEFAULT_REACTION_PAID = "👌"

# Telegram'ga tarmoq beqaror bo'lishi mumkin — taymautlar keng olinadi
DEFAULT_NETWORK_TIMEOUT = 30.0
DEFAULT_SEND_RETRIES = 3


class ConfigError(RuntimeError):
    """Sozlamalar yetishmayotganda yoki noto'g'ri bo'lganda ko'tariladi."""


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_id: int
    group_chat_id: str | None
    report_chat_id_override: str | None
    anthropic_api_key: str
    ai_model: str
    timezone: ZoneInfo
    db_path: str
    log_level: str
    daily_report_time: dtime
    weekly_report_time: dtime
    monthly_check_time: dtime
    reaction_received: str
    reaction_paid: str
    network_timeout: float
    send_retries: int

    @property
    def report_chat_id(self) -> int | str:
        """Hisobot yuboriladigan chat. Alohida ko'rsatilmasa — adminning o'zi."""
        return self.report_chat_id_override or self.admin_id

    @property
    def ai_enabled(self) -> bool:
        return bool(self.anthropic_api_key)


def _read(env: Mapping[str, str], name: str, default: str | None = None) -> str | None:
    """Bo'sh satrni None deb qaraydi — .env dagi `FOO=` ni sozlanmagan deb hisoblaymiz."""
    value = env.get(name, default)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _read_chat_id(env: Mapping[str, str], name: str) -> str | None:
    value = _read(env, name)
    if value is None:
        return None
    if value.startswith("@"):
        return value  # ochiq kanal/guruh username'i
    try:
        int(value)
    except ValueError:
        raise ConfigError(
            f"{name} noto'g'ri: {value!r}. Raqam bo'lishi kerak "
            f"(guruh ID'lari manfiy bo'ladi, masalan -1001234567890) yoki @username."
        ) from None
    return value


def _read_float(env: Mapping[str, str], name: str, default: float) -> float:
    raw = _read(env, name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        raise ConfigError(f"{name} raqam bo'lishi kerak, berilgani: {raw!r}") from None
    if value <= 0:
        raise ConfigError(f"{name} musbat bo'lishi kerak.")
    return value


def _read_time(env: Mapping[str, str], name: str, default: str, tz: ZoneInfo) -> dtime:
    raw = _read(env, name, default)
    assert raw is not None  # default hech qachon bo'sh emas
    try:
        hour_str, minute_str = raw.split(":")
        return dtime(hour=int(hour_str), minute=int(minute_str), tzinfo=tz)
    except ValueError:
        raise ConfigError(
            f"{name} noto'g'ri formatda: {raw!r}. Kutilgan format: HH:MM (masalan 23:00)."
        ) from None


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Muhit o'zgaruvchilaridan sozlamalarni yig'adi.

    Har qanday muammoda darhol ConfigError beradi — bot yarim sozlangan
    holatda ishga tushib, keyin jimgina xato qilishidan ko'ra shu yaxshi.
    """
    env = os.environ if env is None else env

    bot_token = _read(env, "TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise ConfigError(
            "TELEGRAM_BOT_TOKEN sozlanmagan. @BotFather'dan token oling va .env fayliga yozing."
        )
    if ":" not in bot_token:
        raise ConfigError(
            "TELEGRAM_BOT_TOKEN noto'g'ri ko'rinishda — token `123456789:AA...` shaklida bo'ladi."
        )

    admin_raw = _read(env, "ADMIN_ID")
    if not admin_raw:
        raise ConfigError(
            "ADMIN_ID sozlanmagan. Telegram'da @userinfobot ga yozib o'z ID'ingizni oling."
        )
    try:
        admin_id = int(admin_raw)
    except ValueError:
        raise ConfigError(f"ADMIN_ID raqam bo'lishi kerak, berilgani: {admin_raw!r}") from None
    if admin_id <= 0:
        raise ConfigError("ADMIN_ID musbat raqam bo'lishi kerak.")

    tz_name = _read(env, "TZ", DEFAULT_TIMEZONE) or DEFAULT_TIMEZONE
    try:
        timezone = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        raise ConfigError(
            f"TZ noto'g'ri yoki serverda topilmadi: {tz_name!r}. "
            f"Masalan: Asia/Tashkent. Docker'siz ishlatsangiz `pip install tzdata` kerak bo'lishi mumkin."
        ) from None

    return Settings(
        bot_token=bot_token,
        admin_id=admin_id,
        group_chat_id=_read_chat_id(env, "GROUP_CHAT_ID"),
        report_chat_id_override=_read_chat_id(env, "REPORT_CHAT_ID"),
        anthropic_api_key=_read(env, "ANTHROPIC_API_KEY") or "",
        ai_model=_read(env, "AI_MODEL", DEFAULT_AI_MODEL) or DEFAULT_AI_MODEL,
        timezone=timezone,
        db_path=_read(env, "DB_PATH", DEFAULT_DB_PATH) or DEFAULT_DB_PATH,
        log_level=(_read(env, "LOG_LEVEL", DEFAULT_LOG_LEVEL) or DEFAULT_LOG_LEVEL).upper(),
        daily_report_time=_read_time(env, "DAILY_REPORT_TIME", DEFAULT_DAILY_TIME, timezone),
        weekly_report_time=_read_time(env, "WEEKLY_REPORT_TIME", DEFAULT_WEEKLY_TIME, timezone),
        monthly_check_time=_read_time(env, "MONTHLY_CHECK_TIME", DEFAULT_MONTHLY_TIME, timezone),
        reaction_received=_read(env, "REACTION_RECEIVED", DEFAULT_REACTION_RECEIVED)
        or DEFAULT_REACTION_RECEIVED,
        reaction_paid=_read(env, "REACTION_PAID", DEFAULT_REACTION_PAID) or DEFAULT_REACTION_PAID,
        network_timeout=_read_float(env, "NETWORK_TIMEOUT", DEFAULT_NETWORK_TIMEOUT),
        send_retries=int(_read_float(env, "SEND_RETRIES", DEFAULT_SEND_RETRIES)),
    )
