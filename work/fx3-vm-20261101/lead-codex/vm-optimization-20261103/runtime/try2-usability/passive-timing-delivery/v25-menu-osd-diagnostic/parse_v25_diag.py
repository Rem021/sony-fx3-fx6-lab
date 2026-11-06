#!/usr/bin/env python3
"""Read the bounded v25 OSD diagnostic tail from an immutable ring readback."""
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
EVENTS = {
    1: "produce_enter", 2: "produce_return", 3: "receive",
    4: "commit", 5: "wait_enter", 6: "wait_return",
    7: "signal_enter", 8: "signal_return",
}
PAIRS = {2: 1, 6: 5, 8: 7}


def parse(data: bytes) -> dict:
    if len(data) < RECORDS + CAPACITY * STRIDE:
        raise ValueError("diagnostic readback truncated")
    magic, version, total, capacity, stride = struct.unpack_from("<5Q", data, HEADER)
    if (magic, version, capacity, stride) != (MAGIC, 1, CAPACITY, STRIDE):
        raise ValueError("not a v25 diagnostic readback")
    first = max(1, total - CAPACITY + 1)
    rows = []
    invalid = []
    for serial in range(first, total + 1):
        values = struct.unpack_from("<12Q", data, RECORDS + ((serial - 1) % CAPACITY) * STRIDE)
        if values[0] != serial:
            invalid.append(serial)
            continue
        _, ns, tid, event, committed, source, ident, op, result, epoch, token, link = values
        if event not in EVENTS:
            invalid.append(serial)
            continue
        if result & (1 << 63):
            result -= 1 << 64
        rows.append({"serial": serial, "guest_clock_id": 1, "guest_ns": ns,
                     "tid": tid, "event": EVENTS[event], "event_id": event,
                     "committed_seq": committed, "source_seq": source,
                     "id": hex(ident), "op": hex(op), "native_result": result,
                     "epoch": epoch, "token": hex(token), "link": link})
    by_serial = {row["serial"]: row for row in rows}
    pairs = []
    paired = set()
    for row in rows:
        expected = PAIRS.get(row["event_id"])
        if expected is None:
            continue
        prior = by_serial.get(row["link"])
        valid = prior is not None and prior["event_id"] == expected and prior["tid"] == row["tid"]
        pairs.append({"return_serial": row["serial"], "enter_serial": row["link"],
                      "valid_within_tail": valid,
                      "duration_guest_ns": row["guest_ns"] - prior["guest_ns"] if valid else None})
        if valid:
            paired.add(prior["serial"])
    open_enters = [row["serial"] for row in rows if row["event_id"] in PAIRS.values() and row["serial"] not in paired]
    return {"magic": hex(magic), "version": version, "total_events": total,
            "tail_first_serial": first, "tail_capacity": CAPACITY,
            "invalid_or_torn_serials": invalid, "rows": rows,
            "pairs": pairs, "unpaired_enters_in_tail": open_enters,
            "tail_may_omit_earlier_enters": first > 1}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ring", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    result = parse(args.ring.read_bytes())
    encoded = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded)
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
