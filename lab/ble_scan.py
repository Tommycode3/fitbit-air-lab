"""BLE scan: find the Air and optionally dump its full GATT table.

  python -m lab.ble_scan                 # list devices, highlight candidates
  python -m lab.ble_scan --connect ID    # services, characteristics, descriptors, reads -> JSON in lab/captures/

On macOS the ID is a CoreBluetooth UUID, not the MAC address.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path

from bleak import BleakClient, BleakScanner

from lab.hrm import HR_SERVICE

HINTS = ("fitbit", "air", "google", "pixel")
CAPTURES = Path(__file__).parent / "captures"


async def scan(seconds: float) -> None:
    found = await BleakScanner.discover(timeout=seconds, return_adv=True)
    rows = sorted(found.values(), key=lambda t: t[1].rssi, reverse=True)
    for dev, adv in rows:
        name = adv.local_name or dev.name or ""
        hr = HR_SERVICE in [u.lower() for u in adv.service_uuids]
        mark = "HR " if hr else ("?  " if any(h in name.lower() for h in HINTS) else "   ")
        print(f"{mark}{adv.rssi:>4} dBm  {dev.address}  {name!r}  services={adv.service_uuids}"
              + (f"  mfr={ {k: v.hex() for k, v in adv.manufacturer_data.items()} }" if adv.manufacturer_data else ""))
    print(f"\n{len(rows)} devices. 'HR' = advertises 0x180D (requires 'Share heart rate' enabled on the Air).")


async def dump(address: str) -> None:
    out: dict = {"address": address, "at": datetime.now().isoformat(), "services": []}
    async with BleakClient(address, timeout=20) as client:
        for svc in client.services:
            s = {"uuid": svc.uuid, "description": svc.description, "characteristics": []}
            for ch in svc.characteristics:
                c = {"uuid": ch.uuid, "handle": ch.handle, "description": ch.description,
                     "properties": ch.properties, "descriptors": []}
                if "read" in ch.properties:
                    try:
                        val = await client.read_gatt_char(ch)
                        c["value_hex"] = val.hex()
                        c["value_utf8"] = val.decode("utf-8", "replace")
                    except Exception as e:  # reads that need pairing/encryption: record the error, don't abort
                        c["read_error"] = repr(e)
                for d in ch.descriptors:
                    entry = {"uuid": d.uuid, "handle": d.handle}
                    try:
                        entry["value_hex"] = (await client.read_gatt_descriptor(d.handle)).hex()
                    except Exception as e:
                        entry["read_error"] = repr(e)
                    c["descriptors"].append(entry)
                s["characteristics"].append(c)
            out["services"].append(s)

    for s in out["services"]:
        print(f"[{s['uuid']}] {s['description']}")
        for c in s["characteristics"]:
            v = c.get("value_hex") or c.get("read_error", "")
            print(f"   {c['uuid']}  {','.join(c['properties']):<40} {v[:60]}")
    CAPTURES.mkdir(exist_ok=True)
    path = CAPTURES / f"gatt_{datetime.now():%Y%m%d_%H%M%S}.json"
    path.write_text(json.dumps(out, indent=2))
    print(f"\ndump → {path}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--seconds", type=float, default=8.0)
    p.add_argument("--connect", metavar="ID")
    a = p.parse_args()
    asyncio.run(dump(a.connect) if a.connect else scan(a.seconds))


if __name__ == "__main__":
    main()
