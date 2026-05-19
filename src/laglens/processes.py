from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class ProcessConnection:
    pid: int
    name: str
    remote_ip: str
    remote_port: int
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def list_process_connections(
    name_filter: str | None = None,
    limit: int = 25,
) -> list[ProcessConnection]:
    try:
        import psutil
    except ImportError as exc:
        raise RuntimeError(
            "Process scanning requires psutil. Install with: "
            "python -m pip install 'laglens[process]'"
        ) from exc

    lowered_filter = name_filter.lower() if name_filter else None
    results: list[ProcessConnection] = []

    for proc in psutil.process_iter(["pid", "name"]):
        name = proc.info.get("name") or ""
        if lowered_filter and lowered_filter not in name.lower():
            continue

        try:
            connections = proc.net_connections(kind="inet")
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue

        for conn in connections:
            if not conn.raddr:
                continue
            remote_ip = getattr(conn.raddr, "ip", conn.raddr[0])
            remote_port = getattr(conn.raddr, "port", conn.raddr[1])
            results.append(
                ProcessConnection(
                    pid=proc.info["pid"],
                    name=name,
                    remote_ip=remote_ip,
                    remote_port=remote_port,
                    status=conn.status,
                )
            )
            if len(results) >= limit:
                return results

    return results
