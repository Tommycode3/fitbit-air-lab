"""Check the Phase 0 exit criterion on an hr_stream CSV.

  python -m lab.stream_report lab/captures/hr_XXXX.csv

Gap = interval between two consecutive notifications > GAP_S.
  handled     -> a disconnect/stall/retry event was recorded inside the gap
  unhandled   -> silence with no event at all: this is what fails the criterion
"""
from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path

GAP_S = 3.0
TARGET_S = 600.0


def analyze(rows: list[dict]) -> dict:
    data = [r for r in rows if r["event"] == "data"]
    t = [float(r["t_mono"]) for r in data]
    events = [(float(r["t_mono"]), r["event"]) for r in rows if r["event"] in ("disconnect", "stall", "retry")]

    handled, unhandled = [], []
    for a, b in zip(t, t[1:]):
        if b - a > GAP_S:
            (handled if any(a <= te <= b for te, _ in events) else unhandled).append((a - t[0], b - a))

    rr_rows = [r for r in data if r["rr_ms"]]
    rr = [float(x) for r in rr_rows for x in r["rr_ms"].split()]
    bpm = [int(r["bpm"]) for r in data]
    rr_plausible = [x for x in rr if 300 <= x <= 2000]
    # consistency: the reported bpm should be close to 60000 / mean RR
    coherence = None
    if rr_plausible and bpm:
        coherence = 60000 / statistics.mean(rr_plausible) - statistics.mean(bpm)

    return {
        "duration_s": (t[-1] - t[0]) if len(t) > 1 else 0.0,
        "notifications": len(data),
        "rate_hz": len(data) / (t[-1] - t[0]) if len(t) > 1 else 0.0,
        "handled_gaps": handled,
        "unhandled_gaps": unhandled,
        "rr_notification_pct": 100 * len(rr_rows) / len(data) if data else 0.0,
        "rr_count": len(rr),
        "rr_implausible": len(rr) - len(rr_plausible),
        "bpm_range": (min(bpm), max(bpm)) if bpm else None,
        "bpm_vs_rr_delta": coherence,
        "contact_values": sorted({r["contact"] for r in data}),
        "malformed": sum(r["event"] == "malformed" for r in rows),
    }


def main() -> None:
    path = Path(sys.argv[1])
    r = analyze(list(csv.DictReader(path.open())))
    print(f"duration          {r['duration_s']/60:.1f} min, {r['notifications']} notifications ({r['rate_hz']:.2f} Hz)")
    print(f"bpm               {r['bpm_range']}   contact={r['contact_values']}   malformed={r['malformed']}")
    print(f"RR                {r['rr_count']} intervals, in {r['rr_notification_pct']:.0f}% of notifications, "
          f"{r['rr_implausible']} outside 300-2000 ms")
    if r["bpm_vs_rr_delta"] is not None:
        print(f"bpm/RR check     60000/mean RR - mean bpm = {r['bpm_vs_rr_delta']:+.1f} bpm")
    print(f"gaps >{GAP_S:.0f}s        handled {len(r['handled_gaps'])}, UNHANDLED {len(r['unhandled_gaps'])}")
    for at, dur in r["unhandled_gaps"]:
        print(f"   unhandled at {at:.0f}s, duration {dur:.1f}s")
    ok = r["duration_s"] >= TARGET_S and not r["unhandled_gaps"]
    print(f"\nPHASE 0 CRITERION: {'PASS' if ok else 'FAIL'}"
          f"   ·   live HRV possible: {'yes' if r['rr_count'] > 0 and r['rr_notification_pct'] > 50 else 'NO'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
