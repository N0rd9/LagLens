from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class PingStats:
    target: str
    sent: int
    received: int
    loss_percent: float
    samples_ms: list[float] = field(default_factory=list)
    min_ms: float | None = None
    avg_ms: float | None = None
    max_ms: float | None = None
    jitter_ms: float | None = None
    raw_output: str = field(default="", repr=False)

    @property
    def has_samples(self) -> bool:
        return bool(self.samples_ms)

    def to_dict(self, include_raw: bool = False) -> dict[str, Any]:
        payload = asdict(self)
        if not include_raw:
            payload.pop("raw_output", None)
        return payload


@dataclass(frozen=True)
class RouteHop:
    index: int
    host: str | None = None
    ip: str | None = None
    best_rtt_ms: float | None = None
    timed_out: bool = False


@dataclass(frozen=True)
class Advice:
    level: str
    title: str
    detail: str


@dataclass(frozen=True)
class ScanReport:
    target: str
    resolved_ips: list[str]
    ping: PingStats
    route: list[RouteHop] = field(default_factory=list)
    advice: list[Advice] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self, include_raw: bool = False) -> dict[str, Any]:
        return {
            "target": self.target,
            "resolved_ips": self.resolved_ips,
            "ping": self.ping.to_dict(include_raw=include_raw),
            "route": [asdict(hop) for hop in self.route],
            "advice": [asdict(item) for item in self.advice],
            "created_at": self.created_at,
        }
