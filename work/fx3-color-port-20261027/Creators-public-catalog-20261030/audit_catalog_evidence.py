#!/usr/bin/env python3
"""Offline integrity and scope audit of captured public metadata; no network replays."""
import datetime
import hashlib
import io
import json
import pathlib
import plistlib
import subprocess
import tarfile

BASE = pathlib.Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(path.read_bytes())


def verify_manifest(stage):
    manifest_path = stage / "final-receipt.json"
    manifest = read_json(manifest_path)
    for item in manifest["files"]:
        data = (stage / item["path"]).read_bytes()
        assert len(data) == item["bytes"] and sha(data) == item["sha256"], item["path"]
    return {"path": str(manifest_path), "sha256": sha(manifest_path.read_bytes()), "verified_members": len(manifest["files"])}


def main():
    volume = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert volume["VolumeUUID"] == "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"
    assert not (BASE / "evidence-audit.json").exists()
    capture = read_json(BASE / "source-capture.json")
    archive = (BASE / capture["archive_path"]).read_bytes()
    assert sha(archive) == capture["archive_sha256"]
    assert len(archive) == capture["archive_bytes"]
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        for item in capture["selected_sources"]:
            data = (BASE / item["path"]).read_bytes()
            assert sha(data) == item["sha256"] and len(data) == item["bytes"]
            member_name = "CameraSync-" + capture["commit"] + "/" + item["repository_path"]
            assert tar.extractfile(member_name).read() == data
    assert len(capture["selected_sources"]) == 19
    paths = [BASE / "anonymous-list-query/receipt.json"]
    paths += sorted((BASE / "control-queries").glob("*/receipt.json"))
    paths += sorted((BASE / "known-info-and-model-variants").glob("*/receipt.json"))
    rows = []
    for receipt_path in paths:
        receipt = read_json(receipt_path)
        data = (receipt_path.parent / "response.bin").read_bytes()
        assert receipt["http_status"] == 200
        assert sha(data) == receipt["response_sha256"] and len(data) == receipt["response_bytes"]
        parsed = json.loads(data)
        assert parsed == read_json(receipt_path.parent / "response.pretty.json")
        request = None
        if receipt["method"] == "POST":
            encoded = (receipt_path.parent / "request.json").read_bytes()
            assert sha(encoded) == receipt["request_sha256"]
            request = json.loads(encoded)
            assert "ModelList" in request and "modelList" not in request
        rows.append({"receipt": str(receipt_path.relative_to(BASE)), "method": receipt["method"],
            "request": request, "response": parsed, "http_status": receipt["http_status"],
            "response_sha256": receipt["response_sha256"]})
    assert len(rows) == 12
    list_rows = [row for row in rows if row["method"] == "POST"]
    info_rows = [row for row in rows if row["method"] == "GET"]
    assert len(list_rows) == 10 and len(info_rows) == 2
    controls = []
    targets = []
    for row in list_rows:
        for item in row["response"]["firmwareList"]:
            if item["modelName"] in ("ILME-FX5", "ILME-FX5B"):
                assert item["firmwareID"] == "" and item["firmwareVersion"] == "" and item["firmwareSize"] == 0
                targets.append({"receipt": row["receipt"], "item": item, "query_language": row["request"]["language"]})
            else:
                expected = {"ILME-FX3": ("7.02", "953", 811876768), "ILCE-7M4": ("6.02", "963", 757480856)}[item["modelName"]]
                assert (item["firmwareVersion"], item["firmwareID"], item["firmwareSize"]) == expected
                controls.append({"receipt": row["receipt"], "item": item})
    assert len(controls) == 4 and len(targets) == 6
    for row in info_rows:
        assert set(row["response"]) == {"updateURL", "eulaURL", "fwURL"}
        assert "/BODYDATA.DAT" in row["response"]["fwURL"]
    documents = read_json(BASE / "official-documents/capture-receipts.json")
    for item in documents:
        data = (BASE / "official-documents" / item["path"]).read_bytes()
        assert item["http_status"] == 200 and len(data) == item["bytes"] and sha(data) == item["sha256"]
    assert len(documents) == 4
    prefix_receipt = read_json(BASE / "official-documents/fx3-bounded-prefix-receipt.json")
    prefix = (BASE / "official-documents/fx3-catalog-prefix64.bin").read_bytes()
    assert prefix_receipt["http_status"] == 206
    assert prefix_receipt["response_headers"]["Content-Range"] == "bytes 0-63/811876768"
    assert len(prefix) == 64 and sha(prefix) == prefix_receipt["prefix_sha256"]
    with pathlib.Path(prefix_receipt["local_reference"]).open("rb") as source:
        assert source.read(64) == prefix
    prior_blocked = verify_manifest(BASE.parent / "full-goal-blocked-audit-20261030")
    readiness_stage = BASE.parent / "full-goal-readiness-20261029"
    readiness_path = readiness_stage / "readiness-audit.json"
    readiness = read_json(readiness_path)
    manifest = read_json(readiness_stage / "final-receipt.json")
    entry = next(item for item in manifest["files"] if item["path"] == "readiness-audit.json")
    assert sha(readiness_path.read_bytes()) == entry["sha256"]
    for item in readiness["selected_prior_evidence"][:2]:
        data = pathlib.Path(item["path"]).read_bytes()
        assert len(data) == item["bytes"] and sha(data) == item["sha256"]
    assert len(readiness["requirements"]) == 9
    result = {
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "PASS_PUBLIC_CATALOG_EVIDENCE_NOT_FLASH_READINESS",
        "source_commit": capture["commit"], "source_archive_sha256": capture["archive_sha256"],
        "source_members_verified_against_archive": 19, "third_party_source_executed": False,
        "anonymous_metadata_requests_verified": 12, "list_requests": 10, "info_requests": 2,
        "positive_control_results": controls, "empty_FX5_family_results": targets,
        "known_info_results": info_rows, "official_documents_verified": 4,
        "known_FX3_prefix_bytes": 64, "whole_remote_binary_identity_proved": False,
        "response_envelope_date_warning": "2023-01-24T00:00:00Z is an API envelope field, not evidence of firmware publication date; observation time is each HTTP receipt.",
        "zero_version_warning": "The initial synthetic 0.00 batch omitted both positive controls; its FX5 empty result alone is not a sufficient negative control. Singleton real-version controls succeeded.",
        "negative_scope": "Only these public endpoint/model/version/language inputs on this date; not global absence, not confirmation FX5 is supported by consumer Creators App, and not a complete installed-firmware dump.",
        "prior_blocked_stage_integrity": prior_blocked,
        "prior_readiness_sha256": sha(readiness_path.read_bytes()),
        "requirements_preserved": readiness["requirements"],
        "research_progress": "A functioning anonymous catalogue -> info -> binary URL route is now reproducible with positive controls; no FX5 private payload obtained.",
        "readiness_change": "none", "goal_complete": False,
        "historical_blocked_count_reused": False,
        "resumed_goal_turn_with_same_full_readiness_blocker": 1,
        "persistent_goal_status": "active",
        "modified_package_produced": False, "flashable_package_produced": False,
        "new_VENICE_private_ISP_recovered": False,
        "device_actions": 0, "native_Sony_programs_executed": 0,
        "private_signing_key_work": False,
        "other_owner_files_written_or_processes_operated": False,
    }
    (BASE / "evidence-audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ["status", "source_members_verified_against_archive", "anonymous_metadata_requests_verified", "official_documents_verified", "research_progress", "readiness_change", "goal_complete"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
