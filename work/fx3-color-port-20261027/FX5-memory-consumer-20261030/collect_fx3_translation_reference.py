#!/usr/bin/env python3
"""Read matching public FX3 7.00 source helpers; never execute or import vendor code."""
import sys
sys.dont_write_bytecode = True
import datetime
import hashlib
import json
import pathlib
import plistlib
import subprocess
import tarfile
from collect_memory_sources import BASE, PREVIOUS, digest


def main():
    volume = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert volume["VolumeUUID"] == "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"
    assert sys.argv[1:] in ([], ["--cxd900xx"])
    expanded = bool(sys.argv[1:])
    suffix = "-expanded" if expanded else ""
    assert not (BASE / ("fx3-source-capture" + suffix + ".json")).exists()
    metadata = json.loads((PREVIOUS / "fx3-gpl-reference-receipt.json").read_bytes())
    root = pathlib.Path("/Volumes/KAFU2T/AI/Projects/Mac")
    archive = root / metadata["archive_path"]
    assert digest(archive) == metadata["archive_sha256"]
    output = BASE / ("fx3-reference-sources" + suffix)
    output.mkdir(exist_ok=False)
    items = []
    candidates = []
    for_tail = {"adrs_conv.c", "dma32.h", "noncache.h", "platform.h", "dma-mapping.c", "cache.c", "cache.h"}
    selected_namespace = "drivers/udif/mach-cxd900xx/" if expanded else "mach-cxd90057/"
    with tarfile.open(archive, "r|gz") as source:
        for member in source:
            if not member.isfile():
                continue
            name = member.name
            if "cxd" in name and name.endswith(("adrs_conv.c", "dma32.h", "noncache.h", "/platform.h")):
                candidates.append(name)
            if pathlib.PurePosixPath(name).name not in for_tail:
                continue
            if not (selected_namespace in name or "drivers/soc/cxd/" in name):
                continue
            assert member.size <= 1024 * 1024
            data = source.extractfile(member).read()
            path = output / name.removeprefix("linux-kernel/")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            items.append({"member": name, "path": path.relative_to(BASE).as_posix(), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    record = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "archive": str(archive),
        "archive_sha256": metadata["archive_sha256"], "official_page": metadata["source_url"],
        "source_version": "4.9.337 / FX3 Ver7.00 publication", "scope": "Not a measurement of classic FX3 7.02 active kernel/configuration.",
        "selected_sources": items, "candidate_paths": candidates, "source_executed": False, "device_actions": 0}
    record["source_layout_query"] = selected_namespace
    (BASE / ("fx3-source-capture" + suffix + ".json")).write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"selected_files": len(items), "paths": [item["member"] for item in items], "candidate_paths": candidates}, ensure_ascii=False))


if __name__ == "__main__":
    main()
