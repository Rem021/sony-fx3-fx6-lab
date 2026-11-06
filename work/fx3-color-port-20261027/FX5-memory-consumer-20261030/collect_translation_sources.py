#!/usr/bin/env python3
"""Capture the concrete address/cache consumers identified by the first source pass."""
import sys
sys.dont_write_bytecode = True
import datetime
import hashlib
import json
import plistlib
import subprocess
import tarfile
from collect_memory_sources import BASE, PREVIOUS, digest

MEMBERS = {
    "linux-kernel/drivers/soc/cxd/adrs_conv.c",
    "linux-kernel/drivers/soc/cxd/mmap.c",
    "linux-kernel/drivers/soc/cxd/params.c",
    "linux-kernel/drivers/soc/cxd/udif/dma-mapping.c",
    "linux-kernel/drivers/soc/cxd/udif/cache.c",
    "linux-kernel/drivers/soc/cxd/export/mach/platform.h",
    "linux-kernel/drivers/soc/cxd/export/mach/noncache.h",
    "linux-kernel/drivers/soc/cxd/export/mach/dma32.h",
    "linux-kernel/drivers/soc/cxd/export/mach/udif/cache.h",
    "linux-kernel/include/uapi/linux/cxd-adrs_conv.h",
    "linux-kernel/drivers/soc/cxd/Makefile",
    "linux-kernel/drivers/soc/cxd/Kconfig",
    "linux-kernel/arch/arm64/include/asm/memory.h",
    "linux-kernel/arch/arm64/include/asm/pgtable-prot.h",
}


def main():
    volume = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert volume["VolumeUUID"] == "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"
    assert not (BASE / "translation-source-capture.json").exists()
    original = json.loads((BASE / "source-capture.json").read_bytes())
    archive = PREVIOUS / "gpl-archives/linux-kernel.tar.gz"
    assert digest(archive) == original["archive_sha256"]
    items = []
    with tarfile.open(archive, "r|gz") as source:
        for member in source:
            if member.name not in MEMBERS:
                continue
            assert member.isfile() and member.size <= 1024 * 1024
            data = source.extractfile(member).read()
            path = BASE / "sources" / member.name.removeprefix("linux-kernel/")
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as target:
                target.write(data)
            items.append({"member": member.name, "path": path.relative_to(BASE).as_posix(), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    assert {item["member"] for item in items} == MEMBERS
    record = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "archive_sha256": original["archive_sha256"],
        "selected_sources": items, "third_party_code_built_or_executed": False, "device_actions": 0}
    (BASE / "translation-source-capture.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"new_source_files": len(items), "paths": [item["path"] for item in items]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
