#!/usr/bin/env python3
"""Read-only reconstruction of two archived OSD transitions; no QMP or guest access."""
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE.parent.parent / "runs"
CASES = {
    "48a838e5": {"before": 548, "after": 551, "sources": (542, 549)},
    "c017e6ed": {"before": 655, "after": 663, "sources": (648, 656)},
}
EVENTS = ("FX3_GPE_CMD op=", "FX3_GPE104_CMD_RETURN", "FX3_GPE104_COMPLETE_RETURN",
          "FX3_GPE_SCOPE", "FX3_GPE_NATIVE_TARGET", "FX3_OSD_HEADLESS_VALIDATE",
          "FX3_OSD_HEADLESS_COPY", "FX3_OSD_HEADLESS_LEASE", "FX3_OSD102_COMMIT")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def event_rows(lines, source):
    match = re.compile(rf"FX3_OSD102_COMMIT frame={source}(?!\d)")
    end = next(i for i, line in enumerate(lines) if match.search(line))
    start = next(i for i in range(end - 1, -1, -1)
                 if "FX3_OSD102_COMMIT frame=" in lines[i]) + 1
    rows = []
    for i in range(start, end + 1):
        line = lines[i]
        for marker in EVENTS:
            at = line.find(marker)
            if at >= 0:
                rows.append({"line_0_based": i, "marker": marker, "text": line[at:]})
                break
    return rows


def slim(frame):
    keys = ("sequence", "epoch", "update_id", "pixel_source_sequence", "token", "physical",
            "fnv64", "sha256", "PNG_sha256", "host_monotonic", "committed_slot",
            "guest_native_lease_released_before_ring_commit", "CP_composition_panel_acceptance")
    return {k: frame[k] for k in keys} | {
        "target": frame["registered_target"],
        "native_identity": frame["native_identity"],
    }


def main():
    out = {}
    for suffix, case in CASES.items():
        run = RUNS / f"try2mssallinternal-{suffix}"
        serial = run / "serial.log"
        ring = run / "osd-ring-readback.json"
        frames = {f["sequence"]: f for f in json.loads(ring.read_text())["frames"]}
        before, after = (frames[case[k]] for k in ("before", "after"))
        lines = serial.read_bytes().decode(errors="replace").splitlines()
        assert before["PNG_sha256"] != after["PNG_sha256"]
        assert [before["pixel_source_sequence"], after["pixel_source_sequence"]] == list(case["sources"])
        assert before["update_id"] == after["update_id"] == "0x1005"
        assert all(f["registered_target"]["valid_during_native_read_lease_and_raster_lifecycle_guards"]
                   for f in (before, after))
        events = {str(seq): event_rows(lines, seq) for seq in case["sources"]}
        for seq, rows in events.items():
            assert any(r["marker"] == "FX3_OSD_HEADLESS_LEASE" and "result=0" in r["text"] for r in rows), seq
            assert any(r["marker"] == "FX3_OSD102_COMMIT" and "op=0x1003" in r["text"] for r in rows), seq
        out[suffix] = {
            "run": str(run), "serial_sha256": digest(serial), "ring_json_sha256": digest(ring),
            "sample_before": slim(before), "sample_after": slim(after),
            "same_host_monotonic_delta_s": after["host_monotonic"] - before["host_monotonic"],
            "source_events": events,
            "clock_boundary": "GPE ns is guest monotonic. OSD commit has no guest timestamp; PNG sampling has host monotonic. Do not subtract across clocks.",
        }
    (HERE / "timeline.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(HERE / "timeline.json")


if __name__ == "__main__":
    main()
