from app.domain.parsing import parse_amount, parse_request


def test_uzbek_russian_mixed():
    parsed = parse_request(
        "Resurs: https://t.me/Bukhara\n"
        "Proyekt: Garant Bank\n"
        "Summa: 60 000 сум\n"
        "Karta: 5614681255855243"
    )
    assert parsed is not None
    assert parsed.resurs == "https://t.me/Bukhara"
    assert parsed.proyekt == "Garant Bank"
    assert parsed.summa_value == 60000
    assert parsed.karta == "5614681255855243"


def test_fully_russian_labels():
    parsed = parse_request(
        "Ресурс: kanal\nПроект: Kapital\nСумма: 1 200 000\nКарта: 8600 1234 5678 9012"
    )
    assert parsed is not None
    assert parsed.summa_value == 1200000
    assert parsed.karta == "8600123456789012"


def test_value_on_next_line():
    parsed = parse_request(
        "Resurs:\nhttps://t.me/x\nProyekt:\nUzum\nSumma:\n450000\nKarta:\n9860123412341234"
    )
    assert parsed is not None
    assert parsed.proyekt == "Uzum"
    assert parsed.summa_value == 450000


def test_field_order_does_not_matter():
    parsed = parse_request(
        "Karta: 8600000011112222\nSumma: 75 000 so'm\nProyekt: Test\nResurs: t.me/y"
    )
    assert parsed is not None
    assert parsed.summa_value == 75000


def test_loyiha_is_accepted_as_proyekt():
    parsed = parse_request("Resurs: a\nLoyiha: B\nSumma: 100\nKarta: 8600")
    assert parsed is not None
    assert parsed.proyekt == "B"


def test_plain_chat_message_is_ignored():
    assert parse_request("salom bugun to'lov qilamizmi?") is None


def test_incomplete_request_is_ignored():
    assert parse_request("Resurs: a\nSumma: 100") is None


def test_empty_text():
    assert parse_request(None) is None
    assert parse_request("") is None


def test_summa_without_digits_becomes_zero():
    parsed = parse_request("Resurs: a\nProyekt: b\nSumma: keyin aytaman\nKarta: 8600")
    assert parsed is not None
    assert parsed.summa_value == 0


def test_parse_amount():
    assert parse_amount("606000") == 606000
    assert parse_amount("606 000 so'm") == 606000
    assert parse_amount("chek") is None
    assert parse_amount(None) is None
