#!/usr/bin/env python3
"""Read only the observed public catalogue script sources; never execute JavaScript."""
import sys
sys.dont_write_bytecode = True
import concurrent.futures
import datetime
import hashlib
import json
import plistlib
import subprocess
import urllib.request
from capture_pages import BASE


def main():
    volume = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert volume["VolumeUUID"] == "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"
    assert not (BASE / "script-capture.json").exists()
    output = BASE / "scripts"
    output.mkdir(exist_ok=False)
    pages = json.loads((BASE / "page-capture.json").read_bytes())
    wanted = {"clientlib-api.js", "clientlib-modelDetail.js", "clientlib-downloadRoom.js"}
    urls = sorted({url for page in pages["records"] for url in page.get("script_urls", []) if url.rsplit("/", 1)[-1] in wanted})
    assert len(urls) == 3

    def fetch(url):
        record = {"url": url, "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "FirmwareCatalogResearch/1.0"}), timeout=25) as response:
                data = response.read(4 * 1024 * 1024 + 1)
                assert len(data) <= 4 * 1024 * 1024
                record["http_status"] = response.status
            target = output / url.rsplit("/", 1)[-1]
            with target.open("xb") as stream:
                stream.write(data)
            record.update({"path": target.relative_to(BASE).as_posix(), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        except Exception as error:
            record["transport_error"] = {"type": type(error).__name__, "message": str(error)}
        return record

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(fetch, urls))
    (BASE / "script-capture.json").write_text(json.dumps({"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "records": records,
        "javascript_executed": False, "account_or_device_operations": 0}, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(records, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
