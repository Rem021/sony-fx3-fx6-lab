#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FX3 r38 MENU latency decomposition (read-only, pure file analysis).

Only Python standard library.  Reads the frozen native serial log, the passive
OSD ring readback, the host tool timeline/observations and the log-producer
sources; never imports project modules, never starts a VM/QEMU/browser and
never writes outside the explicit --out/--data-dir paths.

Clock rule: guest CLOCK_MONOTONIC values are subtracted only from other guest
CLOCK_MONOTONIC values.  Kernel printk timestamps are a different observed
domain (approximately 31.25x guest plus ~10.8 s in this run, cause unproven)
and are never used for subtraction.  Host monotonic is bridged to guest
monotonic only through an explicitly printed interval/uncertainty.

Usage:
  python3 analyze_menu_timing.py manifest --out input-manifest-before.json
  python3 analyze_menu_timing.py analyze --out results.json --data-dir data
"""

import argparse
import bisect
import csv
import datetime as dt
import hashlib
import json
import os
import re
import statistics
import sys

MAC = "/Volumes/KAFU2T/AI/Projects/Mac"
TRY2 = (MAC + "/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/"
        "runtime/try2-usability")
NATIVE = TRY2 + "/runs/v35diag-n64-r36-r37-4d245250"
HOST = (TRY2 + "/passive-timing-delivery/r37-diagnostic-runner-candidate/"
        "run-inputs/r38-vm-29076c7ba60e")
DELIVERY = TRY2 + "/passive-timing-delivery"
SRC = MAC + "/work/fx3-vm-20261101"

# Frozen inputs used for the before/after manifest.  Every path is required.
INPUTS = {
    "native": [
        NATIVE + "/serial.log",
        NATIVE + "/osd-ring-readback.json",
        NATIVE + "/trial-session.json",
        NATIVE + "/trial-step-01-key-1ab.json",
        NATIVE + "/trial-web-final-receipt.json",
        NATIVE + "/trial-input-events.jsonl",
        NATIVE + "/command.json",
        NATIVE + "/trial-final.json",
        NATIVE + "/trial-phaseA.json",
    ],
    "host": [
        HOST + "/REPORT.md",
        HOST + "/RESULT.json",
        HOST + "/tool-timeline.jsonl",
        HOST + "/FIRST-FRAME-CLOCK.json",
        HOST + "/NATIVE-DOWN-UP-DONE-EXACT.json",
        HOST + "/step-01-attempt-01/outcome.json",
        HOST + "/step-01-attempt-01/identity.json",
        HOST + "/step-01-attempt-01/click-receipt.json",
        HOST + "/step-01-attempt-01/observation-1/observation-result.json",
        HOST + "/step-01-attempt-01/observation-1/observation.png",
        HOST + "/step-01-attempt-01/observation-2/observation-result.json",
        HOST + "/step-01-attempt-01/observation-2/observation.png",
    ],
    "coordinator": [
        DELIVERY + "/r38-coordinator-final-review.json",
        DELIVERY + "/r38-coordinator-r35-readout.json",
        DELIVERY + "/r38-coordinator-resource-audit.json",
    ],
    "producer_source": [
        SRC + "/lead-claude/impl/gpe-perf/fx3-gpe-observe-v26-perf.c",
        MAC + "/work/fx3-vm-20261101/menu-repair-01/runtime/helpers/fx3-gpe-command-wait102-v1.h",
        MAC + "/work/fx3-vm-20261101/menu-repair-01/runtime/helpers/fx3-complete104-observe-v1.h",
        TRY2 + "/passive-timing-delivery/r35-existing-log-observation-candidate/src/fx3-osd-r35.c",
        TRY2 + "/passive-timing-delivery/r35-existing-log-observation-candidate/src/fx3-ui-r35.c",
        TRY2 + "/mss-all-key-contrast/passive-timing-next/src/fx3-rm-empty-provider-v8-long-use-timing.c",
        TRY2 + "/src/fx3-rm-key-gate-v6-long-use.inc",
        TRY2 + "/mss-all-key-contrast/passive-timing-next/build-receipt.json",
        TRY2 + "/mss-all-key-contrast/passive-timing-next/source-receipt.json",
        TRY2 + "/passive-timing-delivery/r33-causal-observation-candidate/GPE-SOURCE-BINDING.json",
        TRY2 + "/passive-timing-delivery/r36-fixed-slot-package/MANIFEST.json",
        TRY2 + "/passive-timing-delivery/r36-fixed-slot-package/DEPENDENCIES.json",
        TRY2 + "/passive-timing-delivery/r36-fixed-slot-package/source-index.json",
        TRY2 + "/passive-timing-delivery/r36-fixed-slot-package/guest.cpio",
    ],
}

TAG_RE = re.compile(r"FX3_[A-Z0-9_]+")
KV_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=(\S+)")
KTS_RE = re.compile(r"\[\s*(\d+\.\d+)\]")
FLOAT_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
INT_RE = re.compile(r"^\d+$")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_slice(path, offset, size):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        f.seek(offset)
        left = size
        while left > 0:
            chunk = f.read(min(1 << 20, left))
            if not chunk:
                break
            h.update(chunk)
            left -= len(chunk)
    return h.hexdigest()


def member_binding():
    cpio = TRY2 + "/passive-timing-delivery/r36-fixed-slot-package/guest.cpio"
    index = load_json(TRY2 + "/passive-timing-delivery/r36-fixed-slot-package/source-index.json")
    wanted = {
        "simulation/fx3-gpe-observe-v7.so": {
            "expect_sha256": "30667f76ccfa3f0b9b4834b1fbce725a76683ccd775615ed66955d49200d7ba4",
            "strings": [b"FX3_GPE104_CMD_RETURN", b"FX3_GPE_NATIVE_TARGET",
                        b"FX3_GPE_CMD op=", b"FX3_GPE_DRAW_INTERVAL"],
        },
        "simulation/fx3-rm-empty-provider-v3-setup.so": {
            "expect_sha256": "ff38874e128d517147b1712588bf68d24412dae781a390eaa8bd7d230c3c1707",
            "strings": [b"wait_enter_ns", b"FX3_KEY95_STEP_DONE",
                        b"FX3_KEY96_POLL", b"clock_id=1"],
        },
        "simulation/fx3-osd-headless-v5.so": {
            "strings": [b"FX3_OSD102_COMMIT", b"clock_id=1"],
        },
    }
    rows = []
    for name, spec in wanted.items():
        e = next((x for x in index if x.get("name") == name), None)
        if not e:
            rows.append({"member": name, "found": False})
            continue
        sh = sha256_slice(cpio, e["payload_offset"], e["size"])
        with open(cpio, "rb") as f:
            f.seek(e["payload_offset"])
            blob = f.read(e["size"])
        strings = {s.decode(): (s in blob) for s in spec["strings"]}
        rows.append({"member": name, "found": True,
                     "bytes": e["size"],
                     "payload_offset": e["payload_offset"],
                     "sha256": sh,
                     "expected_sha256": spec.get("expect_sha256"),
                     "sha_match": (sh == spec["expect_sha256"])
                     if spec.get("expect_sha256") else None,
                     "strings": strings,
                     "all_strings_present": all(strings.values())})
    return {"cpio": cpio, "members": rows}


def manifest():
    out = {"schema": "fx3-r40-input-manifest/v1", "root": MAC,
           "groups": {}, "count": 0, "all_present": True}
    for group, paths in INPUTS.items():
        rows = []
        for p in paths:
            if not os.path.isfile(p):
                rows.append({"path": p, "present": False})
                out["all_present"] = False
                continue
            rows.append({"path": p, "present": True,
                         "bytes": os.path.getsize(p),
                         "sha256": sha256_file(p)})
        out["groups"][group] = rows
        out["count"] += len(rows)
    out["manifest_sha256"] = hashlib.sha256(
        json.dumps(out["groups"], sort_keys=True, separators=(",", ":"))
        .encode()).hexdigest()
    return out


def parse_serial(path):
    """Return (records, kernel_ts, stats).

    A physical serial line can contain more than one FX3 tag because a kernel
    printk and a user dprintf can interleave (and some kernel lines carry a
    tag).  We split at tag starts, so each record owns its own field slice.
    """
    recs = []
    kts = []
    multi = 0
    total_lines = 0
    with open(path, "r", errors="replace") as f:
        for ln, line in enumerate(f, 1):
            total_lines += 1
            line = line.rstrip("\n")
            km = KTS_RE.search(line)
            if km:
                kts.append((ln, float(km.group(1))))
            ms = list(TAG_RE.finditer(line))
            if not ms:
                continue
            if len(ms) > 1:
                multi += 1
            for i, m in enumerate(ms):
                end = ms[i + 1].start() if i + 1 < len(ms) else len(line)
                seg = line[m.start():end]
                fields = {}
                for k, v in KV_RE.findall(seg):
                    v = v.strip().rstrip("\r")
                    # strip a trailing '[' left by an interleaved printk
                    if v.endswith("[") and not v.startswith("0x"):
                        v = v[:-1]
                    fields[k] = v
                recs.append({"ln": ln, "tag": m.group(0), "f": fields,
                             "kts": km.group(1) if km else None})
    return recs, kts, {"lines": total_lines, "records": len(recs),
                       "lines_with_multiple_tags": multi,
                       "kernel_ts_lines": len(kts)}


def to_int(v):
    if v is None:
        return None
    try:
        return int(v, 0) if str(v).lower().startswith("0x") else int(v)
    except (TypeError, ValueError):
        return None


def to_float(v):
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def pair_by_event(recs, enter_tag, return_tag):
    """Pair enter/return records by the shared global event id."""
    opens = {}
    pairs = []
    unmatched_enter = 0
    unmatched_return = 0
    mismatch = []
    for r in recs:
        if r["tag"] == enter_tag:
            ev = r["f"].get("event")
            if ev is None:
                continue
            opens.setdefault(ev, []).append(r)
        elif r["tag"] == return_tag:
            ev = r["f"].get("event")
            stack = opens.get(ev)
            if not stack:
                unmatched_return += 1
                continue
            en = stack.pop(0)
            try:
                dur = int(r["f"]["ns"]) - int(en["f"]["ns"])
            except (KeyError, ValueError):
                dur = None
            bad = []
            for key in ("tid", "flags", "module", "caller"):
                if key in en["f"] and key in r["f"] and en["f"][key] != r["f"][key]:
                    bad.append(key)
            if bad:
                mismatch.append({"event": ev, "fields": bad})
            pairs.append({"enter": en, "return": r, "event": int(ev),
                          "duration_ns": dur})
    unmatched_enter = sum(len(v) for v in opens.values())
    return pairs, unmatched_enter, unmatched_return, mismatch


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def iso_to_dt(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def utc_to_host(tool_rows, when):
    """Linear interpolation of host_ns over the host UTC timestamps."""
    pts = sorted((r["utc_dt"], r["host_ns"]) for r in tool_rows
                 if r.get("utc_dt") is not None)
    times = [p[0] for p in pts]
    i = bisect.bisect_left(times, when)
    if i <= 0:
        return pts[0][1] / 1e9, 0.0
    if i >= len(pts):
        return pts[-1][1] / 1e9, 0.0
    t0, h0 = pts[i - 1]
    t1, h1 = pts[i]
    span = (t1 - t0).total_seconds()
    if span <= 0:
        return h0 / 1e9, 0.0
    frac = (when - t0).total_seconds() / span
    return (h0 + (h1 - h0) * frac) / 1e9, span


def select(recs, tag):
    return [r for r in recs if r["tag"] == tag]


def build_analysis():
    serial_path = NATIVE + "/serial.log"
    recs, kts, parse_stats = parse_serial(serial_path)

    # ---------------------------------------------------------------- tags
    by_tag = {}
    for r in recs:
        by_tag.setdefault(r["tag"], []).append(r)

    def tag_records(t):
        return by_tag.get(t, [])

    # GPE command / completion pairs
    cmd_recs = tag_records("FX3_GPE_CMD")
    ret_recs = tag_records("FX3_GPE104_CMD_RETURN")
    scope_recs = tag_records("FX3_GPE_SCOPE")
    draw_recs = tag_records("FX3_GPE_DRAW_INTERVAL")
    raw_recs = tag_records("FX3_GPE_RAW_PARAMS")
    complete_enter = tag_records("FX3_GPE104_COMPLETE_ENTER")
    complete_return = tag_records("FX3_GPE104_COMPLETE_RETURN")
    dynamic_enter = tag_records("FX3_GPE104_DYNAMIC_ENTER")
    dynamic_return = tag_records("FX3_GPE104_DYNAMIC_RETURN")

    dyn_pairs, dyn_unmatched_in, dyn_unmatched_out, dyn_mismatch = pair_by_event(
        recs, "FX3_GPE104_DYNAMIC_ENTER", "FX3_GPE104_DYNAMIC_RETURN")
    cmp_pairs, cmp_unmatched_in, cmp_unmatched_out, cmp_mismatch = pair_by_event(
        recs, "FX3_GPE104_COMPLETE_ENTER", "FX3_GPE104_COMPLETE_RETURN")

    cmd_by_seq = {}
    for r in cmd_recs:
        s = to_int(r["f"].get("seq"))
        if s is not None:
            cmd_by_seq[s] = r
    ret_by_seq = {}
    for r in ret_recs:
        s = to_int(r["f"].get("seq"))
        if s is not None:
            ret_by_seq[s] = r
    scope_seq = {to_int(r["f"].get("seq")) for r in scope_recs}
    draw_seq = {to_int(r["f"].get("seq")) for r in draw_recs}
    raw_seq = {to_int(r["f"].get("seq")) for r in raw_recs}

    cmp_by_seq = {}
    for p in cmp_pairs:
        s = to_int(p["enter"]["f"].get("seq"))
        if s is not None:
            cmp_by_seq[s] = p

    dyn_by_window = {}
    dyn_sorted = sorted(
        (p for p in dyn_pairs if p["enter"]["f"].get("ns")),
        key=lambda p: int(p["enter"]["f"]["ns"]))
    dyn_ns = [int(p["enter"]["f"]["ns"]) for p in dyn_sorted]

    seqs = sorted(ret_by_seq)
    prev_ns = None
    commands = []
    for s in seqs:
        ret = ret_by_seq[s]
        cmd = cmd_by_seq.get(s)
        op_arg = cmd["f"].get("op") if cmd else None
        op_code = {"FillRect": 0, "BitBlit": 1, "Flush": 4}.get(op_arg)
        ns = to_int(ret["f"].get("ns"))
        delta = (ns - prev_ns) if (ns is not None and prev_ns is not None) else None
        cp = cmp_by_seq.get(s)
        cp_ns = to_int(cp["enter"]["f"]["ns"]) if cp else None
        cp_dur = cp["duration_ns"] if cp else None
        row = {
            "seq": s,
            "op": op_arg,
            "op_code": op_code,
            "tid": ret["f"].get("tid"),
            "ns": ns,
            "result": to_int(ret["f"].get("result")),
            "errno": to_int(ret["f"].get("errno")),
            "completion_source": ret["f"].get("completion_source"),
            "delta_ns": delta,
            "has_scope": s in scope_seq,
            "has_draw_interval": s in draw_seq,
            "has_raw_params": s in raw_seq,
            "complete_event": cp["event"] if cp else None,
            "complete_enter_ns": cp_ns,
            "complete_duration_ns": cp_dur,
            "complete_status": cp["enter"]["f"].get("status") if cp else None,
            "complete_result": to_int(cp["return"]["f"].get("result")) if cp else None,
        }
        # dynamic calls whose ENTER falls in (previous completion, this completion]
        lo = prev_ns if prev_ns is not None else -1
        a = bisect.bisect_right(dyn_ns, lo)
        b = bisect.bisect_right(dyn_ns, ns)
        row["dynamic_events"] = [dyn_sorted[i]["event"] for i in range(a, b)]
        commands.append(row)
        prev_ns = ns
    cmd_rows = commands
    cmd_by_seq_out = {r["seq"]: r for r in cmd_rows}

    # dynamic rows
    dynamic_rows = []
    for p in sorted(dyn_pairs, key=lambda p: int(p["enter"]["f"]["ns"])):
        en, rt = p["enter"], p["return"]
        dynamic_rows.append({
            "event": p["event"],
            "tid": en["f"].get("tid"),
            "ns": to_int(en["f"].get("ns")),
            "return_ns": to_int(rt["f"].get("ns")),
            "duration_ns": p["duration_ns"],
            "flags": en["f"].get("flags"),
            "module": en["f"].get("module"),
            "caller": en["f"].get("caller"),
            "qid": rt["f"].get("QID"),
            "result": to_int(rt["f"].get("result")),
            "errno": to_int(rt["f"].get("errno")),
        })

    # complete rows
    complete_rows = []
    for p in sorted(cmp_pairs, key=lambda p: int(p["enter"]["f"]["ns"])):
        en, rt = p["enter"], p["return"]
        complete_rows.append({
            "event": p["event"],
            "seq": to_int(en["f"].get("seq")),
            "op": to_int(en["f"].get("op")),
            "tid": en["f"].get("tid"),
            "async": en["f"].get("async"),
            "completion_source": en["f"].get("completion_source"),
            "enter_ns": to_int(en["f"].get("ns")),
            "return_ns": to_int(rt["f"].get("ns")),
            "duration_ns": p["duration_ns"],
            "status": en["f"].get("status"),
            "result": to_int(rt["f"].get("result")),
        })

    # event-id coverage: dynamic + complete ENTER ids must cover 1..max once
    all_event_ids = ([p["event"] for p in dyn_pairs] +
                     [p["event"] for p in cmp_pairs])
    event_cov = {
        "count": len(all_event_ids),
        "unique": len(set(all_event_ids)),
        "min": min(all_event_ids) if all_event_ids else None,
        "max": max(all_event_ids) if all_event_ids else None,
        "missing": sorted(set(range(1, max(all_event_ids) + 1)) -
                          set(all_event_ids)) if all_event_ids else [],
        "duplicates": len(all_event_ids) - len(set(all_event_ids)),
    }

    # ------------------------------------------------------------- key/OSD
    key_recv = tag_records("FX3_KEY_INPUT_RECV")
    key_synth = tag_records("FX3_SYNTH_KEY")
    key_done = tag_records("FX3_KEY95_STEP_DONE")
    key_cache = tag_records("FX3_KEY_CACHE")
    key_ready = tag_records("FX3_KEY96_READY")
    osd = tag_records("FX3_OSD102_COMMIT")

    key_events = []
    for r in key_recv:
        f = r["f"]
        key_events.append({
            "kind": "KEY_INPUT_RECV", "step": to_int(f.get("step")),
            "key": f.get("key"), "status": to_int(f.get("status")),
            "clock_id": f.get("clock_id"),
            "wait_enter_ns": to_int(f.get("wait_enter_ns")),
            "wait_return_ns": to_int(f.get("wait_return_ns")),
            "wait_enter_step": to_int(f.get("wait_enter_step")),
            "wait_return_step": to_int(f.get("wait_return_step")),
            "tid": f.get("tid"), "line": r["ln"]})
    for r in key_synth:
        f = r["f"]
        key_events.append({
            "kind": "SYNTH_KEY", "step": to_int(f.get("step")),
            "key": f.get("key"), "status": to_int(f.get("status")),
            "monotonic_ns": to_int(f.get("monotonic_ns")),
            "result": to_int(f.get("result")), "tid": None, "line": r["ln"]})
    key_done_row = None
    if key_done:
        f = key_done[0]["f"]
        key_done_row = {
            "kind": "KEY95_STEP_DONE", "step": to_int(f.get("step")),
            "key": f.get("key"),
            "requested_hold_ms": to_int(f.get("requested_hold_ms")),
            "measured_down_up_ns": to_int(f.get("measured_down_up_ns")),
            "elapsed_ns": to_int(f.get("elapsed_ns")),
            "wait_result": to_int(f.get("wait_result")),
            "one_down_one_up": to_int(f.get("one_down_one_up")),
            "line": key_done[0]["ln"]}
    down_recv = next((e for e in key_events
                      if e["kind"] == "KEY_INPUT_RECV" and e["status"] == 1), None)
    up_recv = next((e for e in key_events
                    if e["kind"] == "KEY_INPUT_RECV" and e["status"] == 0), None)
    down_send = next((e for e in key_events
                      if e["kind"] == "SYNTH_KEY" and e["status"] == 1), None)
    up_send = next((e for e in key_events
                    if e["kind"] == "SYNTH_KEY" and e["status"] == 0), None)

    commits = []
    for r in osd:
        f = r["f"]
        commits.append({
            "frame": to_int(f.get("frame")),
            "ns": to_int(f.get("ns")),
            "op": f.get("op"),
            "pixel_source_seq": to_int(f.get("pixel_source_seq")),
            "copied_gpe_last": to_int(f.get("copied_GPE_last")),
            "tid": f.get("tid"),
            "token": f.get("token"),
            "physical": f.get("physical"),
            "bitmap": f.get("bitmap"),
            "line": r["ln"]})
    commits.sort(key=lambda x: (x["ns"] if x["ns"] else 0, x["frame"]))
    commits_by_frame = {c["frame"]: c for c in commits}

    # ------------------------------------------------------------------ ring
    ring = load_json(NATIVE + "/osd-ring-readback.json")
    ring_frames = ring.get("frames", [])
    ring_rows = []
    for f in ring_frames:
        ring_rows.append({
            "sequence": f.get("sequence"),
            "epoch": f.get("epoch"),
            "update_id": f.get("update_id"),
            "pixel_source_sequence": f.get("pixel_source_sequence"),
            "sha256": f.get("sha256"),
            "PNG_sha256": f.get("PNG_sha256"),
            "host_monotonic": f.get("host_monotonic"),
            "committed_slot": f.get("committed_slot"),
            "width": f.get("width"), "height": f.get("height"),
        })
    ring_seq = [r["sequence"] for r in ring_rows]
    total_commits = len(commits)
    max_commit_frame = max(c["frame"] for c in commits if c["frame"])
    max_ring_seq = max(ring_seq) if ring_seq else None
    missing_from_ring = (max_ring_seq - len(ring_seq)) if max_ring_seq else None
    gaps = ring.get("sequence_gaps", [])
    gap_missing = sum(g.get("missing_count", 0) for g in gaps)
    selected_ring = [r for r in ring_rows if r["sequence"] in range(196, 206)]
    frame200 = next((r for r in ring_rows if r["sequence"] == 200), None)
    identical_after_200 = [c for c in commits
                           if c["frame"] and c["frame"] > 200 and
                           c["pixel_source_seq"] == 200]

    # ------------------------------------------------------- producer evidence
    cpipe_bound = load_json(
        DELIVERY + "/r36-fixed-slot-package/MANIFEST.json")
    gpe_binding = load_json(
        DELIVERY + "/r33-causal-observation-candidate/GPE-SOURCE-BINDING.json")
    provider_build = load_json(
        TRY2 + "/mss-all-key-contrast/passive-timing-next/build-receipt.json")
    provider_receipt = load_json(
        TRY2 + "/mss-all-key-contrast/passive-timing-next/source-receipt.json")
    dist_manifest = {
        "gpe_helper_sha256": gpe_binding.get("actual_helper_sha256"),
        "gpe_cpio_member": gpe_binding.get("actual_CPIO_member"),
        "source_hashes_match": all(
            v.get("matched") for v in
            gpe_binding.get("source_provenance", {}).values()),
        "provider_output_sha256": next(
            (row.get("output_sha256") for row in provider_build.get("rows", [])
             if row.get("kind") == "rm"), None),
        "provider_source_sha256": next(
            (row.get("candidate_sha256")
             for row in provider_receipt.get("rows", [])
             if row.get("kind") == "rm"), None),
        "provider_clock": provider_receipt.get("clock"),
        "guest_cpio_sha256": cpipe_bound.get("initrd", {}).get("sha256"),
        "guest_cpio_bytes": cpipe_bound.get("initrd", {}).get("bytes"),
    }

    members = member_binding()
    dist_manifest["member_binding"] = members

    # ------------------------------------------------------------ host/tool
    timeline = []
    with open(HOST + "/tool-timeline.jsonl", "r") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("UTC"):
                row["utc_dt"] = iso_to_dt(row["UTC"])
            row["host_ns"] = row.get("host_ns")
            timeline.append(row)
    stage_ns = {r["stage"]: r["host_ns"] for r in timeline
                if r.get("stage") and r.get("host_ns")}
    stage = {k: v / 1e9 for k, v in stage_ns.items()}
    ov1 = load_json(HOST + "/step-01-attempt-01/observation-1/observation-result.json")
    ov2 = load_json(HOST + "/step-01-attempt-01/observation-2/observation-result.json")
    click = load_json(HOST + "/step-01-attempt-01/click-receipt.json")
    result = load_json(HOST + "/RESULT.json")
    trial_input = [json.loads(l) for l in
                   open(NATIVE + "/trial-input-events.jsonl")
                   if l.strip()]
    ti = trial_input[0] if trial_input else {}
    arm_ev = None
    alarm = ov1["before"]["before"]["h"]
    for e in alarm.get("events", []):
        if e.get("event") == "armed":
            arm_ev = e
            break
    arm_wall = iso_to_dt(arm_ev["wall_UTC"])
    arm_host, utc_bracket = utc_to_host(timeline, arm_wall)
    arm_ms = arm_ev["performance_ms"]
    due_ms = alarm["current"]["due_ms"]

    def perf_to_host(ms):
        return arm_host + (ms - arm_ms) / 1000.0

    obs1_before = ov1["before"]["before"]["performance_ms"]
    obs1_after = ov1["after"]["before"]["performance_ms"]
    obs2_before = ov2["before"]["before"]["performance_ms"]
    obs2_after = ov2["after"]["before"]["performance_ms"]
    deadline_host = arm_host + result.get(
        "original_alarm_End_elapsed_ms", 20001.4) / 1000.0
    pin_entry = stage.get("operator_tool_pin_entry")
    cleanup_entry = stage.get("cleanup_entry_End_first")
    click_ret = stage.get("operator_tool_click_return_prepared")
    obs2_entry = stage.get("operator_tool_observe_entry")
    obs2_ret = stage.get("operator_tool_observe_return_prepared")
    obs1_entry = stage.get("step-01-attempt-01-observe-1_enter")
    obs1_exit = stage.get("step-01-attempt-01-observe-1_exit")

    def ns_between(a, b):
        return int(round((b - a) * 1e9)) if a is not None and b is not None else None
    gaps = {
        "click_tool_return_to_observe2_entry_ns":
            ns_between(click_ret, obs2_entry),
        "observe2_return_to_pin_entry_ns":
            ns_between(obs2_ret, pin_entry),
        "observe1_start_to_end_ns":
            ns_between(obs1_entry, obs1_exit),
        "pin_entry_after_deadline_ns":
            ns_between(deadline_host, pin_entry),
        "pin_entry_after_cleanup_ns":
            ns_between(pin_entry, cleanup_entry),
    }

    host_stages = []
    for r in timeline:
        if r.get("stage") in (
                "Start-original-button_enter", "step-01-attempt-01-arm_exit",
                "step-01-attempt-01-click_exit",
                "step-01-attempt-01-observe-1_enter",
                "step-01-attempt-01-observe-1_exit",
                "operator_tool_click_return_prepared",
                "operator_tool_observe_entry",
                "step-01-attempt-01-observe-2_enter",
                "step-01-attempt-01-observe-2_exit",
                "operator_tool_observe_return_prepared",
                "operator_tool_pin_entry",
                "cleanup_entry_End_first"):
            host_stages.append({"stage": r["stage"],
                                "host_ns": r["host_ns"],
                                "host_s": r["host_ns"] / 1e9,
                                "UTC": r.get("UTC")})

    # ---------------------------------------------------- clock bridge bounds
    frame_pairs = []
    for frame_no in (198, 199, 200):
        c = commits_by_frame.get(frame_no)
        rf = next((r for r in ring_rows if r["sequence"] == frame_no), None)
        if c and rf:
            d = rf["host_monotonic"] - c["ns"] / 1e9
            frame_pairs.append({"frame": frame_no,
                                "guest_commit_ns": c["ns"],
                                "host_read_monotonic": rf["host_monotonic"],
                                "offset_s": d})
    key_sent = ti.get("sent_monotonic")
    key_anchor = None
    if key_sent and down_recv and down_recv.get("wait_return_ns"):
        key_anchor = key_sent - down_recv["wait_return_ns"] / 1e9
    offsets = [p["offset_s"] for p in frame_pairs]
    o_low = key_anchor if key_anchor is not None else min(offsets)
    o_high = min(offsets) if offsets else None
    bridge = {
        "frame_pairs": frame_pairs,
        "frame_offset_min_s": min(offsets) if offsets else None,
        "frame_offset_max_s": max(offsets) if offsets else None,
        "frame_offset_spread_s": (max(offsets) - min(offsets)) if offsets else None,
        "key_send_anchor": key_anchor,
        "offset_bounds_s": [o_low, o_high] if o_high is not None else None,
        "offset_mid_s": ((o_low + o_high) / 2) if o_high is not None else None,
        "half_width_s": ((o_high - o_low) / 2) if o_high is not None else None,
        "note": "host_monotonic = guest_CLOCK_MONOTONIC + offset; "
                "frame reads happen at/after commit, key receive at/after send",
    }
    o_mid = bridge["offset_mid_s"]

    def guest_to_host(ns):
        if ns is None or o_mid is None:
            return None
        return ns / 1e9 + o_mid

    # -------------------------------------------------------- menu phases
    key_down_recv_ns = down_recv["wait_return_ns"] if down_recv else None
    key_up_recv_ns = up_recv["wait_return_ns"] if up_recv else None
    first_after_key = next((c for c in commits
                            if key_up_recv_ns and c["ns"] and
                            c["ns"] > key_up_recv_ns and
                            c["pixel_source_seq"] != 196), None)
    menu_frames = [commits_by_frame.get(n) for n in (198, 199, 200)]
    flush_seqs = sorted(cmp_by_seq)
    menu_flushes = [s for s in flush_seqs if s in (244, 314, 390)]
    phases = []
    bounds = [(176, 244, "A"), (245, 314, "B"), (315, 390, "C")]
    for a, b, name in bounds:
        ra, rb = cmd_by_seq_out.get(a), cmd_by_seq_out.get(b)
        if not ra or not rb:
            continue
        flush_commit = next((c for c in commits
                             if c["frame"] and c["copied_gpe_last"] == b), None)
        phases.append({
            "pass": name,
            "first_seq": a, "last_seq": b,
            "start_ns": ra["ns"], "end_ns": rb["ns"],
            "duration_ns": rb["ns"] - ra["ns"],
            "command_count": b - a + 1,
            "flush_seq": b,
            "flush_completion_ns": rb["ns"],
            "commit_frame": flush_commit["frame"] if flush_commit else None,
            "commit_ns": flush_commit["ns"] if flush_commit else None,
            "flush_to_commit_ns":
                (flush_commit["ns"] - rb["ns"]) if flush_commit else None,
        })
    pre_draw_gap = None
    if phases and key_up_recv_ns:
        pre_draw_gap = phases[0]["start_ns"] - key_up_recv_ns
    inter_pass = []
    for i in range(len(phases) - 1):
        inter_pass.append({
            "after_pass": phases[i]["pass"],
            "before_pass": phases[i + 1]["pass"],
            "gap_ns": phases[i + 1]["start_ns"] - phases[i]["end_ns"],
        })
    first_menu = commits_by_frame.get(198)
    full_menu = commits_by_frame.get(200)
    menu_timeline = {
        "key_down_receive_ns": key_down_recv_ns,
        "key_up_receive_ns": key_up_recv_ns,
        "key_down_send_ns": down_send["monotonic_ns"] if down_send else None,
        "key_up_send_ns": up_send["monotonic_ns"] if up_send else None,
        "step_done": key_done_row,
        "key_down_to_first_menu_ns":
            (first_menu["ns"] - key_down_recv_ns)
            if first_menu and key_down_recv_ns else None,
        "key_up_to_first_menu_ns":
            (first_menu["ns"] - key_up_recv_ns)
            if first_menu and key_up_recv_ns else None,
        "key_down_to_full_menu_ns":
            (full_menu["ns"] - key_down_recv_ns)
            if full_menu and key_down_recv_ns else None,
        "key_up_to_full_menu_ns":
            (full_menu["ns"] - key_up_recv_ns)
            if full_menu and key_up_recv_ns else None,
        "pre_first_gpe_gap_ns": pre_draw_gap,
        "passes": phases,
        "inter_pass_gaps": inter_pass,
        "first_menu_commit": first_menu,
        "full_menu_commit": full_menu,
        "first_menu_commit_host_est":
            guest_to_host(first_menu["ns"]) if first_menu else None,
        "full_menu_commit_host_est":
            guest_to_host(full_menu["ns"]) if full_menu else None,
    }

    # ------------------------------------------------------------ slow calls
    dyn_sorted_dur = sorted(
        (r for r in dynamic_rows if r["duration_ns"] is not None),
        key=lambda r: r["duration_ns"], reverse=True)
    cmp_sorted_dur = sorted(
        (r for r in complete_rows if r["duration_ns"] is not None),
        key=lambda r: r["duration_ns"], reverse=True)
    cmd_deltas = [r for r in cmd_rows if r["delta_ns"] is not None]
    cmd_deltas_sorted = sorted(cmd_deltas, key=lambda r: r["delta_ns"],
                               reverse=True)
    slow = {
        "dynamic_top": dyn_sorted_dur[:10],
        "dynamic_count": len(dynamic_rows),
        "dynamic_max_ns": dyn_sorted_dur[0]["duration_ns"] if dyn_sorted_dur else None,
        "complete_top": cmp_sorted_dur[:10],
        "complete_count": len(complete_rows),
        "complete_max_ns": cmp_sorted_dur[0]["duration_ns"] if cmp_sorted_dur else None,
        "command_interval_top": [
            {"seq": r["seq"], "op": r["op"], "delta_ns": r["delta_ns"],
             "ns": r["ns"]} for r in cmd_deltas_sorted[:12]],
        "command_interval_median_ns":
            statistics.median([r["delta_ns"] for r in cmd_deltas])
            if cmd_deltas else None,
        "command_interval_p95_ns":
            sorted(r["delta_ns"] for r in cmd_deltas)[
                int(0.95 * (len(cmd_deltas) - 1))] if cmd_deltas else None,
        "lock_wait_rows": len(tag_records("FX3_GPE102_LOCK_WAIT")),
    }
    for p in phases:
        p["command_deltas_ns"] = [
            r["delta_ns"] for r in cmd_rows
            if r["seq"] is not None and p["first_seq"] < r["seq"] <= p["last_seq"]
            and r["delta_ns"] is not None]
        if p["command_deltas_ns"]:
            p["median_delta_ns"] = statistics.median(p["command_deltas_ns"])
            p["max_delta_ns"] = max(p["command_deltas_ns"])

    # ------------------------------------------------------- coverage/limits
    coverage = {
        "gpe_cmd_records": len(cmd_recs),
        "gpe_cmd_return_records": len(ret_recs),
        "cmd_seq_count": len(cmd_by_seq),
        "return_seq_count": len(ret_by_seq),
        "seq_min": min(seqs) if seqs else None,
        "seq_max": max(seqs) if seqs else None,
        "seq_set_equal": set(cmd_by_seq) == set(ret_by_seq),
        "seq_missing_in_returns": sorted(set(cmd_by_seq) - set(ret_by_seq)),
        "seq_missing_in_commands": sorted(set(ret_by_seq) - set(cmd_by_seq)),
        "scope_records": len(scope_recs),
        "draw_interval_records": len(draw_recs),
        "raw_params_records": len(raw_recs),
        "flush_seq_count": len(flush_seqs),
        "draw_seq_count": len(seqs) - len(flush_seqs),
        "flush_seqs": flush_seqs,
        "seqs_without_scope": sorted(set(seqs) - scope_seq),
        "scope_without_cmd": sorted(scope_seq - set(seqs)),
        "complete_seq_set_equals_no_scope_seqs":
            set(cmp_by_seq) == (set(seqs) - scope_seq),
        "complete_seq_count": len(cmp_by_seq),
        "dynamic_enter": len(dynamic_enter),
        "dynamic_return": len(dynamic_return),
        "dynamic_pairs": len(dyn_pairs),
        "dynamic_unmatched_enter": dyn_unmatched_in,
        "dynamic_unmatched_return": dyn_unmatched_out,
        "dynamic_field_mismatches": dyn_mismatch,
        "complete_unmatched_enter": cmp_unmatched_in,
        "complete_unmatched_return": cmp_unmatched_out,
        "complete_field_mismatches": cmp_mismatch,
        "event_id_coverage": event_cov,
        "osd_commit_records": len(commits),
        "serial_parse": parse_stats,
        "ring_frames_retained": len(ring_rows),
        "ring_max_sequence": max_ring_seq,
        "max_commit_frame": max_commit_frame,
        "ring_missing_to_max_sequence": missing_from_ring,
        "ring_gap_sum_missing": gap_missing,
        "ring_retention": ring.get("retention"),
        "ring_scope": ring.get("scope"),
        "repeated_identical_commits_after_200": len(identical_after_200),
    }

    # ------------------------------------------------------- host analysis
    host = {
        "arm_wall_UTC": arm_ev.get("wall_UTC"),
        "arm_performance_ms": arm_ms,
        "arm_host_monotonic_est": arm_host,
        "arm_utc_bracket_s": utc_bracket,
        "due_performance_ms": due_ms,
        "alarm_end_host_monotonic_est": deadline_host,
        "pin_entry_host_monotonic": pin_entry,
        "pin_entry_after_deadline_s":
            (pin_entry - deadline_host) if pin_entry else None,
        "click_request_monotonic": ti.get("requested_monotonic"),
        "click_sent_monotonic": key_sent,
        "click_host_end": click.get("host_end_ns"),
        "observation_1": {
            "performance_before_ms": obs1_before,
            "performance_after_ms": obs1_after,
            "host_before_est": perf_to_host(obs1_before),
            "host_after_est": perf_to_host(obs1_after),
            "displayed_sequence_before":
                ov1["before"]["displayed_frame"]["sequence"],
            "displayed_sequence_after":
                ov1["after"]["displayed_frame"]["sequence"],
            "displayed_png_before":
                ov1["before"]["displayed_frame"]["PNG_sha256"],
            "displayed_png_after":
                ov1["after"]["displayed_frame"]["PNG_sha256"],
            "relative_to_arm_s": (obs1_before - arm_ms) / 1000.0,
        },
        "observation_2": {
            "performance_before_ms": obs2_before,
            "performance_after_ms": obs2_after,
            "host_before_est": perf_to_host(obs2_before),
            "host_after_est": perf_to_host(obs2_after),
            "displayed_sequence_before":
                ov2["before"]["displayed_frame"]["sequence"],
            "displayed_sequence_after":
                ov2["after"]["displayed_frame"]["sequence"],
            "displayed_png_before":
                ov2["before"]["displayed_frame"]["PNG_sha256"],
            "relative_to_arm_s": (obs2_before - arm_ms) / 1000.0,
        },
        "gaps_ns": gaps,
        "stages": host_stages,
    }

    # ------------------------------------------------------- clock domains
    kernel_pairs = []
    for r in recs:
        if r.get("kts") and r["f"].get("ns"):
            try:
                g = int(r["f"]["ns"]) / 1e9
                k = float(r["kts"])
            except ValueError:
                continue
            if 1.0 < g < 200.0:
                kernel_pairs.append({"line": r["ln"], "tag": r["tag"],
                                     "kernel_s": k, "guest_ns": int(r["f"]["ns"]),
                                     "guest_s": g,
                                     "k_minus_31_25g_s": k - 31.25 * g})
    clk = {
        "domains": [
            {"id": "G", "name": "guest CLOCK_MONOTONIC",
             "clock_gettime_id": 1,
             "proven_in": [
                 "fx3-gpe-command-wait102-v1.h: GPE102_CLOCK_MONOTONIC 1; gpe102_now()",
                 "fx3-complete104-observe-v1.h: gpe104_* ns=gpe102_now()",
                 "fx3-osd-r35.c: timing_ns() clock_gettime(1); tags print clock_id=1",
                 "fx3-rm-empty-provider-v8-long-use-timing.c: now() clock_gettime(1)",
                 "fx3-rm-key-gate-v6-long-use.inc: KEY95_STEP_DONE uses now()",
             ],
             "used_for": ["GPE104", "GPE102", "KEY95/96", "OSD102_COMMIT",
                          "OSD owner tags"],
             "subtraction_rule": "only against G"},
            {"id": "K", "name": "guest kernel printk timestamp [N]",
             "proven_in": ["no producer source used in this analysis"],
             "used_for": ["ordering only"],
             "note": "Observed K ~= 31.25*G + 10.79 s; not a proven "
                     "second-domain clock; never subtracted.",
             "same_line_pairs": len(kernel_pairs),
             "offset_mean_s": statistics.mean(
                 [p["k_minus_31_25g_s"] for p in kernel_pairs])
                 if kernel_pairs else None,
             "offset_stdev_s": statistics.pstdev(
                 [p["k_minus_31_25g_s"] for p in kernel_pairs])
                 if kernel_pairs else None},
            {"id": "H", "name": "host monotonic",
             "used_for": ["tool timeline", "QMP ring readback",
                          "pin/deadline host actions"],
             "bridge_to_G": bridge},
            {"id": "B", "name": "browser performance_ms (document origin)",
             "used_for": ["arm/alarm/observation windows"],
             "bridge_to_H": "arm wall UTC interpolated over host tool timeline "
                            "(bracket %.3f s)" % utc_bracket},
            {"id": "U", "name": "UTC wall clock",
             "used_for": ["cross-check only"]},
        ],
        "producer_binding": dist_manifest,
        "kernel_relation_examples": kernel_pairs[:8],
    }

    # --------------------------------------------------------- attribution
    attribution = {
        "measured_guest": {
            "key_down_to_first_menu_ns": menu_timeline["key_down_to_first_menu_ns"],
            "key_down_to_full_menu_ns": menu_timeline["key_down_to_full_menu_ns"],
            "key_up_to_full_menu_ns": menu_timeline["key_up_to_full_menu_ns"],
            "passes": [{k: p[k] for k in (
                "pass", "duration_ns", "first_seq", "last_seq",
                "flush_to_commit_ns", "commit_frame")} for p in phases],
            "inter_pass_gaps_ns": inter_pass,
            "dynamic_max_ns": slow["dynamic_max_ns"],
            "complete_max_ns": slow["complete_max_ns"],
            "command_interval_median_ns": slow["command_interval_median_ns"],
        },
        "host_scheduling_gap": {
            "click_return_to_observe2_entry_ns": gaps[
                "click_tool_return_to_observe2_entry_ns"],
            "observe2_return_to_pin_entry_ns": gaps[
                "observe2_return_to_pin_entry_ns"],
            "pin_entry_after_deadline_ns": gaps["pin_entry_after_deadline_ns"],
            "note": "these host intervals overlap guest progress and are not "
                    "firmware compute time",
        },
        "unknown": {
            "pre_first_gpe_gap_ns": pre_draw_gap,
            "command_start_time": "not logged; only completion cadence known",
            "why_three_passes": "no semantic labels; 198/199/200 hashes differ",
            "kernel_clock_scale_cause": "no producer source",
            "browser_display_lag": "obs1 showed seq197 while ring already "
                                    "held frame198; compositor/publish lag "
                                    "not instrumented",
            "cpu_time": "not measurable from these logs",
        },
    }

    # ---------------------------------------------------------------- result
    out = {
        "schema": "fx3-r40-menu-timing/v1",
        "generated_UTC": dt.datetime.now(dt.timezone.utc).isoformat(),
        "scope": "single r38 run read-only offline analysis; not a new run, "
                 "not a pass, not stability or FX6 evidence",
        "native_run": "v35diag-n64-r36-r37-4d245250",
        "host_run": "r38-vm-29076c7ba60e",
        "task_ids": {"worker_task": "task_1408bbfa4b9b",
                     "r38_task": "task_29076c7ba60e"},
        "key": {
            "key_code": "0x1ab", "key_decimal": 427,
            "key_name_from_trial_session": "MENU",
            "status_map": {"1": "down", "0": "up"},
            "events": key_events,
            "step_done": key_done_row,
            "one_down_one_up": key_done_row["one_down_one_up"]
                if key_done_row else None,
            "measured_down_up_ns": key_done_row["measured_down_up_ns"]
                if key_done_row else None,
        },
        "menu": menu_timeline,
        "ring": {
            "frame200": frame200,
            "selected_196_205": selected_ring,
            "repeated_identical_commits_after_200": len(identical_after_200),
            "repeated_commit_frames": [c["frame"] for c in identical_after_200
                                       if c["frame"] in (201, 230, 250, 270, 287)],
            "retained": len(ring_rows),
            "max_ring_sequence": max_ring_seq,
            "max_commit_frame": max_commit_frame,
            "missing_to_max_sequence": missing_from_ring,
            "gap_sum_missing": gap_missing,
        },
        "host": host,
        "clock_domains": clk,
        "slow": slow,
        "coverage": coverage,
        "attribution": attribution,
        "commands": cmd_rows,
        "complete": complete_rows,
        "dynamic": dynamic_rows,
        "commits": commits,
    }
    return out


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["manifest", "analyze"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--data-dir", default=None)
    args = ap.parse_args()

    if args.mode == "manifest":
        m = manifest()
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(m, f, indent=1, ensure_ascii=False)
            f.write("\n")
        print(json.dumps({"out": args.out, "count": m["count"],
                          "all_present": m["all_present"],
                          "manifest_sha256": m["manifest_sha256"]},
                         ensure_ascii=False))
        return 0 if m["all_present"] else 3

    data = build_analysis()
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
    if args.data_dir:
        os.makedirs(args.data_dir, exist_ok=True)
        write_csv(os.path.join(args.data_dir, "commands.csv"),
                  data["commands"],
                  ["seq", "op", "op_code", "tid", "ns", "delta_ns", "result",
                   "errno", "completion_source", "has_scope",
                   "has_draw_interval", "has_raw_params", "complete_event",
                   "complete_enter_ns", "complete_duration_ns",
                   "complete_status", "complete_result", "dynamic_events"])
        write_csv(os.path.join(args.data_dir, "dynamic.csv"),
                  data["dynamic"],
                  ["event", "tid", "ns", "return_ns", "duration_ns", "flags",
                   "module", "caller", "qid", "result", "errno"])
        write_csv(os.path.join(args.data_dir, "complete.csv"),
                  data["complete"],
                  ["event", "seq", "op", "tid", "async", "completion_source",
                   "enter_ns", "return_ns", "duration_ns", "status", "result"])
        write_csv(os.path.join(args.data_dir, "osd-commits.csv"),
                  data["commits"],
                  ["frame", "ns", "op", "pixel_source_seq", "copied_gpe_last",
                   "tid", "token", "physical", "bitmap", "line"])
        write_csv(os.path.join(args.data_dir, "ring-frames.csv"),
                  data["ring"]["selected_196_205"],
                  ["sequence", "epoch", "update_id", "pixel_source_sequence",
                   "sha256", "PNG_sha256", "host_monotonic", "committed_slot"])
    print(json.dumps({"out": args.out,
                      "commands": len(data["commands"]),
                      "dynamic": len(data["dynamic"]),
                      "complete": len(data["complete"]),
                      "key_down_to_full_menu_ns":
                          data["menu"]["key_down_to_full_menu_ns"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
