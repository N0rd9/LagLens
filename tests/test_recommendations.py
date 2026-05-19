from laglens.models import PingStats, RouteHop
from laglens.recommendations import build_recommendations


def test_recommends_packet_loss_before_generic_ok() -> None:
    stats = PingStats(
        target="game.example",
        sent=10,
        received=9,
        loss_percent=10.0,
        samples_ms=[20, 21, 19],
        min_ms=19,
        avg_ms=20,
        max_ms=21,
        jitter_ms=1,
    )

    advice = build_recommendations(stats)

    assert advice[0].level == "critical"
    assert "packet loss" in advice[0].title.lower()


def test_recommends_local_network_delay_from_first_hop() -> None:
    stats = PingStats(
        target="game.example",
        sent=4,
        received=4,
        loss_percent=0.0,
        samples_ms=[30, 31, 32, 33],
        min_ms=30,
        avg_ms=31.5,
        max_ms=33,
        jitter_ms=1,
    )
    route = [RouteHop(index=1, ip="192.168.1.1", best_rtt_ms=18)]

    advice = build_recommendations(stats, route)

    assert any(item.title == "Local network delay" for item in advice)


def test_stable_connection_gets_ok_message() -> None:
    stats = PingStats(
        target="game.example",
        sent=5,
        received=5,
        loss_percent=0.0,
        samples_ms=[12, 13, 12, 13, 12],
        min_ms=12,
        avg_ms=12.4,
        max_ms=13,
        jitter_ms=1,
    )

    advice = build_recommendations(stats)

    assert len(advice) == 1
    assert advice[0].level == "ok"
