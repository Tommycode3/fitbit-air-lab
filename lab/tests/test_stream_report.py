from lab.stream_report import analyze


def row(t, event="data", bpm="60", rr=""):
    return {"t_mono": str(t), "event": event, "bpm": bpm, "rr_ms": rr, "contact": "1"}


def test_handled_vs_unhandled_gaps():
    rows = [row(i) for i in range(10)]
    rows += [row(10.5, "disconnect"), row(20)]        # gap 9->20 with an event: handled
    rows += [row(21), row(40)]                        # gap 21->40 silent: unhandled
    r = analyze(rows)
    assert len(r["handled_gaps"]) == 1
    assert len(r["unhandled_gaps"]) == 1


def test_rr_coherence():
    rows = [row(i, bpm="60", rr="1000.0") for i in range(5)]
    r = analyze(rows)
    assert r["rr_count"] == 5 and r["rr_notification_pct"] == 100
    assert abs(r["bpm_vs_rr_delta"]) < 1e-9
