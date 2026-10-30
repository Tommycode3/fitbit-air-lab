"""Passive listener on the Air's proprietary services. Read-only.

  python -m lab.listen --id UUID --seconds 120 --label "idle on wrist"

The only write is to the CCCD descriptor (0x2902) to enable notify/indicate, i.e. the
standard GATT subscription. No writes to proprietary characteristics.

Output: lab/captures/listen_<ts>.csv (t, uuid, kind, hex) + a per-characteristic summary
with lengths and byte entropy (~8 bit/byte on long payloads -> likely encrypted/compressed).
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import math
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from bleak import BleakClient, BleakScanner

CAPTURES = Path(__file__).parent / "captures"
STANDARD = ("00001800", "00001801", "0000180a", "0000180d")  # GAP, GATT, DevInfo, HR: not of interest here


def entropy_bits_per_byte(chunks: list[bytes]) -> float:
    data = b"".join(chunks)
    if not data:
        return 0.0
    counts = Counter(data)
    n = len(data)
    return -sum(c / n * math.log2(c / n) for c in counts.values())


async def run(dev_id: str, seconds: float, label: str) -> None:
    CAPTURES.mkdir(exist_ok=True)
    path = CAPTURES / f"listen_{datetime.now():%Y%m%d_%H%M%S}.csv"
    seen: dict[str, list[bytes]] = defaultdict(list)
    t0 = time.monotonic()

    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_s", "uuid", "kind", "hex", "label"])

        def log(uuid: str, kind: str, data: bytes) -> None:
            w.writerow([f"{time.monotonic() - t0:.3f}", uuid, kind, data.hex(), label])
            f.flush()
            seen[uuid].append(data)
            print(f"{time.monotonic() - t0:7.2f}s  {uuid[:8]}  {kind:<6} {data.hex()}")

        dev = await BleakScanner.find_device_by_address(dev_id, timeout=20)
        if dev is None:
            raise SystemExit("device not found (connected to something else? is the HR stream still running?)")
        async with BleakClient(dev, timeout=20) as c:
            chars = [ch for s in c.services if not s.uuid.startswith(STANDARD) for ch in s.characteristics]
            for ch in chars:
                if "read" in ch.properties:
                    try:
                        log(ch.uuid, "read", bytes(await c.read_gatt_char(ch)))
                    except Exception as e:
                        print(f"          {ch.uuid[:8]}  read   ERR {e}")
            for ch in chars:
                if {"notify", "indicate"} & set(ch.properties):
                    try:
                        await c.start_notify(ch, lambda sender, data, u=ch.uuid: log(u, "notif", bytes(data)))
                        print(f"          {ch.uuid[:8]}  sub    ok")
                    except Exception as e:
                        print(f"          {ch.uuid[:8]}  sub    ERR {e}")
            end = time.monotonic() + seconds
            while time.monotonic() < end and c.is_connected:
                await asyncio.sleep(0.5)

    print(f"\n→ {path}\n{'uuid':<38} {'n':>4} {'len':>9} {'H bit/B':>8}")
    for uuid, chunks in sorted(seen.items()):
        lens = sorted({len(x) for x in chunks})
        print(f"{uuid:<38} {len(chunks):>4} {str(lens)[:9]:>9} {entropy_bits_per_byte(chunks):>8.2f}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--id", required=True)
    p.add_argument("--seconds", type=float, default=120)
    p.add_argument("--label", default="", help="what you are doing during the capture (one action at a time)")
    a = p.parse_args()
    asyncio.run(run(a.id, a.seconds, a.label))


if __name__ == "__main__":
    main()
