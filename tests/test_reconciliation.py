from app.domain.reconciliation import Match, Source, build_confirmation_text, classify


def test_exact_match():
    assert classify(60000, 60000) is Match.EXACT


def test_small_excess_is_commission():
    assert classify(60000, 60600) is Match.COMMISSION  # +1%
    assert classify(60000, 63000) is Match.COMMISSION  # +5% chegara


def test_large_excess_is_mismatch():
    assert classify(60000, 70000) is Match.MISMATCH  # +16%


def test_shortfall_is_always_mismatch():
    assert classify(8770000, 700000) is Match.MISMATCH
    assert classify(60000, 59999) is Match.MISMATCH


def test_confirmation_exact_without_source():
    text = build_confirmation_text(
        request_id=5,
        proyekt="Garant Bank",
        requested=60000,
        actual=60000,
        komissiya=0,
        source=Source.NONE,
    )
    assert "👌 #5 to'landi — Garant Bank — 60 000 so'm" in text
    assert "Chekdan summa o'qilmadi" in text


def test_confirmation_with_commission():
    text = build_confirmation_text(
        request_id=5,
        proyekt="Garant Bank",
        requested=60000,
        actual=60600,
        komissiya=600,
        source=Source.CAPTION,
    )
    assert "So'ralgan: 60 000 so'm" in text
    assert "Chekda: 60 600 so'm (izohdan)" in text
    assert "💸 Komissiya: 600 so'm" in text
    assert "mos kelmayapti" not in text


def test_confirmation_warns_on_mismatch():
    text = build_confirmation_text(
        request_id=14,
        proyekt="Garant test das",
        requested=8770000,
        actual=700000,
        komissiya=-8070000,
        source=Source.AI,
        ai_note="ishonch: yuqori",
    )
    assert "⚠️ Summalar mos kelmayapti — tekshiring!" in text
    assert "Chekda: 700 000 so'm (chekdan o'qildi, ishonch: yuqori)" in text
    assert "Farq: 8 070 000 so'm kam" in text


def test_confirmation_marks_replacement():
    text = build_confirmation_text(
        request_id=3,
        proyekt="X",
        requested=1000,
        actual=1000,
        komissiya=0,
        source=Source.CAPTION,
        was_paid=True,
    )
    assert text.startswith("♻️ #3 cheki yangilandi")
