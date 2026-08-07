from app.bot.handlers.menu import build_menu
from app.domain.formatting import chunk_text


def _callbacks(markup):
    return [b.callback_data for row in markup.inline_keyboard for b in row]


def test_menu_has_every_action():
    assert set(_callbacks(build_menu())) == {
        "rep:today",
        "rep:week",
        "rep:month",
        "rep:pending",
        "noop",
        "xls:month",
        "xls:prev",
        "xls:all",
        "bak:now",
    }


def test_restore_button_is_disabled():
    """Ko'chirish tugagach o'chirilgan — kodi turibdi, tugmasi yo'q."""
    assert "bak:restore" not in _callbacks(build_menu())


def test_menu_buttons_are_labelled_in_uzbek():
    labels = [b.text for row in build_menu().inline_keyboard for b in row]
    assert "📅 Bugun" in labels
    assert "⏳ Kutilayotgan to'lovlar" in labels
    assert "📥 Butun tarix" in labels
    assert "💾 Hozir zaxira olish" in labels


def test_callback_data_stays_within_telegram_limit():
    """Telegram callback_data uchun 64 bayt chegara qo'yadi."""
    for data in _callbacks(build_menu()):
        assert len(data.encode()) <= 64


def test_short_text_is_not_split():
    assert chunk_text("qisqa matn") == ["qisqa matn"]


def test_long_text_splits_on_line_boundaries():
    text = "\n".join(f"qator {i}" for i in range(1000))
    chunks = chunk_text(text, limit=200)
    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)
    # Qatorlar buzilmasligi kerak
    assert "\n".join(chunks).replace("\n", "") == text.replace("\n", "")


def test_single_line_longer_than_limit_is_force_split():
    chunks = chunk_text("x" * 500, limit=100)
    assert all(len(c) <= 100 for c in chunks)
    assert "".join(chunks) == "x" * 500
