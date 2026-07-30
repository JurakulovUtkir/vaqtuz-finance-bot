from app.domain.analytics import by_channel, by_project, price_dynamics
from tests.factories import make_request


def test_by_project_sorted_and_counted():
    rows = [
        make_request(1, proyekt="A", summa=10000),
        make_request(2, proyekt="B", summa=50000),
        make_request(3, proyekt="A", summa=10000),
    ]
    stats = by_project(rows)
    assert [(s.key, s.count, s.total) for s in stats] == [("B", 1, 50000), ("A", 2, 20000)]


def test_by_channel_normalises_links():
    rows = [
        make_request(1, resurs="https://t.me/kanal", summa=1000),
        make_request(2, resurs="t.me/kanal", summa=3000),
    ]
    stats = by_channel(rows)
    assert len(stats) == 1
    assert stats[0].key == "@kanal"
    assert stats[0].count == 2
    assert stats[0].average == 2000


def test_average_is_rounded_to_whole_sum():
    rows = [make_request(1, summa=1000), make_request(2, summa=1003)]
    assert by_channel(rows)[0].average == 1002  # 1001.5 -> 1002

    # Python bankers' rounding ishlatadi: 1000.5 -> 1000
    rows = [make_request(1, summa=1000), make_request(2, summa=1001)]
    assert by_channel(rows)[0].average == 1000


def test_average_of_empty_group_is_zero():
    from app.domain.analytics import GroupStat

    assert GroupStat(key="x", count=0, total=0).average == 0


def test_price_dynamics_detects_increase():
    previous = [make_request(1, resurs="https://t.me/a", summa=1000000)]
    current = [make_request(2, resurs="https://t.me/a", summa=1500000)]
    (change,) = price_dynamics(current, previous)
    assert change.channel == "@a"
    assert change.previous_average == 1000000
    assert change.current_average == 1500000
    assert change.ratio == 0.5
    assert change.is_new is False


def test_price_dynamics_marks_new_channel():
    (change,) = price_dynamics([make_request(1, resurs="https://t.me/yangi")], [])
    assert change.is_new is True
    assert change.previous_average is None
    assert change.ratio == 0.0


def test_price_dynamics_orders_biggest_rise_first():
    previous = [
        make_request(1, resurs="https://t.me/a", summa=1000000),
        make_request(2, resurs="https://t.me/b", summa=1000000),
    ]
    current = [
        make_request(3, resurs="https://t.me/a", summa=1100000),  # +10%
        make_request(4, resurs="https://t.me/b", summa=2000000),  # +100%
        make_request(5, resurs="https://t.me/c", summa=500000),  # yangi
    ]
    changes = price_dynamics(current, previous)
    assert [c.channel for c in changes] == ["@b", "@a", "@c"]
    assert changes[-1].is_new is True


def test_price_dynamics_handles_decrease():
    previous = [make_request(1, resurs="https://t.me/a", summa=1000000)]
    current = [make_request(2, resurs="https://t.me/a", summa=800000)]
    (change,) = price_dynamics(current, previous)
    assert change.ratio == -0.2
