#!/usr/bin/env python3
"""Only query published control IDs and explicitly named FX5 model/region variants."""
import sys
sys.dont_write_bytecode = True
import datetime
import hashlib
import json
import plistlib
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from query_public_catalog import BASE, EXPECTED_VOLUME, LIMIT, SonyRedirectsOnly, URL


def main():
    volume = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert volume["VolumeUUID"] == EXPECTED_VOLUME
    out = BASE / "known-info-and-model-variants"
    out.mkdir(exist_ok=False)
    headers = {"Content-Type": "application/json; charset=utf-8", "User-Agent": "FirmwareCatalogResearch/1.0", "Accept": "application/json"}
    cases = []
    for label, source in [("fx3-known-info", "fx3-us_en"), ("a7iv-known-info", "a7iv-us_en")]:
        metadata = json.loads((BASE / "control-queries" / source / "response.pretty.json").read_bytes())
        info_url = metadata["firmwareInfoAPI"]
        parsed = urllib.parse.urlsplit(info_url)
        assert parsed.scheme == "https" and parsed.hostname == "support.d-imaging.sony.co.jp"
        item = metadata["firmwareList"][0]
        assert item["firmwareID"] in ("953", "963") and item["firmwareVersion"]
        url = info_url + "?" + urllib.parse.urlencode({"fwid": item["firmwareID"], "area": "pmm", "lang": "us_en"})
        cases.append((label, "GET", url, None))
    for label, model, language in [("fx5-jp_ja", "ILME-FX5", "jp_ja"), ("fx5b-us_en", "ILME-FX5B", "us_en"), ("fx5b-jp_ja", "ILME-FX5B", "jp_ja")]:
        request = {"locale": "pmm", "language": language, "ModelList": [{"modelName": model, "currentVersion": "1.00"}]}
        cases.append((label, "POST", URL, json.dumps(request, separators=(",", ":")).encode()))
    records = []
    for label, method, url, body in cases:
        directory = out / label
        directory.mkdir(exist_ok=False)
        record = {"case": label, "method": method, "url": url, "request_headers": headers,
            "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "authentication": "none; no cookies or credentials", "device_operations": 0,
            "firmware_id_enumeration": False, "binary_download": False}
        if body:
            (directory / "request.json").write_bytes(body)
            record.update({"request_sha256": hashlib.sha256(body).hexdigest(), "synthetic_version": True})
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            try:
                response = urllib.request.build_opener(SonyRedirectsOnly()).open(req, timeout=25)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                data = response.read(LIMIT + 1)
                assert len(data) <= LIMIT
                record.update({"http_status": response.code, "response_bytes": len(data), "final_url": response.url,
                    "response_sha256": hashlib.sha256(data).hexdigest(),
                    "response_headers": {key: response.headers.get(key) for key in ["Content-Type", "Content-Length", "Date", "Server"] if response.headers.get(key)}})
            (directory / "response.bin").write_bytes(data)
            try:
                parsed_response = json.loads(data)
                (directory / "response.pretty.json").write_text(json.dumps(parsed_response, ensure_ascii=False, indent=2) + "\n")
                record["parsed_response"] = parsed_response
            except (ValueError, UnicodeDecodeError):
                record["parsed_response"] = None
        except Exception as error:
            record["transport_error"] = {"type": type(error).__name__, "message": str(error)}
        record["finished_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (directory / "receipt.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
        records.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)
    (out / "all-receipts.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
