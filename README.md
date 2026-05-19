# LagLens

LagLens is an open-source gaming latency diagnostics tool. It helps players
measure ping, jitter, packet loss, route hops, and local network warning signs
before blaming the game server.

It does not promise impossible "instant ping reduction." Instead, it finds
avoidable latency: unstable Wi-Fi, packet loss, congestion, bad routes, DNS or
region mistakes, and background network usage.

## What it does today

- Runs repeatable latency scans against a game server, IP, or hostname.
- Reports min, average, and max ping plus jitter and packet loss.
- Optionally traces the route to show first-hop and path-level issues.
- Produces plain text or JSON output for sharing results.
- Lists active process network connections when installed with the process extra.
- Gives practical, safe recommendations without packet tampering or game hooks.

## Install from source

```powershell
git clone https://github.com/N0rd9/LagLens.git
cd LagLens
py -m pip install -e ".[dev,process]"
```

Linux/macOS:

```bash
python -m pip install -e ".[dev,process]"
```

## Quick start

Scan a known game server or any reliable host:

```bash
laglens scan 1.1.1.1 --count 12
```

Include a route trace:

```bash
laglens scan example.com --trace
```

Export JSON:

```bash
laglens scan 8.8.8.8 --json
```

List active process connections:

```bash
laglens processes --name valorant
```

## Example output

```text
LagLens scan: 1.1.1.1
Resolved IPs: 1.1.1.1
Packets: 12 sent / 12 received / 0.0% loss
Latency: min 13.2 ms | avg 15.6 ms | max 28.4 ms | jitter 3.1 ms

Advice
[ok] Connection looks stable from this sample.
```

## Safety model

LagLens stays outside the game process. It does not inject DLLs, hook memory,
alter packets, spoof traffic, or bypass anti-cheat systems. The project is
about measurement and safe operating-system/network recommendations.

## Roadmap

- Game profile presets for common regions and server hostnames.
- Before/after comparison reports.
- Background congestion detection.
- Windows QoS/DSCP guidance with explicit user confirmation.
- Desktop dashboard once the CLI diagnostics are solid.

## Development

```bash
python -m pip install -e ".[dev]"
pytest
```

## License

MIT
