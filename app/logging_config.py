"""Log sozlamalari."""

from __future__ import annotations

import logging

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(format=LOG_FORMAT, level=getattr(logging, level, logging.INFO))
    # httpx har bir getUpdates so'rovini INFO darajada yozadi — serverda log'ni ko'mib tashlaydi
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
