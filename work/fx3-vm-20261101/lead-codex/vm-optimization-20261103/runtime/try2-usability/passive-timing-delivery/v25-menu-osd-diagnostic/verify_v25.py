#!/usr/bin/env python3
"""Targeted offline verification for the frozen FX3 v25-r2 candidate."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from audit_original_elf import ROOT as ORIGINAL_LIB_ROOT, audit
from test_v25_diag import main as parser_test

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "src/fx3-osd-headless-v25-r2.c"
SO = HERE / "build/fx3-osd-headless-v25-r2.so"
BASE_SOURCE = HERE.parents[1] / "mss-all-key-contrast/passive-timing-next/src/fx3-osd-headless-v7-observe102-timing.c"
BASE_SO = HERE.parents[1] / "mss-all-key-contrast/passive-timing-next/build/osd-timing.so"
CANDIDATE = HERE / "vmopt-20261104-v25-menu-osd-diagnostic-r2/candidate.json"
BUILD = CANDIDATE.parent / "build-receipt.json"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def undefined_symbols(path):
    return set(subprocess.check_output(["xcrun", "llvm-nm", "-D", "-u", str(path)], text=True).splitlines())


def main():
    parser_test()
    elf = audit(ORIGINAL_LIB_ROOT / "libObj.so")
    source = SOURCE.read_text()
    base = BASE_SOURCE.read_text()
    for call in ("int rc=hwait(id,timeout)", "int rc=hsignal(id)",
                 "if(ack_freed&&!ho_signal_begin(&hm,id,kind))",
                 "if(consume&&!rc)((U *)ring)[6]++",
                 "else if(consume&&rc)hm.failed=1"):
        if source.count(call) != base.count(call) or source.count(call) != 1:
            raise AssertionError("native call/gate altered: " + call)
    if source.count("*__errno_location()=saved;") < base.count("*__errno_location()=saved;"):
        raise AssertionError("errno restoration reduced")
    for event in ("V25_PRODUCE_ENTER", "V25_PRODUCE_RETURN", "V25_RECEIVE", "V25_COMMIT",
                  "V25_WAIT_ENTER", "V25_WAIT_RETURN", "V25_SIGNAL_ENTER", "V25_SIGNAL_RETURN"):
        if source.count(event) < 2:
            raise AssertionError("missing event site: " + event)
    new_imports = sorted(undefined_symbols(SO) - undefined_symbols(BASE_SO))
    if new_imports:
        raise AssertionError("new undefined imports: " + repr(new_imports))
    candidate = json.loads(CANDIDATE.read_text())
    receipt = json.loads(BUILD.read_text())
    if sha(CANDIDATE) != receipt["candidate_sha256"]:
        raise AssertionError("candidate receipt SHA mismatch")
    if sha(SOURCE) != candidate["v25_diagnostic_contract"]["source_sha256"]:
        raise AssertionError("source SHA mismatch")
    if sha(SO) != candidate["v25_diagnostic_contract"]["new_member_sha256"]:
        raise AssertionError("SO SHA mismatch")
    if sha(Path(candidate["initrd"]["path"])) != candidate["initrd"]["sha256"]:
        raise AssertionError("CPIO SHA mismatch")
    if sha(Path(candidate["dtb"]["path"])) != candidate["dtb"]["sha256"]:
        raise AssertionError("DTB SHA mismatch")
    if sha(Path(candidate["native_Backup_seed"]["path"])) != candidate["native_Backup_seed"]["sha256"]:
        raise AssertionError("seed SHA mismatch")
    if len(receipt["changed_members"]) != 1 or receipt["changed_members"][0]["member"] != "simulation/fx3-osd-headless-v5.so":
        raise AssertionError("unexpected changed CPIO members")
    result = {"status": "offline_pass", "guest_runtime_validated": False,
              "source_sha256": sha(SOURCE), "so_sha256": sha(SO),
              "candidate_sha256": sha(CANDIDATE),
              "cpio_sha256": candidate["initrd"]["sha256"],
              "dtb_sha256": candidate["dtb"]["sha256"],
              "original_libObj_sha256": elf["sha256"],
              "new_undefined_imports": new_imports,
              "changed_member_count": 1,
              "parser_cases": ["pair", "interleaved_commit", "wrap", "open_wait", "torn_slot", "truncated_readback"],
              "native_call_and_gate_sites_preserved": True,
              "original_5000ms_timeout_changed": False}
    (HERE / "verification-r2.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
