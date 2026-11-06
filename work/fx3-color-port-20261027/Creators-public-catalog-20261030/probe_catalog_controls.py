#!/usr/bin/env python3
"""Finite anonymous control queries. Versions are analytical inputs, not device reads."""
import sys
sys.dont_write_bytecode = True
import datetime
import hashlib
import json
import plistlib
import subprocess
import urllib.error
import urllib.request
from query_public_catalog import BASE, EXPECTED_VOLUME, LIMIT, SonyRedirectsOnly, URL


def main():
    volume = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert volume["VolumeUUID"] == EXPECTED_VOLUME
    out = BASE / "control-queries"
    out.mkdir(exist_ok=False)
    cases = [
        ("fx3-en_US", "ILME-FX3", "7.00", "en_US"),
        ("a7iv-en_US", "ILCE-7M4", "6.01", "en_US"),
        ("fx5-en_US", "ILME-FX5", "1.00", "en_US"),
        ("fx3-us_en", "ILME-FX3", "7.00", "us_en"),
        ("a7iv-us_en", "ILCE-7M4", "6.01", "us_en"),
        ("fx5-us_en", "ILME-FX5", "1.00", "us_en"),
    ]
    headers = {"Content-Type": "application/json; charset=utf-8", "User-Agent": "FirmwareCatalogResearch/1.0", "Accept": "application/json"}
    records = []
    for label, model, version, language in cases:
        directory = out / label
        directory.mkdir(exist_ok=False)
        request = {"locale": "pmm", "language": language, "ModelList": [{"modelName": model, "currentVersion": version}]}
        encoded = json.dumps(request, separators=(",", ":")).encode()
        (directory / "request.json").write_bytes(encoded)
        record = {"case": label, "request": request, "synthetic_input": True,
            "method": "POST", "url": URL, "request_headers": headers,
            "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "request_sha256": hashlib.sha256(encoded).hexdigest(),
            "authentication": "none; no cookies or credentials", "device_operations": 0}
        try:
            req = urllib.request.Request(URL, data=encoded, headers=headers, method="POST")
            try:
                response = urllib.request.build_opener(SonyRedirectsOnly()).open(req, timeout=25)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                data = response.read(LIMIT + 1)
                assert len(data) <= LIMIT
                record.update({"http_status": response.code, "response_bytes": len(data),
                    "response_sha256": hashlib.sha256(data).hexdigest(), "final_url": response.url,
                    "response_headers": {key: response.headers.get(key) for key in ["Content-Type", "Content-Length", "Date", "Server"] if response.headers.get(key)}})
            (directory / "response.bin").write_bytes(data)
            try:
                parsed = json.loads(data)
                (directory / "response.pretty.json").write_text(json.dumps(parsed, ensure_ascii=False, indent=2) + "\n")
                record["parsed_response"] = parsed
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
