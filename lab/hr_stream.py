"""Stream Heart Rate Measurement (0x2A37) -> CSV, with automatic reconnection.

  python -m lab.hr_stream                       # attach to the first device advertising 0x180D
  python -m lab.hr_stream --id UUID --minutes 10

Every row is an event: `data` (one notification), or `connect` / `disconnect` / `stall` / `retry`.
Gaps caused by disconnections therefore stay *in the file*, labelled: the report separates them from silent ones.
Stops on Ctrl-C or when --minutes elapses.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import time
from datetime import datetime, timezone
from pathlib import Path

from bleak import BleakClient, BleakScanner

from lab.hrm import HR_MEASUREMENT, HR_SERVICE, parse_hrm

CAPTURES = Path(__file__).parent / "captures"
STALL_S = 10.0  # connected but silent for this long -> force a reconnect
FIRST_DATA_S = 30.0  # the first notification can be late (in-app confirmation, sensor warm-up)
FIELDS = ["t_utc", "t_mono", "event", "bpm", "contact", "energy_kj", "rr_ms", "raw_hex", "note"]


class Recorder:
    def __init__(self, path: Path):
        self.f = path.open("w", newline="")
        self.w = csv.DictWriter(self.f, FIELDS)
        self.w.writeheader()
        self.n = self.n_rr = 0
        self.last_data = time.monotonic()

    def event(self, kind: str, note: str = "", **kw) -> None:
        self.w.writerow({"t_utc": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                         "t_mono": f"{time.monotonic():.3f}", "event": kind, "note": note, **kw})
        self.f.flush()
        if kind != "data":
            print(f"  · {kind} {note}")

    def on_notify(self, _char, data: bytearray) -> None:
        self.last_data = time.monotonic()
        try:
            m = parse_hrm(bytes(data))
        except ValueError as e:
            self.event("malformed", note=str(e), raw_hex=bytes(data).hex())
            return
        self.n += 1
        self.n_rr += len(m.rr_ms)
        self.event("data", bpm=m.bpm, contact="" if m.contact is None else int(m.contact),
                   energy_kj="" if m.energy_kj is None else m.energy_kj,
                   rr_ms=" ".join(f"{r:.1f}" for r in m.rr_ms), raw_hex=bytes(data).hex())
        rr = f"  RR {', '.join(f'{r:.0f}' for r in m.rr_ms)} ms" if m.rr_ms else "  (no RR)"
        print(f"\r{m.bpm:>3} bpm{rr:<40} [{self.n} notifications, {self.n_rr} RR]", end="", flush=True)


async def find_device(dev_id: str | None):
    if dev_id:
        return await BleakScanner.find_device_by_address(dev_id, timeout=15)
    return await BleakScanner.find_device_by_filter(
        lambda d, adv: HR_SERVICE in [u.lower() for u in adv.service_uuids], timeout=15)


async def run(dev_id: str | None, minutes: float | None, out: Path) -> None:
    rec = Recorder(out)
    deadline = time.monotonic() + minutes * 60 if minutes else float("inf")
    backoff = 1.0
    print(f"→ {out}")
    try:
        while time.monotonic() < deadline:
            dev = await find_device(dev_id)
            if dev is None:
                rec.event("retry", note=f"device not found, retrying in {backoff:.0f}s")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 15)
                continue
            dropped = asyncio.Event()
            try:
                async with BleakClient(dev, disconnected_callback=lambda _c: dropped.set(), timeout=20) as client:
                    rec.event("connect", note=f"{dev.address} {dev.name or ''}".strip())
                    await client.start_notify(HR_MEASUREMENT, rec.on_notify)
                    connected_at = rec.last_data = time.monotonic()
                    n_at_connect = rec.n
                    backoff = 1.0
                    while not dropped.is_set() and time.monotonic() < deadline:
                        await asyncio.sleep(0.5)
                        limit = STALL_S if rec.n > n_at_connect else FIRST_DATA_S
                        if time.monotonic() - max(rec.last_data, connected_at) > limit:
                            rec.event("stall", note=f"no notification for {limit:.0f}s")
                            break
                    remote = dropped.is_set()  # read before leaving the context: a local close fires the same callback
                print()
                rec.event("disconnect", note="remote" if remote else "local")
            except Exception as e:  # the Air allows one connection at a time and drops it: retry, never die
                print()
                rec.event("retry", note=f"{type(e).__name__}: {e}")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 15)
    finally:
        rec.event("end")
        rec.f.close()
        print(f"\ndone: {rec.n} notifications, {rec.n_rr} RR -> report: python -m lab.stream_report {out}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--id", help="CoreBluetooth UUID (from ble_scan); if omitted, first device advertising 0x180D")
    p.add_argument("--minutes", type=float)
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    CAPTURES.mkdir(exist_ok=True)
    out = a.out or CAPTURES / f"hr_{datetime.now():%Y%m%d_%H%M%S}.csv"
    try:
        asyncio.run(run(a.id, a.minutes, out))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
