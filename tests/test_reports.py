from app.db.models import STATUS_PAID, STATUS_PENDING
from app.domain.formatting import format_percent, format_resurs, format_sum
from app.domain.reports import build_pending_text, build_report_text
from tests.factories import make_request


def test_format_sum():
    assert format_sum(60000) == "60 000 so'm"
    assert format_sum(1200000) == "1 200 000 so'm"
    assert format_sum(0) == "0 so'm"


def test_format_resurs():
    assert format_resurs("https://t.me/segmentuz") == "@segmentuz"
    assert format_resurs("t.me/segmentuz") == "@segmentuz"
    assert format_resurs("https://t.me/s/segmentuz") == "@segmentuz"
    assert format_resurs("@segmentuz") == "@segmentuz"
    assert format_resurs("oddiy matn") == "oddiy matn"
    assert format_resurs(None) == "—"


def test_format_percent():
    assert format_percent(0.2) == "+20%"
    assert format_percent(-0.15) == "-15%"
    assert format_percent(0.0) == "o'zgarmadi"


def test_empty_report():
    assert "so'rovlar bo'lmadi" in build_report_text("Kunlik hisobot", [])


def test_report_totals():
    rows = [
        make_request(1, summa=60000, status=STATUS_PAID, actual=60000),
        make_request(2, summa=40000, status=STATUS_PENDING),
    ]
    text = build_report_text("Kunlik hisobot", rows)
    assert "Jami so'rovlar: 2 ta" in text
    assert "Jami summa (so'ralgan): 100 000 so'm" in text
    assert "✅ To'langan: 1 ta — 60 000 so'm" in text
    assert "⏳ Kutilmoqda: 1 ta — 40 000 so'm" in text


def test_commission_lines_appear_only_when_nonzero():
    without = build_report_text("X", [make_request(1, status=STATUS_PAID, actual=60000)])
    assert "Jami komissiya" not in without

    with_commission = build_report_text(
        "X", [make_request(1, summa=60000, status=STATUS_PAID, actual=60600, komissiya=600)]
    )
    assert "💸 Jami komissiya xarajati: 600 so'm" in with_commission


def test_both_breakdowns_present():
    rows = [
        make_request(1, proyekt="octobank", resurs="https://t.me/kanal_a", summa=90000),
        make_request(2, proyekt="Garant Bank", resurs="https://t.me/kanal_b", summa=10000),
    ]
    text = build_report_text("X", rows)
    assert "🏢 Mijozlar bo'yicha:" in text
    assert "📢 Kanallar bo'yicha:" in text
    assert "• octobank: 1 ta — 90 000 so'm" in text
    assert "• @kanal_a: 1 ta — 90 000 so'm (o'rtacha 90 000 so'm)" in text


def test_projects_sorted_by_amount_desc():
    rows = [
        make_request(1, proyekt="Kichik", summa=10000),
        make_request(2, proyekt="Katta", summa=90000),
    ]
    lines = build_report_text("X", rows).splitlines()
    section = lines.index("🏢 Mijozlar bo'yicha:")
    assert lines[section + 1].startswith("  • Katta")
    assert lines[section + 2].startswith("  • Kichik")


def test_pending_section_includes_channel():
    text = build_report_text(
        "X", [make_request(7, proyekt="Uzum", resurs="https://t.me/uzumkanal", summa=25000)]
    )
    assert "#7 Uzum — 25 000 so'm — @uzumkanal — karta: 8600123412341234" in text


def test_price_dynamics_section():
    previous = [make_request(1, resurs="https://t.me/kanal_a", summa=1000000)]
    current = [make_request(2, resurs="https://t.me/kanal_a", summa=1200000)]
    text = build_report_text("X", current, previous)
    assert "📈 Kanal narxlari" in text
    assert "@kanal_a: 1 000 000 so'm → 1 200 000 so'm (+20%)" in text


def test_dynamics_omitted_without_previous():
    assert "📈 Kanal narxlari" not in build_report_text("X", [make_request(1)])


def test_pending_text_empty():
    assert "kutilayotgan to'lovlar yo'q" in build_pending_text([])


def test_pending_text_totals():
    text = build_pending_text([make_request(1, summa=10000), make_request(2, summa=5000)])
    assert "Jami: 15 000 so'm" in text
