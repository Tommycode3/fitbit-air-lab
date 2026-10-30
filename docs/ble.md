# Air BLE — observed facts

Only things seen in the captures. Hypotheses are marked as such.

## Advertising (2026-09-25)
- Name `Google Fitbit Air`; advertises 0x180D only when "Share heart rate" is enabled.
- Notifications start only after the request is confirmed in the Google Health app.

## GATT (`lab/captures/gatt_20260925_123326.json` (local capture, not published))
| Service | Characteristics | Notes |
|---|---|---|
| 0x180A Device Information | manufacturer `Fitbit`, model `67`, firmware `67.20001.253.2` | serial number readable in plaintext |
| 0x180D Heart Rate | 0x2A37 notify | no 0x2A38 (body sensor location), no 0x2A39 (control point) |
| `abbafd00-e56a-484c-b832-8b17cf6cbfe8` | fd01 read/notify, fd02 read/notify, fd03 read | proprietary, readable without pairing |
| `abbaff00-…` | ff01 write-no-response, ff02 notify | proprietary; *hypothesis*: command/response channel |
| `ac2f0045-8182-4be5-91e0-2992e6b40ebb` | 0145 read, 2845 write | 0145 contains the UUID of 2845 |
| `4eee1c00-4133-479b-8663-02c84bdc14be` | 7 notify/indicate/write characteristics | 1c03 read → GATT error 133 (probably requires encryption) |

No writes have been made to proprietary characteristics.

## Heart Rate Measurement (`lab/captures/hr_probe.csv` (local capture, not published), 60 s probe)
- Flags always `0x01`: HR uint16, **sensor contact not supported, energy absent, RR absent**.
- 1 Hz cadence. Values 63–67 bpm at rest.
- **Consequence: no live HRV via standard BLE.** Live HRV, RR-based breathwork and rMSSD from the stream
  move from ✅ to ❓ (they depend on Phase 4 or Phase 5).
