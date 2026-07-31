"""Testlar uchun umumiy yordamchi."""

from __future__ import annotations

from app.db.models import STATUS_PENDING, PaymentRequest


def make_request(
    request_id: int = 1,
    *,
    proyekt: str = "Garant Bank",
    resurs: str = "https://t.me/segmentuz",
    summa: int = 60000,
    status: str = STATUS_PENDING,
    actual: int = 0,
    komissiya: int = 0,
    created_at: str = "2026-07-28T10:00:00+05:00",
    paid_photo_file_id: str | None = None,
    paid_by: str | None = None,
) -> PaymentRequest:
    return PaymentRequest(
        id=request_id,
        chat_id=-1001,
        message_id=100 + request_id,
        resurs=resurs,
        proyekt=proyekt,
        summa_raw=str(summa),
        summa_value=summa,
        karta="8600123412341234",
        status=status,
        requested_by="Tester",
        created_at=created_at,
        paid_at=None,
        paid_photo_file_id=paid_photo_file_id,
        actual_summa=actual,
        komissiya=komissiya,
        ai_summa=None,
        ai_izoh=None,
        paid_by=paid_by,
        paid_by_id=None,
    )
