"""Hisobot matnini yig'ish. Sof funksiya — baza yoki Telegram'ga bog'liq emas."""

from __future__ import annotations

from typing import Sequence

from app.db.models import PaymentRequest
from app.domain.analytics import by_channel, by_project, price_dynamics
from app.domain.formatting import format_percent, format_resurs, format_sum


def _summary_lines(requests: Sequence[PaymentRequest]) -> list[str]:
    paid = [r for r in requests if r.is_paid]
    pending = [r for r in requests if not r.is_paid]

    total_komissiya = sum(r.komissiya for r in paid)
    total_actual_paid = sum(r.effective_paid for r in paid)

    lines = [
        f"Jami so'rovlar: {len(requests)} ta",
        f"Jami summa (so'ralgan): {format_sum(sum(r.summa_value for r in requests))}",
        f"✅ To'langan: {len(paid)} ta — {format_sum(sum(r.summa_value for r in paid))}",
        f"⏳ Kutilmoqda: {len(pending)} ta — {format_sum(sum(r.summa_value for r in pending))}",
    ]
    if total_komissiya:
        lines.append(f"💳 Haqiqiy o'tkazilgan (komissiya bilan): {format_sum(total_actual_paid)}")
        lines.append(f"💸 Jami komissiya xarajati: {format_sum(total_komissiya)}")
    return lines


def _breakdown_lines(requests: Sequence[PaymentRequest]) -> list[str]:
    lines: list[str] = ["", "🏢 Mijozlar bo'yicha:"]
    for stat in by_project(requests):
        lines.append(f"  • {stat.key}: {stat.count} ta — {format_sum(stat.total)}")

    lines.append("")
    lines.append("📢 Kanallar bo'yicha:")
    for stat in by_channel(requests):
        lines.append(
            f"  • {stat.key}: {stat.count} ta — {format_sum(stat.total)} "
            f"(o'rtacha {format_sum(stat.average)})"
        )
    return lines


def _dynamics_lines(
    requests: Sequence[PaymentRequest], previous: Sequence[PaymentRequest]
) -> list[str]:
    changes = price_dynamics(requests, previous)
    if not changes:
        return []

    lines = ["", "📈 Kanal narxlari (o'tgan davrga nisbatan):"]
    for change in changes:
        if change.is_new:
            lines.append(f"  • {change.channel}: yangi — {format_sum(change.current_average)}")
        else:
            lines.append(
                f"  • {change.channel}: {format_sum(change.previous_average or 0)} → "
                f"{format_sum(change.current_average)} ({format_percent(change.ratio)})"
            )
    return lines


def _pending_lines(requests: Sequence[PaymentRequest]) -> list[str]:
    pending = [r for r in requests if not r.is_paid]
    if not pending:
        return []

    lines = ["", "⏳ Hali to'lanmagan so'rovlar:"]
    for request in pending:
        lines.append(
            f"  #{request.id} {request.proyekt} — {format_sum(request.summa_value)} — "
            f"{format_resurs(request.resurs)} — karta: {request.karta}"
        )
    return lines


def build_report_text(
    title: str,
    requests: Sequence[PaymentRequest],
    previous: Sequence[PaymentRequest] | None = None,
) -> str:
    """`previous` berilsa, kanal narxlari o'tgan davr bilan solishtiriladi."""
    if not requests:
        return f"📊 {title}\n\nBu davrda so'rovlar bo'lmadi."

    lines = [f"📊 {title}", ""]
    lines += _summary_lines(requests)
    lines += _breakdown_lines(requests)
    if previous:
        lines += _dynamics_lines(requests, previous)
    lines += _pending_lines(requests)
    return "\n".join(lines)


def build_pending_text(requests: Sequence[PaymentRequest]) -> str:
    if not requests:
        return "✅ Hozircha kutilayotgan to'lovlar yo'q."

    lines = ["⏳ Kutilayotgan to'lovlar:", ""]
    total = 0
    for request in requests:
        lines.append(
            f"#{request.id} {request.proyekt} — {format_sum(request.summa_value)} — "
            f"{format_resurs(request.resurs)} — karta: {request.karta}"
        )
        total += request.summa_value
    lines.append("")
    lines.append(f"Jami: {format_sum(total)}")
    return "\n".join(lines)
