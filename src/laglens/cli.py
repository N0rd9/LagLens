from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .models import ScanReport
from .probes import resolve_target, run_ping, run_trace
from .processes import list_process_connections
from .recommendations import build_recommendations


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="laglens",
        description="Gaming latency diagnostics for ping, jitter, packet loss, and routes.",
    )
    parser.add_argument("--version", action="version", version=f"LagLens {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Scan latency to a host or IP.")
    scan.add_argument("target", help="Hostname or IP address to scan.")
    scan.add_argument("--count", type=int, default=8, help="Ping sample count.")
    scan.add_argument(
        "--interval",
        type=float,
        default=0.2,
        help="Seconds between ping samples where supported.",
    )
    scan.add_argument("--trace", action="store_true", help="Include route tracing.")
    scan.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    scan.set_defaults(func=scan_command)

    processes = subparsers.add_parser(
        "processes",
        help="List active process network connections.",
    )
    processes.add_argument("--name", help="Filter processes by name.")
    processes.add_argument("--limit", type=int, default=25, help="Maximum rows to print.")
    processes.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    processes.set_defaults(func=processes_command)

    return parser


def scan_command(args: argparse.Namespace) -> int:
    count = max(1, min(args.count, 100))
    interval = max(0.1, min(args.interval, 5.0))

    resolved_ips = resolve_target(args.target)
    ping = run_ping(args.target, count=count, interval=interval)
    route = run_trace(args.target) if args.trace else []
    advice = build_recommendations(ping, route)
    report = ScanReport(
        target=args.target,
        resolved_ips=resolved_ips,
        ping=ping,
        route=route,
        advice=advice,
    )

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        print_scan_report(report)

    return 0 if ping.has_samples and ping.loss_percent < 100 else 2


def processes_command(args: argparse.Namespace) -> int:
    try:
        rows = list_process_connections(name_filter=args.name, limit=max(1, args.limit))
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps([row.to_dict() for row in rows], indent=2, sort_keys=True))
        return 0

    if not rows:
        print("No matching active remote connections found.")
        return 0

    print("PID     Process                         Remote")
    print("------  ------------------------------  -------------------------")
    for row in rows:
        process = row.name[:30]
        remote = f"{row.remote_ip}:{row.remote_port}"
        print(f"{row.pid:<6}  {process:<30}  {remote}")
    return 0


def print_scan_report(report: ScanReport) -> None:
    ping = report.ping
    print(f"LagLens scan: {report.target}")
    print(f"Resolved IPs: {', '.join(report.resolved_ips) if report.resolved_ips else 'unresolved'}")
    print(
        f"Packets: {ping.sent} sent / {ping.received} received / "
        f"{ping.loss_percent:.1f}% loss"
    )

    if ping.has_samples:
        print(
            "Latency: "
            f"min {_fmt_ms(ping.min_ms)} | "
            f"avg {_fmt_ms(ping.avg_ms)} | "
            f"max {_fmt_ms(ping.max_ms)} | "
            f"jitter {_fmt_ms(ping.jitter_ms)}"
        )
    else:
        print("Latency: no replies")

    if report.route:
        print()
        print("Route")
        for hop in report.route:
            label = hop.ip or "*"
            rtt = _fmt_ms(hop.best_rtt_ms) if hop.best_rtt_ms is not None else "timeout"
            print(f"{hop.index:>2}. {label:<15} {rtt}")

    print()
    print("Advice")
    for item in report.advice:
        print(f"[{item.level}] {item.title}: {item.detail}")


def _fmt_ms(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1f} ms"


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
