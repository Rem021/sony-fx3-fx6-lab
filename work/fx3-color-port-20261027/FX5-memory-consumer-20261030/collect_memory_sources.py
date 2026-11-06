#!/usr/bin/env python3
"""Read bounded source members from an already downloaded, pinned public GPL archive."""
import datetime
import hashlib
import json
import pathlib
import plistlib
import subprocess
import tarfile

BASE = pathlib.Path(__file__).resolve().parent
PREVIOUS = BASE.parents[1] / "sony-firmware-20261024/stage133-FX5-source-availability-and-portability"
EXACT = {
    "linux-kernel/arch/arm64/mm/init.c",
    "linux-kernel/arch/arm64/mm/mmu.c",
    "linux-kernel/arch/arm64/mm/ioremap.c",
    "linux-kernel/arch/arm64/kernel/setup.c",
    "linux-kernel/arch/arm64/kernel/head.S",
    "linux-kernel/drivers/of/fdt.c",
    "linux-kernel/drivers/of/address.c",
    "linux-kernel/drivers/of/of_reserved_mem.c",
    "linux-kernel/include/dt-bindings/arm/memtype.h",
    "linux-kernel/include/linux/dma-direct.h",
}


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            value.update(part)
    return value.hexdigest()


def main():
    volume = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert volume["VolumeUUID"] == "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"
    assert not (BASE / "source-capture.json").exists()
    metadata = json.loads((PREVIOUS / "fx5-gpl-download-receipt.json").read_bytes())
    original = next(item for item in metadata["records"] if item["path"] == "gpl-archives/linux-kernel.tar.gz")
    archive = PREVIOUS / original["path"]
    assert archive.stat().st_size == original["bytes"] == 151522353
    assert digest(archive) == original["sha256"] == "1e1cf32816e841462bd1d0f4e93c4897a44d0a9b95641387c74cafb6d6f44190"
    output = BASE / "sources"
    output.mkdir(exist_ok=False)
    selected = []
    candidates = []
    count = 0
    with tarfile.open(archive, "r|gz") as source:
        for member in source:
            count += 1
            if not member.isfile():
                continue
            name = member.name
            if any(term in name.lower() for term in ["rmem", "iomap", "cxd"]) and name.endswith((".c", ".h", ".S")):
                candidates.append({"member": name, "bytes": member.size})
            if name not in EXACT:
                continue
            assert member.size <= 1024 * 1024
            data = source.extractfile(member).read()
            path = output / name.removeprefix("linux-kernel/")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            selected.append({"member": name, "path": path.relative_to(BASE).as_posix(), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    assert {item["member"] for item in selected} == EXACT
    record = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "official_model_page": metadata["official_model_page"], "archive": str(archive),
        "archive_url": original["url"], "archive_sha256": original["sha256"],
        "archive_bytes": archive.stat().st_size, "archive_entries_scanned": count,
        "selected_sources": selected, "filename_candidates_not_yet_captured_or_read": candidates,
        "download_repeated": False, "third_party_source_built_or_executed": False, "device_actions": 0}
    (BASE / "source-capture.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"archive_entries_scanned": count, "selected_source_members": len(selected), "candidate_path_count": len(candidates)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
