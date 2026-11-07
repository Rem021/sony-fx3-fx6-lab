#!/usr/bin/env python3
"""Completed-run provenance, runtime code-write and per-thread wchan review."""
import argparse
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import io
import struct
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def summarize_threads(lines):
    active = None
    rows = []
    for i, line in enumerate(lines, 1):
        m = re.search(r"FX6_NATIVE_THREAD_BEGIN_(\d+)", line)
        if m:
            active = {"tid": int(m[1]), "begin_line": i, "observations": []}
            continue
        m = re.search(r"FX6_NATIVE_THREAD_END_(\d+)", line)
        if m and active:
            active["end_line"] = i
            active["balanced_tid"] = active["tid"] == int(m[1])
            rows.append(active)
            active = None
        elif active:
            active["observations"].append({"line": i, "text": line})
    if active:
        active["end_line"] = None
        rows.append(active)
    return rows


def vma_bytes(e, raw, vma, size):
    for s in e.iter_segments():
        if s["p_type"] == "PT_LOAD" and s["p_vaddr"] <= vma < vma + size <= s["p_vaddr"] + s["p_filesz"]:
            off = s["p_offset"] + vma - s["p_vaddr"]
            return raw[off:off + size]
    raise ValueError("unmapped ELF VMA")


def patch_evidence(shim, appfw):
    se = ELFFile(io.BytesIO(shim))
    ae = ELFFile(io.BytesIO(appfw))
    syms = {}
    for section in se.iter_sections():
        if section["sh_type"] in ("SHT_SYMTAB", "SHT_DYNSYM"):
            syms.update({x.name: x for x in section.iter_symbols() if x["st_shndx"] != "SHN_UNDEF"})
    names = ("Application_System_Init", "fx6_patch_blocking_calls", "fx6_patch_blocking_calls.offs", "_ZNK7MonCtrl7GetFlagEv")
    result = {"actual_shim_symbols": {n: {"vma": hex(syms[n]["st_value"]), "bytes": syms[n]["st_size"]}
               for n in names if n in syms}}
    if "fx6_patch_blocking_calls.offs" in syms:
        s = syms["fx6_patch_blocking_calls.offs"]
        table = vma_bytes(se, shim, s["st_value"], s["st_size"])
        offsets = struct.unpack("<" + "Q" * (len(table) // 8), table)
        dis = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
        targets = []
        for off in offsets:
            original = vma_bytes(ae, appfw, off, 4)
            targets.append({"appfw_offset": hex(off), "container_bytes": original.hex(),
                "container_instruction": [x.mnemonic + " " + x.op_str for x in dis.disasm(original, off)],
                "source_requested_replacement": "1f2003d5 (AArch64 nop)",
                "runtime_bytes_read_back": False})
        result["patch_targets_from_actual_shim_offset_table"] = targets
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--scanner", type=Path, required=True)
    p.add_argument("--base-review", type=Path, required=True)
    p.add_argument("--source-dir", type=Path, required=True)
    a = p.parse_args()
    scanner = load(a.scanner, "cpio_binding")
    review = load(a.base_review, "completed_run_review")
    runs, inits = [], []
    for number in (291, 292, 293):
        r, init = review.run_review(a.root, number, scanner)
        if r["status"] != "completed":
            raise ValueError(f"candidate {number} has no completed receipt")
        run = a.root / "runs" / r["run"]
        raw = (run / "serial.log").read_bytes()
        lines = raw.decode(errors="replace").splitlines()
        patterns = {
            "assert": r"\bassert at |Assertion .*failed|assertion .*failed",
            "segv": r"APPFW_SEGV|SEGV \(PC=|\bsegmentation fault\b",
            "kernel_oops": r"\bOops:|Internal error:|Kernel panic|\bBUG:|\bUnable to handle kernel",
        }
        r["fault_scan"] = {k: [{"line": i + 1, "text": l[:700]}
                for i, l in enumerate(lines) if re.search(pattern, l, re.I)]
                for k, pattern in patterns.items()}
        r["fault_scan_limit"] = "Absence means no matching marker in this finite raw serial artifact; it is not proof that all faults are impossible. Kernel panic=-1 command line is not counted."
        r["runtime_patch_markers"] = [{"line": i + 1, "text": l} for i, l in enumerate(lines)
            if re.search(r"FX6_PATCH_NOP|fix_got_table: base=|fix_got_detail:", l)]
        r["appfw_pid_lines"] = [{"line": i + 1, "text": l} for i, l in enumerate(lines) if "FX6_NATIVE_APPFW_PID=" in l]
        r["all_thread_wchan_samples"] = summarize_threads(lines)
        r["thread225_samples"] = [x for x in r["all_thread_wchan_samples"] if x["tid"] == 225]
        r["init_launch_and_thread_observer"] = [{"line": i + 1, "text": l} for i, l in enumerate(init.splitlines())
            if re.search(r"LD_PRELOAD|/usr/bin/(appfw-launch|im.elf|bootin.elf)|appfw_pid|NATIVE_THREAD|/proc/\$appfw_pid|wchan|/stack|/status|/syscall", l)]
        r["unexpected_ipc_markers"] = [{"line": i + 1, "text": l[:700]} for i, l in enumerate(lines)
            if re.search(r"UNHANDLED_SOURCE|no_reply=1|ret = -1020", l)]
        r["artifact_inventory"] = [f.name for f in run.iterdir()]
        # Native exception monitor does not emit APPFW_SEGV register names.
        r["generic_crash_task_context"] = [{"line": i + 1, "text": l}
            for i, l in enumerate(lines) if re.search(r"\[current task\]|^program:|^address:|^SEGV \(PC=|^IABT |^DABT ", l)]
        # Bind /tmp build outputs without loading or executing their ELF code.
        rows = r["full_container_binding"]["selected_actual_members"]
        cpio = Path(r["full_container_binding"]["initrd"]["path"])
        r["binary_patch_evidence"] = patch_evidence(review.payload(cpio, rows["usr/lib/libgrm-fbinit9.so"]),
                                                    review.payload(cpio, rows["usr/lib/appFw.so"]))
        binaries = {}
        for temp_name, member in ((f"/tmp/libgrm-fbinit25-{number}.so", "usr/lib/libgrm-fbinit9.so"),
                                  ("/tmp/appfw/appfw-launch288", "usr/bin/appfw-launch")):
            temp = Path(temp_name)
            if temp.exists():
                binaries[temp_name] = {**review.fp(temp), "cpio_member": member,
                    "sha_matches_cpio_member": review.digest(temp) == rows[member]["sha256"]}
        r["related_temp_binary_bindings"] = binaries
        runs.append(r)
        inits.append(init)
    comparisons = []
    for old_i, new_i in ((0, 1), (1, 2), (0, 2)):
        old, new = runs[old_i], runs[new_i]
        oldlibs, newlibs = old["all_effective_library_entries"], new["all_effective_library_entries"]
        changed = {n: {"before": oldlibs.get(n), "after": newlibs.get(n)}
            for n in sorted(oldlibs.keys() | newlibs.keys()) if oldlibs.get(n) != newlibs.get(n)}
        oldmembers = old["full_container_binding"]["selected_actual_members"]
        newmembers = new["full_container_binding"]["selected_actual_members"]
        comparisons.append({"from": old["candidate"], "to": new["candidate"],
            "library_member_changes": changed,
            "launcher_bytes_changed": oldmembers["usr/bin/appfw-launch"]["sha256"] != newmembers["usr/bin/appfw-launch"]["sha256"],
            "appfw_container_bytes_changed": oldmembers["usr/lib/appFw.so"]["sha256"] != newmembers["usr/lib/appFw.so"]["sha256"],
            "init_diff": list(difflib.unified_diff(inits[old_i].splitlines(), inits[new_i].splitlines(),
                fromfile=f"candidate{old['candidate']}/init", tofile=f"candidate{new['candidate']}/init", lineterm=""))})
    sources = {}
    for f in a.source_dir.iterdir():
        if f.is_file():
            text = f.read_text()
            sources[f.name] = {**review.fp(f), "write_or_patch_lines": [
                {"line": i + 1, "text": l} for i, l in enumerate(text.splitlines())
                if re.search(r"mprotect|fx6_patch|0x12d82|0xc09e50|d503201f|__clear_cache|\*\(unsigned int \*\)|got_tab\[i\]|pg\[0\]|p\[0\]|q\[0\]", l)]}
    src1 = a.source_dir / "libgrm-fbinit25-291.c"
    src3 = a.source_dir / "libgrm-fbinit25-293.c"
    source_diff = list(difflib.unified_diff(src1.read_text().splitlines(), src3.read_text().splitlines(),
        fromfile=src1.name, tofile=src3.name, lineterm=""))
    print(json.dumps({"schema": "fx6-candidate293-completed-review-v1", "scope": "offline artifacts only",
        "dependencies": [review.fp(a.scanner), review.fp(a.base_review)],
        "runs": runs, "comparisons": comparisons, "source_snapshots": sources,
        "shim291_to293_source_diff": source_diff,
        "runtime_integrity_limit": "Whole-container original appFw SHA does not describe post-mprotect code writes or GOT rewrites in guest memory. No post-write runtime byte readback exists in these inspected artifacts.",
        "thread_identity_limit": "Per-task /proc/.../wchan samples bind PID/TID and kernel wait symbol only; no user PC, thread name, syscall args, queue id or user stack is recorded by this observer."}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
