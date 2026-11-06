#!/usr/bin/env python3
"""Derive one guarded, offline FX3 v25 CPIO. Never starts QEMU."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

from audit_original_elf import ROOT as ORIGINAL_LIB_ROOT, audit

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
BASE = PARENT / "vmopt-20261103-try2-passive-timing-v4"
BUILDER = PARENT / "build_candidate.py"
OUTPUT = HERE / "vmopt-20261104-v25-menu-osd-diagnostic"
BASE_SHA = "90adc5fda97a4b26293e4763da1ed3d5eec22eaf2f0115292c1b720c5049e9aa"
BUILDER_SHA = "7245eca988c5a6f0dd7fc3e2ac178a6162af1411908b12c1849d067c7e256cb1"
SOURCE_SHA = "d7b76e881684822f0be542ef52fbd065fa128595589d3cf0d44e491ca5c819b4"
SO_SHA = "4cab743cef3841fbc24ef066aa503ff9fc22a973bbc09750e7fcd6215cd8eb9f"
OLD_MEMBER_SHA = "8023300a7b02e69cb1ea39c1489214cabce403cc3cab39058ac00bf06cd2a636"
MEMBER = "simulation/fx3-osd-headless-v5.so"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    for path, expected in ((BUILDER, BUILDER_SHA),
                           (BASE / "candidate.json", BASE_SHA),
                           (HERE / "src/fx3-osd-headless-v25.c", SOURCE_SHA),
                           (HERE / "build/fx3-osd-headless-v25.so", SO_SHA)):
        if sha(path) != expected:
            raise ValueError("frozen input changed: " + str(path))
    elf_audit = audit(ORIGINAL_LIB_ROOT / "libObj.so")
    spec = importlib.util.spec_from_file_location("fx3_v4_cpio_builder", BUILDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OLD = BASE
    module.BUILD = HERE / "build"
    module.NEW = OUTPUT
    module.BASE_SHA = BASE_SHA
    module.REPLACEMENTS = {MEMBER: ("fx3-osd-headless-v25.so", OLD_MEMBER_SHA, SO_SHA)}
    module.main()
    manifest = OUTPUT / "candidate.json"
    candidate = json.loads(manifest.read_text())
    base = json.loads((BASE / "candidate.json").read_text())
    diag = candidate.pop("passive_timing_contract")
    candidate["passive_timing_contract"] = base["passive_timing_contract"]
    candidate["v25_diagnostic_contract"] = {
        "base_candidate": str(BASE / "candidate.json"),
        "base_sha256": BASE_SHA,
        "member": MEMBER,
        "old_member_sha256": OLD_MEMBER_SHA,
        "new_member_sha256": SO_SHA,
        "source_sha256": SOURCE_SHA,
        "changed_members": diag["changed_members"],
        "original_libObj_sha256": elf_audit["sha256"],
        "diagnostic_ring_offset": "0x2000",
        "diagnostic_ring_records": 256,
        "guest_clock_id": 1,
        "menu_handler_offset": None,
        "runtime_validated": False,
        "returns_and_original_timeouts_unchanged": True,
    }
    manifest.write_text(json.dumps(candidate, indent=2) + "\n")
    receipt = json.loads((OUTPUT / "build-receipt.json").read_text())
    receipt["candidate_sha256"] = sha(manifest)
    receipt["source_sha256"] = SOURCE_SHA
    receipt["so_sha256"] = SO_SHA
    receipt["builder_sha256"] = BUILDER_SHA
    receipt["original_elf_audit"] = elf_audit
    receipt["QEMU_started"] = False
    receipt["guest_validated"] = False
    (OUTPUT / "build-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"candidate": str(manifest),
                      "candidate_sha256": sha(manifest),
                      "cpio_sha256": receipt["initrd_sha256"],
                      "dtb_sha256": receipt["dtb_sha256"],
                      "changed_members": receipt["changed_members"]}, indent=2))


if __name__ == "__main__":
    main()
