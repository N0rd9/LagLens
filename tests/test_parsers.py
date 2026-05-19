from laglens.probes import parse_ping_output, parse_route_output


def test_parse_windows_ping_output() -> None:
    output = """
Pinging 1.1.1.1 with 32 bytes of data:
Reply from 1.1.1.1: bytes=32 time=14ms TTL=57
Reply from 1.1.1.1: bytes=32 time=18ms TTL=57
Reply from 1.1.1.1: bytes=32 time=16ms TTL=57
Reply from 1.1.1.1: bytes=32 time=20ms TTL=57

Ping statistics for 1.1.1.1:
    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),
Approximate round trip times in milli-seconds:
    Minimum = 14ms, Maximum = 20ms, Average = 17ms
"""
    stats = parse_ping_output(output, target="1.1.1.1")

    assert stats.sent == 4
    assert stats.received == 4
    assert stats.loss_percent == 0
    assert stats.min_ms == 14
    assert stats.avg_ms == 17
    assert stats.max_ms == 20
    assert stats.jitter_ms == 3.333


def test_parse_portuguese_windows_ping_output() -> None:
    output = """
Disparando 127.0.0.1 com 32 bytes de dados:
Resposta de 127.0.0.1: bytes=32 tempo<1ms TTL=128
Resposta de 127.0.0.1: bytes=32 tempo=1ms TTL=128

Estatisticas do Ping para 127.0.0.1:
    Pacotes: Enviados = 2, Recebidos = 2, Perdidos = 0 (0% de perda),
"""
    stats = parse_ping_output(output, target="127.0.0.1")

    assert stats.sent == 2
    assert stats.received == 2
    assert stats.loss_percent == 0
    assert stats.samples_ms == [0.5, 1.0]


def test_parse_unix_ping_output_with_loss() -> None:
    output = """
PING 8.8.8.8 (8.8.8.8): 56 data bytes
64 bytes from 8.8.8.8: icmp_seq=0 ttl=117 time=12.1 ms
64 bytes from 8.8.8.8: icmp_seq=2 ttl=117 time=22.3 ms

--- 8.8.8.8 ping statistics ---
3 packets transmitted, 2 received, 33.333% packet loss
round-trip min/avg/max/stddev = 12.1/17.2/22.3/5.1 ms
"""
    stats = parse_ping_output(output, target="8.8.8.8")

    assert stats.sent == 3
    assert stats.received == 2
    assert stats.loss_percent == 33.33
    assert stats.samples_ms == [12.1, 22.3]


def test_parse_windows_route_output() -> None:
    output = """
Tracing route to 1.1.1.1 over a maximum of 30 hops

  1     1 ms    <1 ms     1 ms  192.168.1.1
  2    12 ms    11 ms    13 ms  10.10.0.1
  3     *        *        *     Request timed out.
"""
    hops = parse_route_output(output)

    assert len(hops) == 3
    assert hops[0].ip == "192.168.1.1"
    assert hops[0].best_rtt_ms == 0.5
    assert hops[2].timed_out is True
