#!/usr/bin/env python3
"""Offline completed-run comparison using the coordinator's complete CPIO scanner."""
import argparse
import difflib
import hashlib
import importlib.util
import io
import json
import mmap
from pathlib import Path
import re
from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationSection

WANTED = (
    "init", "usr/bin/appfw-launch", "usr/lib/appFw.so", "usr/lib/AppConfig.so",
    "usr/lib/libgrm-fbinit9.so", "usr/lib/libMWF.so", "usr/lib/libuxengine.so",
    "usr/lib/libgrm.so", "usr/lib/libstella.so", "usr/lib/liblibra.so",
    "usr/lib/libosal_utm.so", "usr/lib/libosal_uipc.so", "usr/lib/libosal_udate.so",
    "usr/lib/libosal_ulogio.so", "usr/lib/libosal.so", "usr/share/app/global.xdb",
)
EVENT = re.compile(r"FX6_APP_CONFIG|FX6_APPFW_|FX6_NATIVE_|FX6_GRM_|FX6_UX_|"
    r"FX6_OSD_FLUSH|mpMemoryHeap|mpTextHeap|fix_got_table|appfw-launch:|"
    r"APPFW_SEGV|APPFW_PC_MODULE|APPFW_LR_MODULE|assert at|function:|SEGV \(PC=|"
    r"WidgetSystemFactory|SetGlobalFactory|FX6_GPE_FILLRECT|FX6_GPE_RECTBLIT")


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def fp(path):
    return {"path": str(path), "sha256": digest(path), "bytes": path.stat().st_size}


def payload(path, row):
    if row is None:
        return None
    with path.open("rb") as f:
        f.seek(row["offset"])
        data = f.read(row["bytes"])
    if hashlib.sha256(data).hexdigest() != row["sha256"]:
        raise ValueError("member changed since full audit")
    return data


def map_vma(e, raw, vma, size):
    for s in e.iter_segments():
        if s["p_type"] == "PT_LOAD" and s["p_vaddr"] <= vma < s["p_vaddr"] + s["p_filesz"]:
            off = s["p_offset"] + vma - s["p_vaddr"]
            return raw[off:off + size]
    return b""


def describe_mwf(raw):
    e = ELFFile(io.BytesIO(raw))
    symbols = []
    for sec in e.iter_sections():
        if sec["sh_type"] in ("SHT_DYNSYM", "SHT_SYMTAB"):
            for s in sec.iter_symbols():
                if s["st_value"] <= 0x3e908 < s["st_value"] + s["st_size"] or \
                   s["st_value"] <= 0x38f14 < s["st_value"] + s["st_size"] or \
                   s.name in ("_ZN3MWF6RsrcDP10smp_monErrE", "_ZN3MWF6RsrcDP10InitializeEv"):
                    symbols.append({"name": s.name, "vma": hex(s["st_value"]), "bytes": s["st_size"]})
    strings = {hex(v): map_vma(e, raw, v, 160).split(b"\0", 1)[0].decode(errors="replace")
               for v in (0x433c8, 0x437c7)}
    relocations = []
    for sec in e.iter_sections():
        if isinstance(sec, RelocationSection):
            syms = e.get_section(sec["sh_link"])
            for rel in sec.iter_relocations():
                if rel["r_offset"] == 0x63f08:
                    relocations.append({"vma": hex(rel["r_offset"]), "symbol": syms.get_symbol(rel["r_info_sym"]).name})
    return {"symbols": symbols, "diagnostic_strings": strings, "error_monitor_got_relocations": relocations,
            "faulting_instruction_bytes": map_vma(e, raw, 0x3e908, 8).hex(),
            "static_interpretation": "GetFlag reads byte this+0x10; caller MyPrintf error branch reads smp_monErr through GOT. Runtime X0=0 explains addr=0x10."}


def elf_sections(raw):
    e = ELFFile(io.BytesIO(raw))
    return {s.name: {"bytes": s["sh_size"], "flags": s["sh_flags"],
                       "sha256": hashlib.sha256(s.data()).hexdigest()}
            for s in e.iter_sections() if s["sh_type"] != "SHT_NOBITS"}


def run_review(root, number, scanner):
    manifest = root / f"vm-candidate-gpecap25-{number}.json"
    manifest_hash = digest(manifest)
    receipts = []
    for p in (root / "runs").glob("*/run-receipt.json"):
        d = json.loads(p.read_text())
        if d.get("manifest_sha256") == manifest_hash and d.get("process_reaped") is True and d.get("locks_released") is True:
            receipts.append((p, d))
    if not receipts:
        return {"candidate": number, "status": "no_completed_run"}, ""
    rp, receipt = max(receipts, key=lambda x: x[0].stat().st_mtime_ns)
    run = rp.parent
    watched = [rp, run / "serial.log", run / "command.json", manifest]
    pre = [(p.stat().st_size, p.stat().st_mtime_ns) for p in watched]
    binding = scanner.audit(manifest, WANTED)
    rows = binding["selected_actual_members"]
    cpio = Path(binding["initrd"]["path"])
    init = payload(cpio, rows["init"]).decode(errors="replace")
    # Reuse scan() to compare the entire library closure, including all appended members.
    with cpio.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
        history, trailers = scanner.scan(mm)
        so = {n: {"bytes": v[-1]["bytes"], "sha256": v[-1]["sha256"]}
              for n, v in history.items() if n.startswith("usr/lib/") and ".so" in n}
    serial_path = run / "serial.log"
    lines = serial_path.read_text(errors="replace").splitlines()
    events = [{"line": i + 1, "text": l[:650]} for i, l in enumerate(lines) if EVENT.search(l)]
    registers = {}
    for l in lines:
        m = re.search(r"APPFW_X(\d+)=(?:0x)?([0-9a-f]+)", l)
        if m:
            registers["x" + m[1]] = "0x" + m[2]
    exception = None
    for i, l in enumerate(lines):
        m = re.search(r"APPFW_SEGV sig=(\d+) addr=(0x[0-9a-f]+) pc=([0-9a-f]+)", l)
        if m:
            exception = {"line": i + 1, "signal": int(m[1]), "addr": m[2], "pc": "0x" + m[3]}
    if exception:
        for l in lines:
            m = re.search(r"APPFW_(PC|LR)_MODULE (\S+) base=(0x[0-9a-f]+)", l)
            if m:
                exception[m[1].lower() + "_module"] = {"path": m[2], "base": m[3]}
        if "pc_module" in exception:
            exception["pc_offset"] = hex(int(exception["pc"], 16) - int(exception["pc_module"]["base"], 16))
        if "lr_module" in exception and "x30" in registers:
            exception["lr_offset"] = hex(int(registers["x30"], 16) - int(exception["lr_module"]["base"], 16))
    frames = []
    for p in run.glob("gpe*.bin"):
        raw = p.read_bytes()
        frames.append({**fp(p), "nonzero_bytes": sum(x != 0 for x in raw)})
    members = {n: r for n, r in rows.items() if r}
    mwf = payload(cpio, rows["usr/lib/libMWF.so"])
    result = {
        "candidate": number, "status": "completed", "run": run.name,
        "receipt": fp(rp), "reason": receipt.get("reason"), "elapsed_seconds": receipt.get("elapsed_seconds"),
        "serial": fp(serial_path),
        "serial_matches_receipt": digest(serial_path) == receipt.get("logs", {}).get("serial.log", {}).get("sha256"),
        "receipt_faults": receipt.get("serial_observation", {}).get("fault_markers"),
        "full_container_binding": binding,
        "all_effective_library_entries": so,
        "init_relevant_lines": [{"line": i + 1, "text": l} for i, l in enumerate(init.splitlines())
            if re.search(r"appfw|APPFW|NATIVE_|seed-|LD_PRELOAD|LD_LIBRARY|stream|dmm|grm_ma|upm|udate|kikilog", l, re.I)],
        "observed_events": events,
        "explicit_appfw_exception": exception, "last_appfw_registers": registers,
        "mwf_static_binding": describe_mwf(mwf),
        "launcher_elf_sections": elf_sections(payload(cpio, rows["usr/bin/appfw-launch"])),
        "sampled_frames": frames,
        "widget_factory_direct_runtime_evidence": [e for e in events if re.search(r"WidgetSystemFactory|SetGlobalFactory", e["text"])],
        "source_provenance_limit": "Compiled shim is identified by the full-container member hash. No build receipt binding it to a source snapshot is present in this review; current source text is not silently equated to the executed binary.",
    }
    result["input_files_unchanged_during_review"] = pre == [(p.stat().st_size, p.stat().st_mtime_ns) for p in watched]
    return result, init


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--scanner", type=Path, required=True)
    p.add_argument("--candidates", type=int, nargs="+", default=[287, 288, 289, 290])
    a = p.parse_args()
    spec = importlib.util.spec_from_file_location("coordinator_cpio_scanner", a.scanner)
    scanner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scanner)
    runs, inits = [], []
    for n in a.candidates:
        r, init = run_review(a.root, n, scanner)
        runs.append(r)
        inits.append(init)
    comparisons = []
    for i in range(1, len(runs)):
        prev, cur = runs[i - 1], runs[i]
        if prev["status"] != "completed" or cur["status"] != "completed":
            continue
        keys = prev["all_effective_library_entries"].keys() | cur["all_effective_library_entries"].keys()
        changed = {n: {"before": prev["all_effective_library_entries"].get(n), "after": cur["all_effective_library_entries"].get(n)}
            for n in sorted(keys) if prev["all_effective_library_entries"].get(n) != cur["all_effective_library_entries"].get(n)}
        prevsecs, cursecs = prev["launcher_elf_sections"], cur["launcher_elf_sections"]
        changedsecs = {n: {"before": prevsecs.get(n), "after": cursecs.get(n)}
            for n in sorted(prevsecs.keys() | cursecs.keys()) if prevsecs.get(n) != cursecs.get(n)}
        allocchanged = [n for n, v in changedsecs.items() if any(
            item and item["flags"] & 2 for item in v.values())]
        comparisons.append({"from": prev["candidate"], "to": cur["candidate"],
            "library_member_changes": changed,
            "launcher_section_changes": changedsecs,
            "launcher_allocated_section_changes": allocchanged,
            "init_diff": list(difflib.unified_diff(inits[i - 1].splitlines(), inits[i].splitlines(),
                fromfile=f"candidate{prev['candidate']}/init", tofile=f"candidate{cur['candidate']}/init", lineterm=""))})
    source_paths = [Path("/tmp/libgrm-fbinit25-289.c"), Path("/tmp/appfw/appfw-launch288.c")]
    print(json.dumps({"schema": "fx6-completed-native-runtime-review-v2", "scanner": fp(a.scanner),
        "related_source_files_not_build_bound": [fp(p) for p in source_paths if p.exists()],
        "scope": "offline completed observations only; no sockets or process control", "runs": runs, "comparisons": comparisons}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
