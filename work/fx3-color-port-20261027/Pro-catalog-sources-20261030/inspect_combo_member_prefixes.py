#!/usr/bin/env python3
"""Inspect two stored firmware member prefixes without downloading whole members."""
import sys
sys.dont_write_bytecode = True
import datetime
import hashlib
import json
import pathlib
import plistlib
import struct
import subprocess
import urllib.error
import urllib.request
from capture_pages import BASE


def main():
    volume = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert volume["VolumeUUID"] == "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"
    assert sys.argv[1:] in ([], ["--prefix-etag"])
    suffix = "-prefix-etag" if sys.argv[1:] else ""
    assert not (BASE / ("combo-member-prefixes" + suffix + ".json")).exists()
    original = json.loads((BASE / "combo-zip-inspection.json").read_bytes())
    assert original["result"] == "CENTRAL_DIRECTORY_READ_ONLY"
    url = original["encoded_request_url"]
    etags = [row["headers"].get("ETag") for row in original["requests"]]
    requested_etag = etags[0] if suffix else etags[-1]
    selected = [row for row in original["members"] if row["name"].endswith(("AXS-R7_V600_firmware.f.bin", "MPC-3610_V610_firmware.bin"))]
    assert len(selected) == 2 and all(row["compression_method"] == 0 and not row["flags"] & 1 for row in selected)
    output = BASE / ("combo-member-prefixes" + suffix)
    output.mkdir(exist_ok=False)
    records = []
    for member in selected:
        filename = pathlib.PurePosixPath(member["name"]).name
        start = member["local_header_offset"]
        record = {"member_basename": filename, "local_header_offset": start, "requested_bytes": 4096, "full_member_downloaded": False,
            "request_If_Match": requested_etag, "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        try:
            headers = {"User-Agent": "FirmwareCatalogResearch/1.0", "Accept-Encoding": "identity", "Range": "bytes=" + str(start) + "-" + str(start + 4095), "If-Match": requested_etag}
            request = urllib.request.Request(url, headers=headers)
            try:
                response = urllib.request.urlopen(request, timeout=25)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                raw = response.read(4096)
                record.update({"http_status": response.code, "http_date": response.headers.get("Date"), "response_ETag": response.headers.get("ETag"),
                    "Content_Range": response.headers.get("Content-Range")})
            path = output / (filename + ".range4096.bin")
            path.write_bytes(raw)
            record.update({"path": path.relative_to(BASE).as_posix(), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
            if record["http_status"] != 206:
                record["result"] = "RANGE_OR_OBJECT_PRECONDITION_NOT_SATISFIED"
            else:
                assert record["Content_Range"] == "bytes " + str(start) + "-" + str(start + 4095) + "/" + str(original["remote_archive_bytes"])
                fields = struct.unpack_from("<4s5H3I2H", raw)
                assert fields[0] == b"PK\x03\x04" and fields[3] == 0
                name_length, extra_length = fields[9], fields[10]
                name_bytes = raw[30:30 + name_length]
                assert name_bytes == member["name"].encode("cp437")
                assert fields[7] == member["compressed_bytes"] and fields[8] == member["uncompressed_bytes"]
                assert fields[6] == int(member["declared_CRC32"], 0)
                offset = 30 + name_length + extra_length
                fragment = raw[offset:]
                payload = output / (filename + ".payload-prefix.bin")
                payload.write_bytes(fragment)
                record.update({"result": "MEMBER_PREFIX_ONLY", "local_header_matches_central_directory": True,
                    "payload_prefix_path": payload.relative_to(BASE).as_posix(), "payload_prefix_bytes": len(fragment),
                    "payload_prefix_sha256": hashlib.sha256(fragment).hexdigest(), "first16_hex": fragment[:16].hex(),
                    "response_ETag_matches_requested": record["response_ETag"] == requested_etag,
                    "tar_ustar_at_257": fragment[257:262] == b"ustar"})
                properties = []
                cursor = 0
                while record["tar_ustar_at_257"] and cursor + 512 <= len(fragment):
                    header = fragment[cursor:cursor + 512]
                    if not any(header):
                        break
                    if header[257:262] != b"ustar":
                        break
                    declared_sum = int(header[148:156].strip(b" \0"), 8)
                    assert sum(header[:148]) + 8 * 32 + sum(header[156:]) == declared_sum
                    name = header[:100].split(b"\0", 1)[0].decode("ascii", "replace")
                    size = int(header[124:136].strip(b" \0") or b"0", 8)
                    entry = {"tar_member_name": name, "declared_bytes": size, "complete_in_prefix": cursor + 512 + size <= len(fragment)}
                    if entry["complete_in_prefix"] and name.endswith("property.xml"):
                        entry["property_xml"] = fragment[cursor + 512:cursor + 512 + size].decode("utf-8", "replace")
                    properties.append(entry)
                    cursor += 512 + ((size + 511) // 512) * 512
                record["tar_prefix_members"] = properties
        except Exception as error:
            record["result"] = "BOUNDED_PREFIX_INSPECTION_GAP"
            record["error"] = {"type": type(error).__name__, "message": str(error)}
        records.append(record)
    result = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "records": records,
        "earlier_range_ETags_equal": len(set(etags)) == 1,
        "identity_warning": "The initial prefix and suffix had different ETags. Do not claim a single verified whole archive or assemble a flashable file from these ranges.",
        "CRC_of_whole_members_verified": False, "complete_private_loader_or_ISP_obtained": False, "device_actions": 0}
    result["If_Match_selection"] = "Observed original prefix version" if suffix else "Observed original suffix version"
    (BASE / ("combo-member-prefixes" + suffix + ".json")).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
