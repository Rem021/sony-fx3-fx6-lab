#!/usr/bin/env python3
"""Read a pinned public format implementation, without importing or executing it."""
import datetime
import hashlib
import io
import json
import pathlib
import plistlib
import subprocess
import tarfile
import urllib.request

BASE = pathlib.Path(__file__).resolve().parent
PIN = "cdba742b73eed5981480c326aeb30033aabf0223"


def main():
    volume = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert volume["VolumeUUID"] == "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"
    assert not (BASE / "fwtool-source-capture.json").exists()
    output = BASE / "format-reference"
    output.mkdir(exist_ok=False)
    url = "https://codeload.github.com/ma1co/fwtool.py/tar.gz/" + PIN
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "FirmwareCatalogResearch/1.0"}), timeout=25) as response:
        data = response.read(16 * 1024 * 1024 + 1)
        assert len(data) <= 16 * 1024 * 1024 and response.status == 200
    (output / "fwtool-pinned.tar.gz").write_bytes(data)
    members = []
    matching_paths = []
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        for member in archive:
            if not member.isfile():
                continue
            path = member.name.split("/", 1)[1]
            if "msfirm" in path.lower():
                matching_paths.append(path)
            if path != "README.md" and not path.lower().endswith("msfirm.py"):
                continue
            assert member.size < 512 * 1024
            source = archive.extractfile(member).read()
            target = output / (path.replace("/", "_") + ".source.txt")
            target.write_bytes(source)
            members.append({"repository_path": path, "path": target.relative_to(BASE).as_posix(), "bytes": len(source), "sha256": hashlib.sha256(source).hexdigest()})
    result = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "repository": "https://github.com/ma1co/fwtool.py", "commit": PIN,
        "url": url, "archive_path": "format-reference/fwtool-pinned.tar.gz", "archive_bytes": len(data), "archive_sha256": hashlib.sha256(data).hexdigest(),
        "selected_sources": members, "msfirm_named_paths": matching_paths, "source_imported_or_executed": False, "device_actions": 0}
    (BASE / "fwtool-source-capture.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
