#!/usr/bin/env python3
"""Bounded remote ZIP directory inspection; no full package download or code execution."""
import sys
sys.dont_write_bytecode = True
import datetime
import hashlib
import json
import plistlib
import re
import struct
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from capture_pages import BASE


def main():
    volume = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert volume["VolumeUUID"] == "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"
    assert not (BASE / "combo-zip-inspection.json").exists()
    source = json.loads((BASE / "registered-target-queries.json").read_bytes())
    info = next(row for row in source["records"] if row["case"] == "VENICE-AXSR7-known-info")
    assert info["entry"]["id"] == "00003067" and len(info["entry"]["downloadPath"]) == 1
    supplied_url = info["entry"]["downloadPath"][0]
    parts = urllib.parse.urlsplit(supplied_url)
    assert parts.scheme == "https" and parts.hostname == "www.sonystyle.com.cn"
    url = urllib.parse.urlunsplit((parts.scheme, parts.netloc, urllib.parse.quote(parts.path, safe="/"), parts.query, ""))
    output = BASE / "combo-zip-inspection"
    output.mkdir(exist_ok=False)
    record = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "source_url": supplied_url, "encoded_request_url": url,
        "requests": [], "full_package_downloaded": False, "archive_members_extracted": False, "CRC_or_whole_file_identity_verified": False,
        "account_or_device_operations": 0, "scope": "Only public server range bytes and central-directory metadata; no private payload readability claim."}

    def fetch(label, range_header, limit):
        item = {"label": label, "requested_range": range_header, "read_cap": limit, "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        req = urllib.request.Request(url, headers={"User-Agent": "FirmwareCatalogResearch/1.0", "Range": range_header, "Accept-Encoding": "identity"})
        try:
            response = urllib.request.urlopen(req, timeout=25)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            data = response.read(limit)
            item.update({"http_status": response.code, "final_url": response.url,
                "headers": {key: response.headers.get(key) for key in ["Content-Type", "Content-Length", "Content-Range", "Date", "ETag"] if response.headers.get(key)}})
        path = output / (label + ".bin")
        path.write_bytes(data)
        item.update({"path": path.relative_to(BASE).as_posix(), "bytes_read": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        record["requests"].append(item)
        return item, data

    try:
        first, prefix = fetch("prefix4096", "bytes=0-4095", 4096)
        record["ZIP_local_header_present"] = prefix.startswith(b"PK\x03\x04")
        if first["http_status"] not in (200, 206) or not record["ZIP_local_header_present"]:
            record["result"] = "SOURCE_URL_DID_NOT_YIELD_A_ZIP_PREFIX"
        else:
            tail_record, tail = fetch("suffix65557", "bytes=-65557", 65557)
            content_range = tail_record["headers"].get("Content-Range", "")
            match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", content_range)
            if tail_record["http_status"] != 206 or not match:
                record["result"] = "RANGE_NOT_CONFIRMED_NO_DIRECTORY_CLAIM"
            else:
                start, end, total = map(int, match.groups())
                assert end == total - 1 and end - start + 1 == len(tail)
                marker = tail.rfind(b"PK\x05\x06")
                assert marker >= 0 and marker + 22 <= len(tail)
                signature, disk, cd_disk, disk_entries, entries, cd_bytes, cd_offset, comment_length = struct.unpack_from("<4s4H2IH", tail, marker)
                assert marker + 22 + comment_length == len(tail)
                assert disk == cd_disk == 0 and disk_entries == entries
                assert 0 < entries <= 1000 and 0 < cd_bytes <= 1024 * 1024
                assert cd_offset + cd_bytes <= total
                if start <= cd_offset and cd_offset + cd_bytes <= start + len(tail):
                    directory = tail[cd_offset - start:cd_offset - start + cd_bytes]
                else:
                    extra, directory = fetch("central-directory", "bytes=" + str(cd_offset) + "-" + str(cd_offset + cd_bytes - 1), cd_bytes)
                    assert extra["http_status"] == 206 and len(directory) == cd_bytes
                    assert extra["headers"].get("Content-Range") == "bytes " + str(cd_offset) + "-" + str(cd_offset + cd_bytes - 1) + "/" + str(total)
                position = 0
                members = []
                while position < len(directory):
                    fields = struct.unpack_from("<4s6H3I5H2I", directory, position)
                    assert fields[0] == b"PK\x01\x02"
                    flags, method, crc, compressed, uncompressed = fields[3], fields[4], fields[7], fields[8], fields[9]
                    name_length, extra_length, comment_length = fields[10:13]
                    assert position + 46 + name_length + extra_length + comment_length <= len(directory)
                    name_bytes = directory[position + 46:position + 46 + name_length]
                    name = name_bytes.decode("utf-8" if flags & 0x800 else "cp437", "replace")
                    members.append({"name": name, "flags": flags, "compression_method": method, "compressed_bytes": compressed,
                        "uncompressed_bytes": uncompressed, "local_header_offset": fields[16], "declared_CRC32": hex(crc)})
                    position += 46 + name_length + extra_length + comment_length
                assert position == len(directory) and len(members) == entries
                record.update({"result": "CENTRAL_DIRECTORY_READ_ONLY", "remote_archive_bytes": total, "members": members,
                    "separate_program_members": [row["name"] for row in members if row["name"].lower().endswith((".exe", ".dll", ".so", ".dylib", ".app"))]})
    except Exception as error:
        record["result"] = "BOUNDED_INSPECTION_GAP"
        record["error"] = {"type": type(error).__name__, "message": str(error)}
    (BASE / "combo-zip-inspection.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
