"""Baza yozuvlarining tiplashtirilgan ko'rinishi."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

STATUS_PENDING = "kutilmoqda"
STATUS_PAID = "tolandi"


@dataclass(frozen=True)
class PaymentRequest:
    id: int
    chat_id: int
    message_id: int
    resurs: str
    proyekt: str
    summa_raw: str
    summa_value: int
    karta: str
    status: str
    requested_by: str
    created_at: str
    paid_at: str | None
    paid_photo_file_id: str | None
    actual_summa: int
    komissiya: int

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "PaymentRequest":
        return cls(
            id=row["id"],
            chat_id=row["chat_id"],
            message_id=row["message_id"],
            resurs=row["resurs"],
            proyekt=row["proyekt"],
            summa_raw=row["summa_raw"],
            summa_value=row["summa_value"] or 0,
            karta=row["karta"],
            status=row["status"],
            requested_by=row["requested_by"],
            created_at=row["created_at"],
            paid_at=row["paid_at"],
            paid_photo_file_id=row["paid_photo_file_id"],
            actual_summa=row["actual_summa"] or 0,
            komissiya=row["komissiya"] or 0,
        )

    @property
    def is_paid(self) -> bool:
        return self.status == STATUS_PAID

    @property
    def effective_paid(self) -> int:
        """Haqiqiy o'tkazilgan summa; belgilanmagan bo'lsa — so'ralgani."""
        return self.actual_summa or self.summa_value
