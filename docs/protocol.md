# Air proprietary protocol — status

Legend: **[OBS]** observed by us in the captures · **[SRC]** cited external source · **[HYP]** hypothesis.

## Service map
| UUID | What it is | Provenance |
|---|---|---|
| `abbaff00` (ff01 RX write, ff02 TX notify) | Gattlink, the transport of **Golden Gate** (Fitbit's open-source stack): CoAP / DTLS / UDP / IP / Gattlink | [SRC] github.com/google/bumble `apps/gg_bridge.py`; github.com/Fitbit/golden-gate |
| `abbafd00` (fd01, fd02, fd03) | LinkStatusService: fd01 connection config (9 B), fd02 status (bonded/encrypted/DLE) | [SRC] github.com/denysvitali/openwatch PROTOCOL.md §2.0 · [OBS] fd01=`180000004800f70000`, fd02=`01000000000000` |
| `ac2f0045` (0145 read, 2845 write) | GATT cache validation; 0145 points to an ephemeral characteristic; writing `0x00` starts Gattlink | [SRC] openwatch; Gadgetbridge issue #504 (comment 2026-09-22) · [OBS] 0145 contains the UUID of 2845 |
| `4eee1c00` | Unknown, not present in the Golden Gate code | [SRC] openwatch · [OBS] 1c03 requires encryption |

## Encryption — answer to question 4 of the brief
- DTLS 1.2 with a **per-device PSK** on top of Gattlink. [SRC] openwatch
- The data dump ("megadump") is AES-128-EAX, and the key lives only on the tracker and on the Fitbit backend. [SRC] Gadgetbridge #504
- Gadgetbridge (Charge 6, PR #6273) connects only after the official onboarding and key extraction from a rooted Android device. The server-generated sync response remains undecryptable. [SRC]
- **Not yet verified on our Air.** Verifying requires writing `0x00` to ac2f2845, which has not been done (read-only policy).

→ According to the sources, the brief's stop condition is triggered ("encrypted with per-device keys: stop and propose options").

## Hardware
- Model GW9C8, FCC ID **SZGGW9C8**, 34.5 mAh battery. [SRC] support.google.com/product-documentation/answer/17050752
- Sensors: PPG, red+IR (SpO2), skin temperature, accelerometer + gyroscope. [SRC] dcrainmaker.com 2026/05
- SoC: **unknown**. Ambiq Apollo4 is plausible (used in Charge 5, Luxe, Sense 2). [HYP]
- FCC internal photos possibly confidential until 2027-03. [HYP, not verified at the source]

## RR / HRV
- BLE 0x180D: bpm only. [OBS]
- Google Health API: HRV = RMSSD in ms only, HR at 1 s resolution, no RR. [SRC] developers.google.com/health/data-types/vitals
