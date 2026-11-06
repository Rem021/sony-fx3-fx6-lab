#!/usr/bin/env python3
"""Anonymous, bounded Sony firmware metadata lookup; no device or updater code."""
import datetime
import hashlib
import json
import pathlib
import plistlib
import subprocess
import urllib.error
import urllib.parse
import urllib.request

BASE = pathlib.Path(__file__).resolve().parent
EXPECTED_VOLUME = "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"
URL = "https://support.d-imaging.sony.co.jp/FSErFHP8Je0xINMFVv9P/api/firmwarelist_api.php"
LIMIT = 4 * 1024 * 1024


class SonyRedirectsOnly(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlsplit(newurl)
        if parsed.scheme != "https" or parsed.hostname != "support.d-imaging.sony.co.jp":
            raise RuntimeError("Refusing redirect outside the observed Sony metadata host")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def main():
    volume = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert volume["VolumeUUID"] == EXPECTED_VOLUME
    assert BASE == pathlib.Path("/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/Creators-public-catalog-20261030")
    out = BASE / "anonymous-list-query"
    out.mkdir(exist_ok=False)
    body = {
        "locale": "pmm",
        "language": "en_US",
        "ModelList": [
            {"modelName": "ILME-FX3", "currentVersion": "0.00"},
            {"modelName": "ILME-FX5", "currentVersion": "0.00"},
            {"modelName": "ILCE-7M4", "currentVersion": "0.00"},
        ],
    }
    encoded = json.dumps(body, separators=(",", ":")).encode()
    headers = {"Content-Type": "application/json; charset=utf-8", "User-Agent": "FirmwareCatalogResearch/1.0", "Accept": "application/json"}
    (out / "request.json").write_bytes(encoded)
    record = {
        "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "method": "POST", "url": URL, "headers": headers,
        "request_sha256": hashlib.sha256(encoded).hexdigest(),
        "request_version_is_synthetic": True,
        "request_version_note": "0.00 is an explicitly declared catalogue lookup input, not a camera measurement.",
        "controls": ["ILME-FX3", "ILCE-7M4"], "target": "ILME-FX5",
        "authentication": "none; no cookies or credentials", "device_operations": 0,
        "third_party_code_executed": False,
    }
    try:
        opener = urllib.request.build_opener(SonyRedirectsOnly())
        req = urllib.request.Request(URL, data=encoded, headers=headers, method="POST")
        try:
            response = opener.open(req, timeout=30)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            data = response.read(LIMIT + 1)
            assert len(data) <= LIMIT, "Metadata exceeds declared limit"
            record.update({"http_status": response.code, "final_url": response.url,
                "response_headers": {key: response.headers.get(key) for key in ["Content-Type", "Content-Length", "Date", "Server", "Location"] if response.headers.get(key)},
                "response_bytes": len(data), "response_sha256": hashlib.sha256(data).hexdigest()})
        (out / "response.bin").write_bytes(data)
        try:
            parsed = json.loads(data)
            (out / "response.pretty.json").write_text(json.dumps(parsed, ensure_ascii=False, indent=2) + "\n")
            record["response_json_type"] = type(parsed).__name__
            record["response_top_level_keys"] = list(parsed) if isinstance(parsed, dict) else None
        except (ValueError, UnicodeDecodeError):
            record["response_json_type"] = None
    except Exception as error:
        record["transport_error"] = {"type": type(error).__name__, "message": str(error)}
    record["finished_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (out / "receipt.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
