#!/usr/bin/env python3
"""Capture bounded official documentation and a 64-byte known-package prefix."""
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
from query_public_catalog import BASE, EXPECTED_VOLUME


def main():
    volume = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert volume["VolumeUUID"] == EXPECTED_VOLUME
    out = BASE / "official-documents"
    out.mkdir(exist_ok=False)
    cases = [
        ("creators-update.html", "https://helpguide.sony.net/di-app/ca/v1/en/contents/CA_update_software.html"),
        ("fx5-maintenance.html", "https://helpguide.sony.net/ilc/2630/v1/en/contents/maintenance.html"),
        ("fx5-location-enterprise.html", "https://helpguide.sony.net/ilc/2630/v1/en/contents/location_info.html"),
        ("fx5-japan-downloads.html", "https://support.sony.jp/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx5/downloads"),
    ]
    records = []
    for filename, url in cases:
        record = {"path": filename, "url": url, "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "FirmwareCatalogResearch/1.0"})
            with urllib.request.urlopen(req, timeout=25) as response:
                data = response.read(4 * 1024 * 1024 + 1)
                assert len(data) <= 4 * 1024 * 1024
                record.update({"http_status": response.status, "final_url": response.url})
            (out / filename).write_bytes(data)
            record.update({"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        except Exception as error:
            record["transport_error"] = {"type": type(error).__name__, "message": str(error)}
        records.append(record)
        (out / "capture-receipts.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(record, ensure_ascii=False), flush=True)
    info = json.loads((BASE / "known-info-and-model-variants/fx3-known-info/response.pretty.json").read_bytes())
    url = info["fwURL"]
    parsed = urllib.parse.urlsplit(url)
    assert parsed.scheme == "https" and parsed.hostname == "support.d-imaging.sony.co.jp" and parsed.path.endswith("/BODYDATA.DAT")
    record = {"url": url, "method": "GET", "requested_range": "bytes=0-63", "read_limit": 64,
        "authentication": "none", "device_operations": 0, "full_binary_download": False,
        "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FirmwareCatalogResearch/1.0", "Range": "bytes=0-63", "Accept-Encoding": "identity"})
        with urllib.request.urlopen(req, timeout=25) as response:
            data = response.read(64)
            record.update({"http_status": response.status, "final_url": response.url,
                "response_headers": {key: response.headers.get(key) for key in ["Content-Type", "Content-Length", "Content-Range", "ETag", "Last-Modified", "Date"] if response.headers.get(key)}})
        (out / "fx3-catalog-prefix64.bin").write_bytes(data)
        local = BASE.parents[1] / "sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"
        with local.open("rb") as source:
            local_prefix = source.read(64)
        record.update({"bytes_read": len(data), "prefix_sha256": hashlib.sha256(data).hexdigest(),
            "local_reference": str(local), "local_reference_bytes": local.stat().st_size,
            "prefix_equals_local": data == local_prefix,
            "whole_file_identity_proved": False,
            "scope": "64 bytes only; same prefix and length do not establish full-file identity or modified-package acceptance."})
    except Exception as error:
        record["transport_error"] = {"type": type(error).__name__, "message": str(error)}
    (out / "fx3-bounded-prefix-receipt.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(record, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
