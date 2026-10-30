# fitbit-air-lab

Bluetooth LE lab tools for the Google Fitbit Air: scan, dump the GATT table, record the standard Heart Rate stream to CSV with every disconnection logged, and check whether a recording is usable. The question I built them to answer was whether the Air sends RR intervals over the standard Heart Rate Service. It does not: 0x2A37 always carries flags `0x01`, a `uint16` heart rate at 1 Hz and nothing else, so live HRV over standard BLE is not possible on this device.

This is phase 0 of a personal recovery app on top of the band ([`docs/brief.md`](docs/brief.md)). Only the lab tools exist; `app/` and `backend/` are empty placeholders.

## Usage

Python 3.10+ and a machine with Bluetooth LE (developed on macOS, where device IDs are CoreBluetooth UUIDs, not MAC addresses). On the Air, enable "Share heart rate" in the Google Health app, otherwise it does not advertise the Heart Rate Service.

```sh
pip install -r requirements.txt

python -m lab.ble_scan                       # list nearby devices; "HR" marks 0x180D advertisers
python -m lab.ble_scan --connect <ID>        # full GATT dump -> lab/captures/gatt_<ts>.json
python -m lab.hr_stream --minutes 10         # HR + RR -> lab/captures/hr_<ts>.csv
python -m lab.stream_report lab/captures/hr_<ts>.csv   # exit criterion: PASS/FAIL, exit code 0/1
python -m lab.listen --id <ID> --seconds 120 --label "idle on wrist"   # passive listen on proprietary services

python -m pytest lab/tests                   # 8 tests, no hardware needed
```

`hr_stream` works with any device that implements the standard Heart Rate Service, such as chest straps or watches in broadcast mode.

## How it works

`lab/hrm.py` parses 0x2A37. Byte 0 is a flag field: bit 0 selects a `uint8` or `uint16` heart rate, bits 1-2 encode sensor contact (reported as `True` / `False` / `None`), bit 3 announces a `uint16` energy-expended field in kJ, and bit 4 announces zero or more `uint16` RR intervals in units of 1/1024 s:

$$
\mathrm{RR}_{\mathrm{ms}} = \mathrm{raw} \cdot \frac{1000}{1024}
$$

A truncated payload raises `ValueError`, which the recorder logs as a `malformed` event.

`lab/hr_stream.py` writes one CSV row per event, with both a UTC time and a monotonic timestamp. Disconnections are rows (`connect`, `disconnect`, `stall`, `retry`, `malformed`) instead of exceptions, so a gap in the data can later be classified as "the link dropped and we recovered" or "data silently stopped". A connection is stalled after 10 s without notifications (30 s for the first one, which can wait for confirmation in the app), and reconnection backs off as $t_k = \min(2^k, 15)$ s.

`lab/stream_report.py` takes the monotonic timestamps $t_1 < \dots < t_N$ of data rows and calls any $t_{i+1} - t_i > 3$ s a gap. A gap is handled if a `disconnect`, `stall` or `retry` event falls inside it. The exit criterion is

$$
t_N - t_1 \ge 600\ \mathrm{s} \quad \wedge \quad \#\{\text{unhandled gaps}\} = 0 .
$$

It also checks that RR and bpm describe the same beats, with RR restricted to 300-2000 ms:

$$
\Delta = \frac{60\,000}{\overline{\mathrm{RR}}_{\mathrm{ms}}} - \overline{\mathrm{bpm}} \approx 0,
$$

and reports "live HRV possible" only if RR intervals appear in more than 50% of notifications.

`lab/listen.py` reads every readable non-standard characteristic and subscribes to every notify/indicate one. The only write it performs is the standard CCCD subscription (0x2902); nothing proprietary is written. For each characteristic it reports payload lengths and the byte entropy

$$
H = -\sum_{b=0}^{255} p_b \log_2 p_b \quad [\text{bit/byte}],
$$

where values near 8 on long payloads suggest encrypted or compressed data.

## What the Air sends

All from my own device; captures are personal physiological data and are git-ignored, so these findings cannot be reproduced from the repo alone.

- 0x180D is advertised only with "Share heart rate" enabled, and notifications start only after confirming the request in the Google Health app.
- 0x2A37 flags are always `0x01`: no RR intervals, no sensor-contact or energy fields. Details in [`docs/ble.md`](docs/ble.md).
- A 10-minute capture passed the exit criterion above.
- The proprietary services match Fitbit's open-source Golden Gate stack (Gattlink transport, CoAP over DTLS). Public sources indicate per-device pre-shared keys, which is where the brief stops reverse engineering. Observed facts, external sources and hypotheses are tagged separately in [`docs/protocol.md`](docs/protocol.md).

## Limitations

- Tested on one Fitbit Air, on macOS. Linux and Windows should work through bleak but are untried.
- Tests cover the parser and the report; BLE code paths need hardware and have no automated tests.
- Read-only toward the device, so questions such as whether Gattlink starts on a write to `ac2f2845` stay open.
- Not affiliated with Google or Fitbit. Not a medical device.

MIT, see [LICENSE](LICENSE).
