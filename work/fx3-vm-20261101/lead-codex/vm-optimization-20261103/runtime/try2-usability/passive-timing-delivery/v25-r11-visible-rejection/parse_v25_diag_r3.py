#!/usr/bin/env python3
"""Parse a QMP-paused v25-r3 ring; preserve lost/ambiguous evidence."""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

MAGIC = 0x3147414944353256
HEADER = 0x2000
RECORDS = 0x2040
CAPACITY = 256
WORDS = 12
STRIDE = WORDS * 8
EVENTS = {1: "produce_enter", 2: "produce_return", 3: "receive", 4: "commit",
          5: "wait_enter", 6: "wait_return", 7: "signal_enter", 8: "signal_return"}
PAIRS = {2: 1, 6: 5, 8: 7}
IDENTITY = ("tid", "id", "op", "committed_seq", "source_seq", "epoch", "token")


def parse(data: bytes, *, quiesced: bool = False) -> dict:
    if len(data) < RECORDS + CAPACITY * STRIDE:
        raise ValueError("diagnostic readback truncated")
    magic, version, total, capacity, stride, dropped = struct.unpack_from("<6Q", data, HEADER)
    if (magic, version, capacity, stride) != (MAGIC, 2, CAPACITY, STRIDE):
        raise ValueError("not a v25-r3 diagnostic readback")
    first = max(1, total - CAPACITY + 1)
    rows, invalid = [], []
    for serial in range(first, total + 1):
        values = struct.unpack_from("<12Q", data, RECORDS + ((serial - 1) % CAPACITY) * STRIDE)
        if values[0] != serial or values[3] not in EVENTS:
            invalid.append({"serial": serial, "observed_serial": values[0],
                            "reason": "overwritten" if values[0] > serial else "missing_or_torn"})
            continue
        _, ns, tid, event, committed, source, ident, op, result, epoch, token, link = values
        if result & (1 << 63):
            result -= 1 << 64
        rows.append({"serial": serial, "guest_clock_id": 1, "guest_ns": ns,
                     "tid": tid, "event": EVENTS[event], "event_id": event,
                     "committed_seq": committed, "source_seq": source,
                     "id": ident, "op": op, "native_result": result,
                     "epoch": epoch, "token": token, "link": link})
    by_serial = {row["serial"]: row for row in rows}
    pairs, paired, bad_links = [], set(), set()
    for row in rows:
        expected = PAIRS.get(row["event_id"])
        if expected is None:
            continue
        prior = by_serial.get(row["link"])
        faults = []
        if not quiesced:
            faults.append("snapshot_not_quiesced")
        if row["link"] >= row["serial"] or row["link"] == 0:
            faults.append("link_not_before_return")
        if prior is None:
            faults.append("enter_outside_tail" if 0 < row["link"] < first else "enter_missing")
        else:
            if prior["event_id"] != expected:
                faults.append("wrong_enter_event")
            if row["guest_ns"] < prior["guest_ns"] or not row["guest_ns"] or not prior["guest_ns"]:
                faults.append("nonmonotonic_guest_time")
            faults.extend("identity_" + field for field in IDENTITY if prior[field] != row[field])
            if prior["serial"] in paired:
                faults.append("duplicate_return_link")
        valid = not faults
        if valid:
            paired.add(prior["serial"])
        elif prior is not None:
            bad_links.add(prior["serial"])
        pairs.append({"return_serial": row["serial"], "enter_serial": row["link"],
                      "valid_within_tail": valid, "faults": faults,
                      "duration_guest_ns": row["guest_ns"] - prior["guest_ns"] if valid else None})
    evidence_incomplete = bool(dropped or invalid or not quiesced)
    open_enters = [{"serial": row["serial"],
                    "classification": "invalid_return_link" if row["serial"] in bad_links else
                    "unknown_possible_lost_return" if evidence_incomplete else "unpaired_at_quiesced_snapshot"}
                   for row in rows if row["event_id"] in PAIRS.values() and row["serial"] not in paired]
    return {"magic": hex(magic), "version": version, "total_accepted_events": total,
            "dropped_busy_writer_events": dropped, "tail_first_serial": first,
            "tail_capacity": CAPACITY, "readback_quiesced": quiesced,
            "invalid_or_torn_slots": invalid, "rows": rows, "pairs": pairs,
            "unpaired_enters_in_tail": open_enters, "tail_may_omit_earlier_enters": first > 1,
            "absence_cannot_prove_no_guest_call": evidence_incomplete or first > 1}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ring", type=Path)
    ap.add_argument("--quiesced", action="store_true", help="Only with verified QMP stop/query-status")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    result = parse(args.ring.read_bytes(), quiesced=args.quiesced)
    encoded = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded)
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
