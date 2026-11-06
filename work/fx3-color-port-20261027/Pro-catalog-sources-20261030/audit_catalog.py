#!/usr/bin/env python3
"""Offline consistency/scope audit of the professional catalogue investigation."""
import datetime
import hashlib
import io
import json
import pathlib
import plistlib
import struct
import subprocess
import tarfile

BASE = pathlib.Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def verify_record(row, page=False):
    if "path" not in row:
        return False
    path = BASE / row["path"]
    if page and not path.exists():
        path = BASE / "pages" / row["path"]
    data = path.read_bytes()
    assert sha(data) == row["sha256"]
    expected = row.get("bytes", row.get("bytes_read"))
    assert expected is not None and len(data) == expected
    return True


def main():
    volume = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert volume["VolumeUUID"] == "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"
    assert not (BASE / "verification-receipt.json").exists()
    batches = ["page-capture.json", "script-capture.json", "china-controls.json", "global-script-capture.json", "global-catalog-queries.json", "registered-target-queries.json"]
    for filename in batches:
        for row in load(BASE / filename)["records"]:
            assert verify_record(row, filename == "page-capture.json")
    global_rows = {row["case"]: row for row in load(BASE / "global-catalog-queries.json")["records"]}
    for row in global_rows.values():
        assert row["http_status"] == 200 and row["api_result"] is True and row["api_code"] == "00"
        data = json.loads((BASE / row["path"]).read_bytes())
        assert data == load(BASE / pathlib.Path(row["path"]).with_suffix(".pretty.json"))
    assert global_rows["ILME-FX6V"]["entries"][0]["id"] == "00002963"
    assert "6.01" in global_rows["ILME-FX6V"]["entries"][0]["title"]
    assert global_rows["ILME-FX3"]["entries"][0]["id"] == "00003048"
    assert "7.02" in global_rows["ILME-FX3"]["entries"][0]["title"]
    assert global_rows["MPC-3628"]["entries"][0]["id"] == "00003066"
    assert "5.00" in global_rows["MPC-3628"]["entries"][0]["title"]
    assert global_rows["ILME-FX5"]["entries"] == global_rows["ILME-FX5B"]["entries"] == []
    registered = global_rows["registered-ILME-series"]["relevant_registered_models"]
    assert {row["enName"] for row in registered} >= {"ILME-FX5", "ILME-FX5B", "ILME-FX6V", "ILME-FX3"}
    follow = load(BASE / "registered-target-queries.json")["records"]
    for row in follow[:2]:
        assert row["http_status"] == 200 and row["api_result"] is True and row["api_code"] == "00" and row["entries"] == []
    directory = load(BASE / "combo-zip-inspection.json")
    assert directory["result"] == "CENTRAL_DIRECTORY_READ_ONLY" and len(directory["members"]) == 13
    assert directory["separate_program_members"] == [] and directory["remote_archive_bytes"] == 231304333
    for row in directory["requests"]:
        assert verify_record(row)
    assert directory["requests"][0]["headers"]["ETag"] != directory["requests"][1]["headers"]["ETag"]
    initial = load(BASE / "combo-member-prefixes.json")
    current = load(BASE / "combo-member-prefixes-prefix-etag.json")
    for row in initial["records"] + current["records"]:
        assert verify_record(row)
        if row["http_status"] == 412:
            assert row["bytes"] == 0 and row["result"] == "RANGE_OR_OBJECT_PRECONDITION_NOT_SATISFIED"
    axs = next(row for row in current["records"] if row["member_basename"] == "AXS-R7_V600_firmware.f.bin")
    assert axs["http_status"] == 206 and axs["response_ETag_matches_requested"] and axs["local_header_matches_central_directory"]
    payload = (BASE / axs["payload_prefix_path"]).read_bytes()
    assert len(payload) == 3996 and sha(payload) == axs["payload_prefix_sha256"]
    assert payload[:16].hex() == "000001354158532d5237000000000000"
    source = load(BASE / "fwtool-source-capture.json")
    archive = (BASE / source["archive_path"]).read_bytes()
    assert sha(archive) == source["archive_sha256"]
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as container:
        for row in source["selected_sources"]:
            assert verify_record(row)
            original = "fwtool.py-" + source["commit"] + "/" + row["repository_path"]
            assert container.extractfile(original).read() == (BASE / row["path"]).read_bytes()
    parser_row = next(row for row in source["selected_sources"] if row["repository_path"].endswith("msfirm.py"))
    parser = (BASE / parser_row["path"]).read_text()
    assert "header[20:-20] == b'\\0' * 88" in parser
    assert payload[:128][20:-20] != bytes(88)
    old = BASE.parent / "FX3-runtime-DMA-binding-20261030"
    manifest = old / "final-receipt.json"
    assert sha(manifest.read_bytes()) == "9290a2729f20324c4c44056f9b8129d05b172a2b753e1b80740ba2bb00d87ea8"
    previous = load(manifest)
    for row in previous["files"]:
        data = (old / row["path"]).read_bytes()
        assert len(data) == row["bytes"] and sha(data) == row["sha256"]
    signature_inputs = []
    for filename, expected in [("official-key-rsa-verification-results.json", "323965d979d40bf71497fb4311cffe55e924fde6c431ded07662c304d10d503b"),
        ("native-openssl-verification-results.json", "896f3344b01324b5d4603d117e1cba6068bfd98cdf85eea43a3bf2892316c519")]:
        path = BASE.parent / "input-20261028" / filename
        assert sha(path.read_bytes()) == expected
        signature_inputs.append({"path": str(path), "sha256": expected, "original_tests_replayed": False})
    requirements_path = BASE.parent / "full-goal-readiness-20261029/readiness-audit.json"
    requirements = load(requirements_path)["requirements"]
    assert len(requirements) == 9
    result = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "status": "PASS_SCOPED_CATALOG_AND_PREFIX_EVIDENCE_NOT_FLASH_READINESS",
        "catalogue_API_JSON_requests_verified": 12, "registered_ILME_models_returned": 12, "registered_FX5_family_models": 2,
        "FX5_family_empty_queries": 4, "named_positive_control_models": ["ILME-FX6V", "ILME-FX3", "MPC-3628", "MPC-3610"],
        "positive_control_note": "FX3 returned one 7.02 payload item plus one instructions-only item; do not count it as two firmware binaries.",
        "global_support_route_note": "Observed professional FX5 support link went via sony.co.jp global entry to Sony UK product URL; direct captures were HTTP403, not a proof of absent downloads.",
        "old_combo_archive_directory_entries": 13, "range_identity_warning": "Initial prefix and suffix ETags differ. No single verified whole archive was assembled.",
        "AXSR7_prefix_bytes": 3996, "AXSR7_prefix_msfirm_structural_result": "False for the pinned isMsFirm zero-middle-header prerequisite. No key or cipher attempts; not a global decoder-absence claim.",
        "AXSR7_complete_member_or_loader_obtained": False, "VENICE_new_private_inner_recovered": False,
        "requirements_preserved": requirements, "signature_evidence_reused": signature_inputs,
        "prior_sealed_files_verified": len(previous["files"]),
        "previous_goal_turn_classification": "progress: discovered anonymous professional catalogue endpoints and successful FX6 controls before interruption",
        "current_goal_turn_classification": "progress: registered target-path queries, scoped positive/negative metadata and an independently rejected format candidate change further donor investigation",
        "readiness_change": "none", "full_objective_preserved": True, "goal_complete": False,
        "native_goal_status": "active", "modified_or_flashable_firmware_produced": False,
        "device_actions": 0, "Sony_native_programs_or_downloaded_source_executed": False,
        "signing_key_work": False, "other_owner_files_written_or_tools_run": False}
    (BASE / "verification-receipt.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ["status", "catalogue_API_JSON_requests_verified", "FX5_family_empty_queries", "AXSR7_prefix_msfirm_structural_result", "readiness_change", "goal_complete"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
