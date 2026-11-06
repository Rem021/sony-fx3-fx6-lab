#!/usr/bin/env python3
"""Read the observed global download/model catalogue implementations, without executing them."""
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
    assert not (BASE / "global-script-capture.json").exists()
    source = json.loads((BASE / "china-controls.json").read_bytes())
    page = next(row for row in source["records"] if row["case"] == "global-download-html")
    urls = [url for url in page["script_urls"] if url.rsplit("/", 1)[-1] in {"clientlib-modelList.js", "clientlib-downloadList.js"}]
    assert len(urls) == 2

    def fetch(url):
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "FirmwareCatalogResearch/1.0"}), timeout=25) as response:
            data = response.read(4 * 1024 * 1024 + 1)
            assert len(data) <= 4 * 1024 * 1024 and response.status == 200
        target = BASE / "scripts" / url.rsplit("/", 1)[-1]
        with target.open("xb") as stream:
            stream.write(data)
        return {"url": url, "path": target.relative_to(BASE).as_posix(), "HTTP_status": 200, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        records = list(pool.map(fetch, urls))
    result = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "records": records, "JavaScript_executed": False,
        "authentication": "none", "device_actions": 0}
    (BASE / "global-script-capture.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(records, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
