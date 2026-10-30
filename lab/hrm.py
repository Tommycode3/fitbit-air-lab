"""Parser for the Heart Rate Measurement characteristic (0x2A37).

Reference: Bluetooth SIG, Heart Rate Service 1.0, §3.1.
Flags (byte 0):
  bit 0    HR format: 0 = uint8, 1 = uint16
  bit 1-2  sensor contact: 0/1 = not supported, 2 = supported but not detected, 3 = supported and detected
  bit 3    energy expended present (uint16, kJ)
  bit 4    RR intervals present (uint16 each, unit 1/1024 s)
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

HR_SERVICE = "0000180d-0000-1000-8000-00805f9b34fb"
HR_MEASUREMENT = "00002a37-0000-1000-8000-00805f9b34fb"


@dataclass
class HrMeasurement:
    bpm: int
    contact: bool | None          # None = sensor does not support contact detection
    energy_kj: int | None
    rr_ms: list[float] = field(default_factory=list)
    flags: int = 0


def parse_hrm(data: bytes) -> HrMeasurement:
    if len(data) < 2:
        raise ValueError(f"payload too short: {data.hex()}")
    flags = data[0]
    i = 1
    if flags & 0x01:
        (bpm,) = struct.unpack_from("<H", data, i)
        i += 2
    else:
        bpm = data[i]
        i += 1

    contact_bits = (flags >> 1) & 0x03
    contact = None if contact_bits < 2 else contact_bits == 3

    energy = None
    if flags & 0x08:
        (energy,) = struct.unpack_from("<H", data, i)
        i += 2

    rr: list[float] = []
    if flags & 0x10:
        remaining = len(data) - i
        if remaining % 2:
            raise ValueError(f"RR field has odd length: {data.hex()}")
        for (raw,) in struct.iter_unpack("<H", data[i:]):
            rr.append(raw * 1000.0 / 1024.0)

    return HrMeasurement(bpm=bpm, contact=contact, energy_kj=energy, rr_ms=rr, flags=flags)
