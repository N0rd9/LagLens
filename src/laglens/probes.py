from __future__ import annotations

import platform
import re
import shutil
import socket
import statistics
import subprocess

from .models import PingStats, RouteHop


_TIME_RE = re.compile(
    r"(?:time|tempo)(?P<op>[=<])\s*(?P<value>\d+(?:\.\d+)?)\s*ms",
    re.I,
)
_WINDOWS_PACKETS_RE = re.compile(
    r"(?:sent|enviados)\s*=\s*(?P<sent>\d+).*?"
    r"(?:received|recebidos)\s*=\s*(?P<received>\d+).*?"
    r"(?:lost|perdidos)\s*=\s*(?P<lost>\d+).*?"
    r"\((?P<loss>\d+(?:\.\d+)?)%\s*(?:loss|de perda|perda)?\)",
    re.I | re.S,
)
_UNIX_PACKETS_RE = re.compile(
    r"(?P<sent>\d+)\s+packets transmitted,\s*"
    r"(?P<received>\d+)(?:\s+packets)? received,.*?"
    r"(?P<loss>\d+(?:\.\d+)?)%\s+packet loss",
    re.I | re.S,
)
_IP_RE = re.compile(r"(?<![\w:])(?:\d{1,3}\.){3}\d{1,3}(?![\w:])")
_RTT_RE = re.compile(r"(?P<op><)?\s*(?P<value>\d+(?:\.\d+)?)\s*ms", re.I)


def resolve_target(target: str) -> list[str]:
    """Resolve a hostname without failing the whole scan on DNS errors."""
    try:
        results = socket.getaddrinfo(target, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return []

    ips: list[str] = []
    for family, _, _, _, sockaddr in results:
        if family in {socket.AF_INET, socket.AF_INET6}:
            ip = sockaddr[0]
            if ip not in ips:
                ips.append(ip)
    return ips


def run_ping(target: str, count: int = 8, interval: float = 0.2) -> PingStats:
    system = platform.system().lower()
    if system == "windows":
        command = ["ping", "-n", str(count), "-w", "1000", target]
        timeout = max(5, count + 5)
    elif system == "darwin":
        command = ["ping", "-c", str(count), "-i", str(interval), target]
        timeout = max(5, int(count * max(interval, 1) + 5))
    else:
        command = [
            "ping",
            "-c",
            str(count),
            "-i",
            str(interval),
            "-W",
            "1",
            target,
        ]
        timeout = max(5, int(count * max(interval, 1) + 5))

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return PingStats(
            target=target,
            sent=count,
            received=0,
            loss_percent=100.0,
            raw_output=str(exc),
        )

    output = "\n".join(part for part in [completed.stdout, completed.stderr] if part)
    return parse_ping_output(output, target=target, fallback_sent=count)


def parse_ping_output(
    output: str, target: str = "", fallback_sent: int | None = None
) -> PingStats:
    samples = [_coerce_ms(match) for match in _TIME_RE.finditer(output)]
    sent, received, loss_percent = _parse_packet_summary(output)

    if sent is None:
        sent = fallback_sent if fallback_sent is not None else len(samples)
    if received is None:
        received = len(samples)
    if loss_percent is None:
        loss_percent = _loss_percent(sent, received)

    min_ms = min(samples) if samples else None
    avg_ms = statistics.fmean(samples) if samples else None
    max_ms = max(samples) if samples else None
    jitter_ms = _jitter(samples) if samples else None

    return PingStats(
        target=target,
        sent=sent,
        received=received,
        loss_percent=round(loss_percent, 2),
        samples_ms=[round(sample, 3) for sample in samples],
        min_ms=_round_optional(min_ms),
        avg_ms=_round_optional(avg_ms),
        max_ms=_round_optional(max_ms),
        jitter_ms=_round_optional(jitter_ms),
        raw_output=output,
    )


def run_trace(target: str, max_hops: int = 20) -> list[RouteHop]:
    system = platform.system().lower()
    if system == "windows":
        command = ["tracert", "-d", "-h", str(max_hops), target]
    elif shutil.which("traceroute"):
        command = ["traceroute", "-n", "-m", str(max_hops), target]
    elif shutil.which("tracepath"):
        command = ["tracepath", target]
    else:
        return []

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=max(10, max_hops * 2),
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []

    output = "\n".join(part for part in [completed.stdout, completed.stderr] if part)
    return parse_route_output(output)


def parse_route_output(output: str) -> list[RouteHop]:
    hops: list[RouteHop] = []
    for line in output.splitlines():
        match = re.match(r"^\s*(?P<index>\d+)\s+(?P<body>.+)$", line)
        if not match:
            continue

        index = int(match.group("index"))
        body = match.group("body").strip()
        ip_match = _IP_RE.search(body)
        rtts = [_coerce_route_ms(item) for item in _RTT_RE.finditer(body)]
        timed_out = "*" in body and not rtts

        hops.append(
            RouteHop(
                index=index,
                host=ip_match.group(0) if ip_match else None,
                ip=ip_match.group(0) if ip_match else None,
                best_rtt_ms=round(min(rtts), 3) if rtts else None,
                timed_out=timed_out,
            )
        )
    return hops


def _parse_packet_summary(output: str) -> tuple[int | None, int | None, float | None]:
    for pattern in (_WINDOWS_PACKETS_RE, _UNIX_PACKETS_RE):
        match = pattern.search(output)
        if match:
            return (
                int(match.group("sent")),
                int(match.group("received")),
                float(match.group("loss")),
            )
    return None, None, None


def _loss_percent(sent: int, received: int) -> float:
    if sent <= 0:
        return 0.0
    return max(0.0, min(100.0, ((sent - received) / sent) * 100))


def _jitter(samples: list[float]) -> float:
    if len(samples) < 2:
        return 0.0
    deltas = [abs(current - previous) for previous, current in zip(samples, samples[1:])]
    return statistics.fmean(deltas)


def _coerce_ms(match: re.Match[str]) -> float:
    value = float(match.group("value"))
    return value / 2 if match.group("op") == "<" else value


def _coerce_route_ms(match: re.Match[str]) -> float:
    value = float(match.group("value"))
    return value / 2 if match.group("op") else value


def _round_optional(value: float | None) -> float | None:
    return round(value, 3) if value is not None else None
