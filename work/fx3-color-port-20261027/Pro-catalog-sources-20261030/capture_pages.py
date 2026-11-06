#!/usr/bin/env python3
"""Anonymous bounded captures of observed Sony professional support entry points."""
import concurrent.futures
import datetime
import hashlib
import html.parser
import json
import pathlib
import plistlib
import subprocess
import urllib.error
import urllib.parse
import urllib.request

BASE = pathlib.Path(__file__).resolve().parent
CASES = [
    ("pro-FX5.html", "https://pro.sony/ue_US/products/handheld-camcorders/ilme-fx5"),
    ("global-FX5.html", "https://www.sony.co.jp/en/ILME-FX5/"),
    ("china-FX6-model.html", "https://service.sony.com.cn/content/casch/products/di/ILME-FX6V.html"),
    ("china-FX6-firmware.html", "https://service.sony.com.cn/download/firm/00002963.html"),
]


class Links(html.parser.HTMLParser):
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.scripts = []
        self.links = []

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if tag == "script" and attributes.get("src"):
            self.scripts.append(urllib.parse.urljoin(self.url, attributes["src"]))
        if tag == "a" and attributes.get("href"):
            url = urllib.parse.urljoin(self.url, attributes["href"])
            if any(term in url.lower() for term in ["fx5", "download", "support", "firmware"]):
                self.links.append(url)


def capture(case):
    filename, url = case
    record = {"path": filename, "url": url, "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "authentication": "none; no cookies, Sony account, serial or credentials", "device_actions": 0}
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "FirmwareCatalogResearch/1.0"})
        try:
            response = urllib.request.urlopen(request, timeout=25)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            data = response.read(8 * 1024 * 1024 + 1)
            assert len(data) <= 8 * 1024 * 1024
            record.update({"http_status": response.code, "final_url": response.url,
                "headers": {key: response.headers.get(key) for key in ["Content-Type", "Content-Length", "Date", "Server"] if response.headers.get(key)}})
        (BASE / "pages" / filename).write_bytes(data)
        record.update({"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        parser = Links(record["final_url"])
        parser.feed(data.decode("utf-8", "replace"))
        record["script_urls"] = list(dict.fromkeys(parser.scripts))
        record["relevant_links"] = list(dict.fromkeys(parser.links))
    except Exception as error:
        record["transport_error"] = {"type": type(error).__name__, "message": str(error)}
    return record


def main():
    volume = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert volume["VolumeUUID"] == "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"
    assert not (BASE / "page-capture.json").exists()
    (BASE / "pages").mkdir(exist_ok=False)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(capture, CASES))
    result = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "records": records,
        "javascript_executed": False, "downloaded_firmware_binaries": 0, "device_actions": 0}
    (BASE / "page-capture.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"records": [{"path": row["path"], "status": row.get("http_status"), "bytes": row.get("bytes"),
        "final_url": row.get("final_url"), "error": row.get("transport_error"), "script_urls": row.get("script_urls"), "relevant_links": row.get("relevant_links")} for row in records]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
