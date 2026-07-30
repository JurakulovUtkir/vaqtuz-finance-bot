"""Telegram'ga yuborishda qayta urinish.

Server bilan api.telegram.org orasidagi yo'l beqaror: ulanish goh 0.05 soniya,
goh 5+ soniya davom etadi. Taymautlarni kengaytirish yetmaydi — vaqti-vaqti
bilan ulanish umuman amalga oshmaydi, shuning uchun qayta urinish kerak.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, TypeVar

from telegram.error import NetworkError, TimedOut

logger = logging.getLogger(__name__)

T = TypeVar("T")

RETRY_BASE_DELAY = 2.0


async def send_with_retry(
    action: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    description: str = "yuborish",
) -> T | None:
    """Tarmoq xatoligida qayta uriniladi. Hammasi yiqilsa None qaytadi.

    Yuborilmagan xabar botni to'xtatmasligi kerak — ma'lumot bazaga
    allaqachon yozilgan bo'ladi.
    """
    for attempt in range(1, attempts + 1):
        try:
            return await action()
        except (TimedOut, NetworkError) as error:
            if attempt == attempts:
                logger.error("%s: %s urinishdan keyin ham yiqildi (%s)", description, attempts, error)
                return None
            delay = RETRY_BASE_DELAY * attempt
            logger.warning(
                "%s: %s-urinish muvaffaqiyatsiz (%s), %.0fs dan keyin qayta urinaman",
                description,
                attempt,
                error,
                delay,
            )
            await asyncio.sleep(delay)
    return None
