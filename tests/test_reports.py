from app.db.models import STATUS_PAID, STATUS_PENDING, PaymentRequest
from app.domain.formatting import format_sum
from app.domain.reports import build_pending_text, build_report_text


def _request(
    request_id=1,
    proyekt="Garant Bank",
    summa=60000,
    status=STATUS_PENDING,
    actual=0,
    komissiya=0,
):
    return PaymentRequest(
        id=request_id,
        chat_id=-1001,
        message_id=100 + request_id,
        resurs="t.me/x",
        proyekt=proyekt,
        summa_raw=str(summa),
        summa_value=summa,
        karta="8600123412341234",
        status=status,
        requested_by="Tester",
        created_at="2026-07-28T10:00:00+05:00",
        paid_at=None,
        paid_photo_file_id=None,
        actual_summa=actual,
        komissiya=komissiya,
    )


def test_format_sum():
    assert format_sum(60000) == "60 000 so'm"
    assert format_sum(1200000) == "1 200 000 so'm"
    assert format_sum(0) == "0 so'm"


def test_empty_report():
    text = build_report_text("Kunlik hisobot", [])
    assert "so'rovlar bo'lmadi" in text


def test_report_totals():
    rows = [
        _request(1, summa=60000, status=STATUS_PAID, actual=60000),
        _request(2, summa=40000, status=STATUS_PENDING),
    ]
    text = build_report_text("Kunlik hisobot", rows)
    assert "Jami so'rovlar: 2 ta" in text
    assert "Jami summa (so'ralgan): 100 000 so'm" in text
    assert "✅ To'langan: 1 ta — 60 000 so'm" in text
    assert "⏳ Kutilmoqda: 1 ta — 40 000 so'm" in text


def test_commission_lines_appear_only_when_nonzero():
    without = build_report_text("X", [_request(1, status=STATUS_PAID, actual=60000)])
    assert "Jami komissiya" not in without

    with_commission = build_report_text(
        "X", [_request(1, summa=60000, status=STATUS_PAID, actual=60600, komissiya=600)]
    )
    assert "💸 Jami komissiya xarajati: 600 so'm" in with_commission
    assert "💳 Haqiqiy o'tkazilgan (komissiya bilan): 60 600 so'm" in with_commission


def test_projects_sorted_by_amount_desc():
    rows = [
        _request(1, proyekt="Kichik", summa=10000),
        _request(2, proyekt="Katta", summa=90000),
    ]
    lines = build_report_text("X", rows).splitlines()
    project_lines = [line for line in lines if line.startswith("  • ")]
    assert project_lines[0].startswith("  • Katta")
    assert project_lines[1].startswith("  • Kichik")


def test_pending_section_lists_unpaid_requests():
    text = build_report_text("X", [_request(7, proyekt="Uzum", summa=25000)])
    assert "#7 Uzum — 25 000 so'm — karta: 8600123412341234" in text


def test_pending_text_empty():
    assert "kutilayotgan to'lovlar yo'q" in build_pending_text([])


def test_pending_text_totals():
    text = build_pending_text([_request(1, summa=10000), _request(2, summa=5000)])
    assert "Jami: 15 000 so'm" in text
