#!/usr/bin/env python3
"""Read-only newc CPIO/manifest binding audit; never extracts or executes members.

This checks file provenance, not runtime success, compatibility or authorization.
Only member names, sizes, hashes and self-authored diagnostic marker names leave
the archive. JSON goes to stdout. A mismatch produces exit status 1.
"""
import argparse
import datetime as dt
import hashlib
import json
import mmap
from pathlib import Path, PurePosixPath
import plistlib
import re
import stat
import subprocess

UUID = "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"
MARKERS = (b"FX6_APP_CONFIG_ENTRY", b"FX6_APP_CONFIG_HOLD")
DEFAULT_MEMBERS = ("init", "usr/bin/appfw-launch", "usr/lib/appFw.so",
                   "usr/lib/AppConfig.so", "usr/lib/libgrm-fbinit9.so",
                   "usr/lib/libuxengine.so", "usr/share/app/global.xdb")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(name):
    p = PurePosixPath(name)
    if p.is_absolute() or ".." in p.parts or (not p.parts and name != "."):
        raise ValueError("unsafe archive member name")
    return str(p)


def scan(data):
    rows, pos, archive_index, trailers = {}, 0, 0, 0
    nonzero = re.compile(b"[^\x00]")
    while pos + 110 <= len(data):
        if data[pos] == 0:
            match = nonzero.search(data, pos)
            if match is None:
                break
            pos = match.start()
        h = data[pos:pos + 110]
        if h[:6] != b"070701":
            raise ValueError(f"expected newc header at {pos}")
        fields = [int(h[i:i + 8], 16) for i in range(6, 110, 8)]
        mode, size, namesize = fields[1], fields[6], fields[11]
        if not 1 <= namesize <= 4096 or pos + 110 + namesize > len(data):
            raise ValueError("invalid member name bounds")
        raw = data[pos + 110:pos + 110 + namesize]
        if raw[-1:] != b"\0" or b"\0" in raw[:-1]:
            raise ValueError("invalid member name terminator")
        name = raw[:-1].decode("utf-8", "strict")
        start = (pos + 110 + namesize + 3) & ~3
        end = start + size
        next_pos = (end + 3) & ~3
        if next_pos > len(data):
            raise ValueError("truncated member payload or padding")
        if name == "TRAILER!!!":
            if size:
                raise ValueError("nonempty trailer")
            trailers += 1
            archive_index += 1
            pos = next_pos
            continue
        name = canonical(name)
        payload = data[start:end]
        rows.setdefault(name, []).append({"bytes": size, "sha256": digest(payload),
                      "archive_index": archive_index, "offset": start,
                      "regular_file": stat.S_ISREG(mode), "hardlink_count": fields[4],
                      "diagnostic_markers": [m.decode() for m in MARKERS if m in payload]})
        pos = next_pos
    if any(data[pos:]):
        raise ValueError("unparsed nonzero trailing data")
    if not rows:
        raise ValueError("empty CPIO member index")
    return rows, trailers


def claims(obj, prefix=""):
    if isinstance(obj, dict):
        if isinstance(obj.get("member"), str) and isinstance(obj.get("sha256"), str):
            yield prefix, obj["member"], obj["sha256"]
        for k, v in obj.items():
            yield from claims(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from claims(v, f"{prefix}[{i}]")


def audit(manifest_path, members):
    raw_manifest = manifest_path.read_bytes()
    m = json.loads(raw_manifest)
    path = Path(m["initrd"]["path"])
    before = path.stat()
    with path.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as data:
        actual_hash = digest(data)
        histories, trailers = scan(data)
        rows = {name: versions[-1] for name, versions in histories.items()}
    after = path.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError("CPIO changed during audit")
    if manifest_path.read_bytes() != raw_manifest:
        raise ValueError("manifest changed during audit")
    checks = []
    for field, name, expected in claims(m):
        row = rows.get(name)
        item = {"field": field, "claimed_member": name, "expected_sha256": expected}
        if row is None:
            item["status"] = "member_not_found_exactly"
            # Annotated historical names are diagnostic hints, never exact bindings.
            hint = name.split(" (", 1)[0]
            if hint in rows:
                item["diagnostic_candidate_member"] = hint
                item["diagnostic_actual_sha256"] = rows[hint]["sha256"]
        else:
            item["actual_sha256"] = row["sha256"]
            item["status"] = "match" if row["sha256"] == expected else "sha256_mismatch"
        checks.append(item)
    loader_paths = [s.split("loader,file=", 1)[1].split(",addr=", 1)[0]
                    for s in m.get("candidate_argv_before_observer_serial_retarget", [])
                    if s.startswith("loader,file=") and ",addr=0x440000000," in s]
    container_ok = actual_hash == m["initrd"]["sha256"] and before.st_size == m["initrd"]["bytes"]
    loader_ok = loader_paths == [str(path)]
    member_ok = all(c["status"] == "match" for c in checks)
    return {"schema": "fx6-cpio-member-binding-audit-v1",
            "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "scope": "offline provenance only; no guest execution or authorization decision",
            "manifest": {"path": str(manifest_path), "sha256": digest(raw_manifest)},
            "initrd": {"path": str(path), "bytes": before.st_size, "sha256": actual_hash},
            "container_binding_matches": container_ok, "loader_binding_matches": loader_ok,
            "archive_trailer_count": trailers, "distinct_member_count": len(rows),
            "index_semantics": "last archive occurrence; does not emulate kernel hardlink or filesystem extraction",
            "member_claims": checks,
            "selected_actual_members": {n: rows.get(n) for n in members},
            "selected_member_histories": {n: histories[n] for n in members if n in histories and len(histories[n]) > 1},
            "diagnostic_marker_members": {n: r for n, r in rows.items() if r["diagnostic_markers"]},
            "verdict": "match" if container_ok and loader_ok and member_ok else "binding_inconsistent"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest", type=Path)
    p.add_argument("--member", action="append", default=[])
    args = p.parse_args()
    if str(args.manifest.resolve()).startswith("/Volumes/KAFU2T/"):
        info = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
        if info.get("VolumeUUID") != UUID or info.get("MountPoint") != "/Volumes/KAFU2T":
            raise RuntimeError("external volume identity mismatch")
    result = audit(args.manifest, tuple(dict.fromkeys((*DEFAULT_MEMBERS, *args.member))))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["verdict"] == "match" else 1


if __name__ == "__main__":
    raise SystemExit(main())
