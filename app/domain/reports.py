"""Hisobot matnini yig'ish. Sof funksiya — baza yoki Telegram'ga bog'liq emas."""

from __future__ import annotations

from typing import Sequence

from app.db.models import PaymentRequest
from app.domain.formatting import format_sum


def build_report_text(title: str, requests: Sequence[PaymentRequest]) -> str:
    if not requests:
        return f"📊 {title}\n\nBu davrda so'rovlar bo'lmadi."

    paid = [r for r in requests if r.is_paid]
    pending = [r for r in requests if not r.is_paid]

    total_sum = sum(r.summa_value for r in requests)
    paid_sum = sum(r.summa_value for r in paid)
    pending_sum = sum(r.summa_value for r in pending)
    total_komissiya = sum(r.komissiya for r in paid)
    total_actual_paid = sum(r.effective_paid for r in paid)

    by_project: dict[str, dict[str, int]] = {}
    for request in requests:
        entry = by_project.setdefault(request.proyekt, {"count": 0, "sum": 0})
        entry["count"] += 1
        entry["sum"] += request.summa_value

    lines = [f"📊 {title}", ""]
    lines.append(f"Jami so'rovlar: {len(requests)} ta")
    lines.append(f"Jami summa (so'ralgan): {format_sum(total_sum)}")
    lines.append(f"✅ To'langan: {len(paid)} ta — {format_sum(paid_sum)}")
    lines.append(f"⏳ Kutilmoqda: {len(pending)} ta — {format_sum(pending_sum)}")
    if total_komissiya:
        lines.append(f"💳 Haqiqiy o'tkazilgan (komissiya bilan): {format_sum(total_actual_paid)}")
        lines.append(f"💸 Jami komissiya xarajati: {format_sum(total_komissiya)}")
    lines.append("")
    lines.append("Proyektlar bo'yicha:")
    for proyekt, data in sorted(by_project.items(), key=lambda item: -item[1]["sum"]):
        lines.append(f"  • {proyekt}: {data['count']} ta — {format_sum(data['sum'])}")

    if pending:
        lines.append("")
        lines.append("⏳ Hali to'lanmagan so'rovlar:")
        for request in pending:
            lines.append(
                f"  #{request.id} {request.proyekt} — "
                f"{format_sum(request.summa_value)} — karta: {request.karta}"
            )

    return "\n".join(lines)


def build_pending_text(requests: Sequence[PaymentRequest]) -> str:
    if not requests:
        return "✅ Hozircha kutilayotgan to'lovlar yo'q."

    lines = ["⏳ Kutilayotgan to'lovlar:", ""]
    total = 0
    for request in requests:
        lines.append(
            f"#{request.id} {request.proyekt} — "
            f"{format_sum(request.summa_value)} — karta: {request.karta}"
        )
        total += request.summa_value
    lines.append("")
    lines.append(f"Jami: {format_sum(total)}")
    return "\n".join(lines)
