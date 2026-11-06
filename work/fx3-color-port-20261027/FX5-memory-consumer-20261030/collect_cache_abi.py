#!/usr/bin/env python3
"""Capture generic cache-direction ABI and assembly consumers for both public baselines."""
import sys
sys.dont_write_bytecode = True
import datetime
import hashlib
import json
import pathlib
import plistlib
import subprocess
import tarfile
from collect_memory_sources import BASE, digest

TARGETS = {"include/linux/udif/cache.h", "include/linux/udif/types.h", "include/linux/udif/sg.h",
    "include/linux/dma-direction.h", "arch/arm64/include/asm/cacheflush.h", "arch/arm64/mm/cache.S"}


def main():
    volume = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert volume["VolumeUUID"] == "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"
    assert not (BASE / "cache-abi-source-capture.json").exists()
    models = [("fx5", "source-capture.json"), ("fx3", "fx3-source-capture-expanded.json")]
    records = []
    for model, source_receipt in models:
        metadata = json.loads((BASE / source_receipt).read_bytes())
        archive = pathlib.Path(metadata["archive"])
        assert digest(archive) == metadata["archive_sha256"]
        output = BASE / (model + "-cache-abi-sources")
        output.mkdir(exist_ok=False)
        items = []
        with tarfile.open(archive, "r|gz") as source:
            for member in source:
                relative = member.name.removeprefix("linux-kernel/")
                if relative not in TARGETS:
                    continue
                assert member.isfile() and member.size <= 1024 * 1024
                data = source.extractfile(member).read()
                target = output / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                items.append({"member": member.name, "path": target.relative_to(BASE).as_posix(), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        assert {item["member"].removeprefix("linux-kernel/") for item in items} == TARGETS
        records.append({"model": model, "archive_sha256": metadata["archive_sha256"], "selected_sources": items})
        print(json.dumps({"model": model, "source_files": len(items)}), flush=True)
    result = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "models": records,
        "source_built_or_executed": False, "cache_operations_executed": 0, "device_actions": 0}
    (BASE / "cache-abi-source-capture.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
