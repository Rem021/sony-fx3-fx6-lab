#!/usr/bin/env python3
"""Public read-only metadata controls derived from observed source and HTML attributes."""
import sys
sys.dont_write_bytecode = True
import concurrent.futures
import datetime
import hashlib
import html.parser
import json
import plistlib
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from capture_pages import BASE, Links


class Attribute(html.parser.HTMLParser):
    def __init__(self, target):
        super().__init__()
        self.target = target
        self.value = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id") == self.target:
            self.value = attrs.get("path")


def main():
    volume = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert volume["VolumeUUID"] == "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"
    assert not (BASE / "china-controls.json").exists()
    output = BASE / "china-controls"
    output.mkdir(exist_ok=False)
    model = Attribute("modelPath")
    model.feed((BASE / "pages/china-FX6-model.html").read_text())
    firmware = Attribute("title")
    firmware.feed((BASE / "pages/china-FX6-firmware.html").read_text())
    assert model.value and firmware.value
    source = (BASE / "scripts/clientlib-modelDetail.js").read_text()
    page_size = int(re.search(r"pageSize2\s*:\s*(\d+)", source).group(1))
    assert 1 <= page_size <= 100
    host = "https://service.sony.com.cn"
    cases = [
        ("FX6-model-control", host + "/casch/homePageExt?" + urllib.parse.urlencode({"method": "findDownLoadPage", "currentNo": 0, "pageSize": page_size,
            "path": model.value, "downloadType": "SONY_CASCH_DOWNLOAD_FIRM", "keyword": ""})),
        ("FX6-firmware-control", host + "/casch/outDownload?" + urllib.parse.urlencode({"method": "findOne", "path": firmware.value})),
        ("global-download-html", host + "/content/casch/download.html"),
    ]

    def fetch(case):
        label, url = case
        record = {"case": label, "url": url, "method": "GET", "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "authentication": "none; no Cookie or Authorization header", "account_or_device_operations": 0}
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "FirmwareCatalogResearch/1.0", "Content-Type": "application/json"})
            try:
                response = urllib.request.urlopen(req, timeout=25)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                data = response.read(4 * 1024 * 1024 + 1)
                assert len(data) <= 4 * 1024 * 1024
                record.update({"http_status": response.code, "final_url": response.url, "content_type": response.headers.get("Content-Type"), "http_date": response.headers.get("Date")})
            path = output / (label + ".raw")
            path.write_bytes(data)
            record.update({"path": path.relative_to(BASE).as_posix(), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
            if label.endswith("html"):
                parser = Links(record["final_url"])
                parser.feed(data.decode("utf-8", "replace"))
                record["script_urls"] = parser.scripts
            else:
                parsed = json.loads(data)
                (output / (label + ".pretty.json")).write_text(json.dumps(parsed, ensure_ascii=False, indent=2) + "\n")
                record["top_level_keys"] = list(parsed) if isinstance(parsed, dict) else None
        except Exception as error:
            record["transport_error"] = {"type": type(error).__name__, "message": str(error)}
        return record

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(fetch, cases))
    record = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "model_path_from_HTML": model.value, "firmware_path_from_HTML": firmware.value,
        "page_size_from_source": page_size, "records": results, "javascript_executed": False, "firmware_binaries_downloaded": 0}
    (BASE / "china-controls.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
