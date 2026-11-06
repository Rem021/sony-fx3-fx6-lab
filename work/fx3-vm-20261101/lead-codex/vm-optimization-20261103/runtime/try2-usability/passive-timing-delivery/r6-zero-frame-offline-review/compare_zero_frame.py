#!/usr/bin/env python3
"""Bounded, read-only comparison of the frozen r3/r4e CPIOs and serials."""

import argparse
import hashlib
import json
import re
from pathlib import Path


HERE = Path(__file__).resolve().parent
BASE = HERE.parent.parent
RUNS = BASE / "runs"
R3 = RUNS / "v25diag-web-r3-91001f82"
R4E = RUNS / "v25procdiag-web-r4e-6274aabb"
R6 = RUNS / "v25procdiag-web-r6-9182e182"
CPIO3 = HERE.parent / "v25-menu-osd-diagnostic-r3/vmopt-20261104-v25-menu-osd-diagnostic-r3/guest.cpio"
CPIO4 = HERE.parent / "v25-r4-postmortem-host/vmopt-20261104-v25-procdiag-r4e/guest.cpio"
MARKERS = (
    "FX3_GPE104_DYNAMIC_ENTER", "FX3_GPE104_DYNAMIC_RETURN",
    "FX3_KEY96_POLL", "FX3_AP89_SCREEN_OPEN_ENTER",
    "FX3_AP89_SCREEN_CREATE", "FX3_UI_WIRE", "FX3_UIPC_RECV_BEGIN",
    "FX3_UI_CONFIG_DONE", "FX3_UI_FILL_EXEC",
    "FX3_GPE_CMD op=", "FX3_GPE104_CMD_RETURN",
    "FX3_OSD_HEADLESS_BOUND", "FX3_OSD102_COMMIT",
    "FX3_OSD_FRAME_TARGET_VALID", "FX3_OSD_NATIVE_SIGNAL",
)
OWNER_STRINGS = tuple(x.encode() for x in (
    "FX3_UI_WIRE", "FX3_UI_FILL_EXEC", "FX3_AP89_SCREEN_OPEN_ENTER",
    "FX3_GPE_CMD op=", "FX3_OSD102_COMMIT",
))


def archive_index(path):
    rows = {}
    with path.open("rb") as f:
        while True:
            start = f.tell()
            h = f.read(110)
            if len(h) != 110 or h[:6] not in (b"070701", b"070702"):
                raise ValueError(f"invalid newc header at {path}:{start}")
            fields = tuple(int(h[6 + i*8:14 + i*8], 16) for i in range(13))
            name_raw = f.read(fields[11])
            if len(name_raw) != fields[11] or not name_raw.endswith(b"\0"):
                raise ValueError(f"invalid name at {path}:{start}")
            name = name_raw[:-1].decode()
            f.seek((f.tell() + 3) & ~3)
            data_at = f.tell()
            f.seek((data_at + fields[6] + 3) & ~3)
            if name == "TRAILER!!!":
                return rows
            if name in rows:
                raise ValueError(f"duplicate member: {name}")
            rows[name] = {"offset": data_at, "bytes": fields[6], "fields": fields}


def byte_compare(a, ai, b, bi, search=()):
    if ai["bytes"] != bi["bytes"]:
        return False, [], []
    length = ai["bytes"]
    seen_a, seen_b = set(), set()
    with a.open("rb") as fa, b.open("rb") as fb:
        fa.seek(ai["offset"]); fb.seek(bi["offset"])
        prior_a = prior_b = b""
        while length:
            n = min(1 << 20, length)
            ca, cb = fa.read(n), fb.read(n)
            if len(ca) != n or len(cb) != n:
                raise ValueError("short CPIO member")
            for marker in search:
                if marker in prior_a + ca: seen_a.add(marker.decode())
                if marker in prior_b + cb: seen_b.add(marker.decode())
            prior_a, prior_b = ca[-128:], cb[-128:]
            if ca != cb:
                return False, sorted(seen_a), sorted(seen_b)
            length -= n
    return True, sorted(seen_a), sorted(seen_b)


def member_bytes(path, row):
    with path.open("rb") as f:
        f.seek(row["offset"])
        return f.read(row["bytes"])


def cpio_report():
    a, b = archive_index(CPIO3), archive_index(CPIO4)
    equal = []; changed = []; metadata = []; owners = {}
    for name in sorted(a.keys() & b.keys()):
        same, own_a, own_b = byte_compare(CPIO3, a[name], CPIO4, b[name], OWNER_STRINGS)
        (equal if same else changed).append(name)
        if a[name]["fields"] != b[name]["fields"]:
            metadata.append(name)
        if own_a or own_b:
            owners[name] = {"r3": own_a, "r4e": own_b}
    old = member_bytes(CPIO3, a["init"])
    new = member_bytes(CPIO4, b["init"])
    prefix = 0
    while prefix < min(len(old), len(new)) and old[prefix] == new[prefix]:
        prefix += 1
    suffix = 0
    while suffix < min(len(old)-prefix, len(new)-prefix) and old[-1-suffix] == new[-1-suffix]:
        suffix += 1
    insertion = new[prefix:len(new)-suffix]
    return {
        "r3_members": len(a), "r4e_members": len(b),
        "only_r3": sorted(a.keys()-b.keys()), "only_r4e": sorted(b.keys()-a.keys()),
        "equal_shared_payload_count": len(equal), "changed_shared_payload": changed,
        "changed_shared_header_fields": metadata,
        "init_old_bytes": len(old), "init_new_bytes": len(new),
        "init_common_prefix_bytes": prefix, "init_common_suffix_bytes": suffix,
        "init_removed_bytes_hex": old[prefix:len(old)-suffix].hex(),
        "init_inserted_bytes_hex": insertion.hex(),
        "init_inserted_text": insertion.decode("utf8", "replace"),
        "init_r3_sha256": hashlib.sha256(old).hexdigest(),
        "init_r4e_sha256": hashlib.sha256(new).hexdigest(),
        "marker_owner_members": owners,
    }


def guest_ns(s):
    m = re.search(r"(?<![A-Za-z_])ns=(\d+)", s)
    return int(m.group(1)) if m else None


def serial_report(path):
    data = path.read_bytes()
    instances = {m: [] for m in MARKERS}
    wire_raw = []
    for raw in data.splitlines():
        s = raw.decode("utf8", "replace")
        for marker in MARKERS:
            at = s.find(marker)
            if at >= 0:
                instances[marker].append({"guest_ns": guest_ns(s[at:]), "text": s[at:][:480]})
                if marker == "FX3_UI_WIRE":
                    wire_raw.append(raw[raw.find(marker.encode()):])
    opens = []
    for item in instances["FX3_AP89_SCREEN_OPEN_ENTER"]:
        m = re.search(r"id2=(0x[0-9a-f]+|0)\b", item["text"])
        opens.append({"id2": m.group(1) if m else None, "guest_ns": item["guest_ns"]})
    wire = []
    for item in instances["FX3_UI_WIRE"][:70]:
        m = re.search(r"target=(0x[0-9a-f]+).*?tag1=(0x[0-9a-f]+)", item["text"])
        wire.append(m.groups() if m else None)
    ns_all = [int(m.group(1)) for m in re.finditer(rb"(?<![A-Za-z_])ns=(\d+)", data)]
    recv_queues = {}
    for item in instances["FX3_UIPC_RECV_BEGIN"]:
        m = re.search(r"queue=(0x[0-9a-f]+)", item["text"])
        if m:
            recv_queues[m.group(1)] = recv_queues.get(m.group(1), 0) + 1
    return {
        "serial_bytes": len(data), "max_logged_guest_ns": max(ns_all) if ns_all else None,
        "marker_counts": {k: len(v) for k,v in instances.items()},
        "screen_open": opens, "ui_wire_first70_target_tag": wire,
        "uipc_recv_begin_by_queue": recv_queues,
        "ui_wire_ninth_raw_hex": wire_raw[8].hex() if len(wire_raw) >= 9 else None,
        "ui_wire_ninth_raw_ascii": wire_raw[8].decode("ascii", "replace") if len(wire_raw) >= 9 else None,
        "first": {k: v[0] if v else None for k,v in instances.items()},
        "last_key_poll": instances["FX3_KEY96_POLL"][-1] if instances["FX3_KEY96_POLL"] else None,
    }


def main():
    p = argparse.ArgumentParser(); p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    out = {"cpio": cpio_report(), "serial": {
        "r3": serial_report(R3/"serial.log"),
        "r4e": serial_report(R4E/"serial.log"),
        "r6": serial_report(R6/"serial.log"),
    }}
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps({"output":str(args.output),"changed_payload":out["cpio"]["changed_shared_payload"],
                      "only_r4e":out["cpio"]["only_r4e"]},ensure_ascii=False))


if __name__ == "__main__":
    main()
