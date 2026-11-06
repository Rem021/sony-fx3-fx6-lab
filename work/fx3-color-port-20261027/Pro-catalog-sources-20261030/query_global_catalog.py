#!/usr/bin/env python3
"""Bounded anonymous catalogue lookups for named target and control models."""
import sys
sys.dont_write_bytecode = True
import concurrent.futures
import datetime
import hashlib
import json
import plistlib
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from capture_pages import BASE


def main():
    volume = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert volume["VolumeUUID"] == "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"
    assert not (BASE / "global-catalog-queries.json").exists()
    output = BASE / "global-catalog-queries"
    output.mkdir(exist_ok=False)
    source = (BASE / "scripts/clientlib-downloadList.js").read_text()
    assert 'method=findPage&currentNo=' in source and '&enName=' in source
    page_size = int(re.search(r"pageSize\s*:\s*(\d+)", source).group(1))
    assert page_size == 5
    model_source = (BASE / "scripts/clientlib-modelList.js").read_text()
    assert 'method=findProList&series=' in model_source
    controls = json.loads((BASE / "china-controls.json").read_bytes())
    series = controls["model_path_from_HTML"].rsplit("/", 1)[0]
    host = "https://service.sony.com.cn"
    models = ["ILME-FX6V", "ILME-FX3", "ILME-FX5", "ILME-FX5B", "MPC-3628", "MPC-3610"]
    cases = [(model, host + "/casch/outDownload?" + urllib.parse.urlencode({"method": "findPage", "currentNo": 0, "pageSize": page_size,
        "downloadType": "SONY_CASCH_DOWNLOAD_FIRM", "path": "", "enName": model})) for model in models]
    cases.append(("registered-ILME-series", host + "/casch/outProduct?" + urllib.parse.urlencode({"method": "findProList", "series": series})))

    def fetch(case):
        label, url = case
        record = {"case": label, "url": url, "method": "GET", "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "authentication": "none; no Cookie or Authorization", "account_or_device_operations": 0}
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "FirmwareCatalogResearch/1.0", "Content-Type": "application/json"})
            try:
                response = urllib.request.urlopen(request, timeout=25)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                data = response.read(4 * 1024 * 1024 + 1)
                assert len(data) <= 4 * 1024 * 1024
                record.update({"http_status": response.code, "final_url": response.url, "content_type": response.headers.get("Content-Type"), "http_date": response.headers.get("Date")})
            path = output / (label + ".raw")
            path.write_bytes(data)
            record.update({"path": path.relative_to(BASE).as_posix(), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
            parsed = json.loads(data)
            (output / (label + ".pretty.json")).write_text(json.dumps(parsed, ensure_ascii=False, indent=2) + "\n")
            record["api_result"] = parsed.get("result")
            record["api_code"] = parsed.get("code")
            returned = parsed.get("returnData") or {}
            record["page"] = returned.get("Page")
            items = returned.get("Data") or []
            record["returned_items"] = len(items) if isinstance(items, list) else None
            if label == "registered-ILME-series":
                record["relevant_registered_models"] = [{key: item.get(key) for key in ["enName", "path"]} for item in items if item.get("enName") in models]
            else:
                record["entries"] = [{key: item.get(key) for key in ["id", "title", "path", "downloadPath"]} for item in items]
        except Exception as error:
            record["transport_error"] = {"type": type(error).__name__, "message": str(error)}
        return record

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(fetch, cases))
    result = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "source_scripts": ["scripts/clientlib-modelList.js", "scripts/clientlib-downloadList.js"],
        "records": records, "JavaScript_executed": False, "firmware_binaries_downloaded": 0,
        "negative_scope": "Only these named model queries and the returned registered ILME series; not worldwide absence or evidence of private firmware readability."}
    (BASE / "global-catalog-queries.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(records, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
