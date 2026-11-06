#!/usr/bin/env python3
"""Follow returned model/firmware paths; no guessed download IDs or device actions."""
import sys
sys.dont_write_bytecode = True
import concurrent.futures
import datetime
import hashlib
import json
import plistlib
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from capture_pages import BASE


def main():
    volume = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert volume["VolumeUUID"] == "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"
    assert not (BASE / "registered-target-queries.json").exists()
    output = BASE / "registered-target-queries"
    output.mkdir(exist_ok=False)
    previous = json.loads((BASE / "global-catalog-queries.json").read_bytes())
    models = next(row for row in previous["records"] if row["case"] == "registered-ILME-series")["relevant_registered_models"]
    cases = []
    for name in ["ILME-FX5", "ILME-FX5B"]:
        model = next(row for row in models if row["enName"] == name)
        query = {"method": "findDownLoadPage", "currentNo": 0, "pageSize": 6, "path": model["path"], "downloadType": "SONY_CASCH_DOWNLOAD_FIRM", "keyword": ""}
        cases.append((name + "-registered-path", "https://service.sony.com.cn/casch/homePageExt?" + urllib.parse.urlencode(query)))
    venice = next(row for row in previous["records"] if row["case"] == "MPC-3610")["entries"]
    assert len(venice) == 1 and venice[0]["id"] == "00003067"
    cases.append(("VENICE-AXSR7-known-info", "https://service.sony.com.cn/casch/outDownload?" + urllib.parse.urlencode({"method": "findOne", "path": venice[0]["path"]})))

    def fetch(case):
        label, url = case
        record = {"case": label, "url": url, "method": "GET", "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "authentication": "none; no Cookie/Authorization", "path_provenance": "Exact path from returned public model or firmware metadata"}
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "FirmwareCatalogResearch/1.0", "Content-Type": "application/json"})
            try:
                response = urllib.request.urlopen(request, timeout=25)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                data = response.read(4 * 1024 * 1024 + 1)
                assert len(data) <= 4 * 1024 * 1024
                record.update({"http_status": response.code, "http_date": response.headers.get("Date"), "final_url": response.url})
            target = output / (label + ".raw")
            target.write_bytes(data)
            record.update({"path": target.relative_to(BASE).as_posix(), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
            parsed = json.loads(data)
            (output / (label + ".pretty.json")).write_text(json.dumps(parsed, ensure_ascii=False, indent=2) + "\n")
            record.update({"api_code": parsed.get("code"), "api_result": parsed.get("result")})
            body = parsed.get("returnData") or {}
            record["page"] = body.get("Page")
            items = body.get("Data")
            if isinstance(items, list):
                record["entries"] = [{key: row.get(key) for key in ["id", "title", "path", "downloadPath"]} for row in items]
            elif isinstance(items, dict):
                record["entry"] = {key: items.get(key) for key in ["id", "title", "path", "downloadPath", "fileSize"]}
                record["history_counts"] = {key: len(items.get(key) or []) for key in ["downloadHistory", "otherDownloadHistory"]}
        except Exception as error:
            record["transport_error"] = {"type": type(error).__name__, "message": str(error)}
        return record

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(fetch, cases))
    result = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "records": records,
        "firmware_binary_downloaded": False, "account_or_device_operations": 0}
    (BASE / "registered-target-queries.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(records, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
