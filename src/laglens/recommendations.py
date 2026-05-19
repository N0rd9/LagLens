from __future__ import annotations

from .models import Advice, PingStats, RouteHop


def build_recommendations(stats: PingStats, route: list[RouteHop] | None = None) -> list[Advice]:
    route = route or []
    advice: list[Advice] = []

    if not stats.has_samples:
        return [
            Advice(
                level="critical",
                title="No ping replies received",
                detail=(
                    "The target did not answer this scan. Check the host, firewall, "
                    "VPN, or whether the game blocks ICMP ping."
                ),
            )
        ]

    if stats.loss_percent >= 5:
        advice.append(
            Advice(
                level="critical",
                title="High packet loss",
                detail=(
                    "Packet loss this high usually feels worse than raw ping. Try "
                    "Ethernet, pause downloads, reboot the router, and test another "
                    "device on the same network."
                ),
            )
        )
    elif stats.loss_percent >= 1:
        advice.append(
            Advice(
                level="warning",
                title="Packet loss detected",
                detail=(
                    "Even small loss can create rubber-banding in shooters. Repeat "
                    "the scan and compare Wi-Fi versus Ethernet if possible."
                ),
            )
        )

    if stats.jitter_ms is not None and stats.jitter_ms >= 25:
        advice.append(
            Advice(
                level="warning",
                title="Unstable latency",
                detail=(
                    "Jitter is high. This often points to Wi-Fi interference, router "
                    "bufferbloat, or background uploads."
                ),
            )
        )

    if stats.avg_ms is not None and stats.avg_ms >= 120:
        advice.append(
            Advice(
                level="info",
                title="High average ping",
                detail=(
                    "Average ping is mostly distance and routing. Check that the game "
                    "matched you to the closest region before changing local settings."
                ),
            )
        )

    first_responsive_hop = next(
        (hop for hop in route if hop.best_rtt_ms is not None),
        None,
    )
    if first_responsive_hop and first_responsive_hop.best_rtt_ms >= 15:
        advice.append(
            Advice(
                level="warning",
                title="Local network delay",
                detail=(
                    "The first responsive hop is already slow, so the issue may be "
                    "inside your home network or ISP access link."
                ),
            )
        )

    if len(route) >= 18:
        advice.append(
            Advice(
                level="info",
                title="Long route",
                detail=(
                    "The route has many hops. A VPN or a different game region may "
                    "help only if it produces a shorter, more stable route."
                ),
            )
        )

    if not advice:
        advice.append(
            Advice(
                level="ok",
                title="Connection looks stable",
                detail="This sample did not show obvious local packet loss or jitter.",
            )
        )

    return advice
