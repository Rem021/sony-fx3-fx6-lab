#!/usr/bin/env python3
"""Read completed FX6 observations; never connects to QEMU or executes trial code."""
import argparse
import ast
import hashlib
import json
import mmap
import re
from pathlib import Path

SELECTED = {
    "init", "usr/lib/appFw.so", "usr/lib/libgrm-fbinit9.so",
    "usr/lib/libuxengine.so", "usr/lib/libgrm.so", "usr/bin/appfw-launch",
}
RELEVANT = re.compile(
    r"APPFW_|FX6_APP|FX6_OSAL_|SEGV \(PC=|Assertion|assert at|"
    r"stub dlsym failed|sys_panic|Kernel panic|Internal error:|"
    r"FX6_OSD_FLUSH|FX6_GPE_|FX3_KEY\d+_STEP_DONE"
)


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fingerprint(path):
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha(path)}


def cpio_members(path):
    """Parse the first newc archive only. Appended members are outside this scan."""
    found = {}
    with path.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as m:
        off = 0
        while True:
            if m[off:off + 6] not in (b"070701", b"070702"):
                raise ValueError(f"invalid newc header at {off}")
            fields = [int(m[off + 6 + 8*i:off + 14 + 8*i], 16) for i in range(13)]
            size, ns = fields[6], fields[11]
            if ns < 1 or off + 110 + ns > len(m):
                raise ValueError("invalid newc filename")
            name = m[off + 110:off + 110 + ns - 1].decode()
            start = (off + 110 + ns + 3) & ~3
            if start + size > len(m):
                raise ValueError("truncated newc payload")
            normalized = name.removeprefix("./")
            if normalized in SELECTED or normalized.startswith("usr/lib/libosal_"):
                view = memoryview(m)[start:start + size]
                found[normalized] = {"bytes": size, "sha256": hashlib.sha256(view).hexdigest()}
                del view
            off = (start + size + 3) & ~3
            if name == "TRAILER!!!":
                break
    return found


def run_summary(root, number):
    manifest = root / f"vm-candidate-gpecap25-{number}.json"
    manifest_hash = sha(manifest)
    md = json.loads(manifest.read_text())
    receipts = []
    for receipt in (root / "runs").glob("*/run-receipt.json"):
        rd = json.loads(receipt.read_text())
        if rd.get("manifest_sha256") == manifest_hash:
            receipts.append((receipt, rd))
    completed = [(p, d) for p, d in receipts if d.get("process_reaped") is True
                 and d.get("locks_released") is True]
    if not completed:
        return {"candidate": number, "status": "no_completed_receipt", "manifest": fingerprint(manifest)}
    receipt, rd = max(completed, key=lambda x: x[0].stat().st_mtime_ns)
    run = receipt.parent
    cpio = Path(md["initrd"]["path"])
    watched = [receipt, run / "serial.log", run / "command.json", manifest, cpio]
    before = [(p.stat().st_mtime_ns, p.stat().st_size) for p in watched]
    serial = (run / "serial.log").read_text(errors="replace")
    lines = serial.splitlines()
    interesting = [{"line": i + 1, "text": l[:600]} for i, l in enumerate(lines) if RELEVANT.search(l)]
    actual_cpio = fingerprint(cpio)
    cmd = json.loads((run / "command.json").read_text())
    argv = cmd.get("argv", [])
    loader = [a for a in argv if isinstance(a, str) and a.startswith("loader,file=") and ".cpio," in a]
    captures = []
    for f in sorted(run.glob("gpe*.bin")):
        raw = f.read_bytes()
        captures.append({**fingerprint(f), "nonzero_bytes": sum(b != 0 for b in raw)})
    members = cpio_members(cpio)
    fault_markers = rd.get("serial_observation", {}).get("fault_markers")
    result = {
        "candidate": number, "run": run.name,
        "completed_definition": "process_reaped=true AND locks_released=true in receipt",
        "manifest": fingerprint(manifest), "receipt": fingerprint(receipt),
        "manifest_sha_matches_receipt": manifest_hash == rd.get("manifest_sha256"),
        "cpio": actual_cpio,
        "cpio_sha_matches_manifest": actual_cpio["sha256"] == md["initrd"].get("sha256"),
        "cpio_size_matches_manifest": actual_cpio["bytes"] == md["initrd"].get("bytes"),
        "command_cpio_loader": loader,
        "command_loader_matches_cpio": any(f"loader,file={cpio}," in s for s in loader),
        "cpio_members": members,
        "cpio_member_scan_scope": "first newc archive, ends at its first TRAILER!!!; appended archives/members and effective guest override order are not analyzed",
        "recorded_grm_fbinit_metadata": md.get("grm_fbinit"),
        "recorded_grm_fbinit_sha_matches_member": md.get("grm_fbinit", {}).get("sha256") == members.get("usr/lib/libgrm-fbinit9.so", {}).get("sha256"),
        "run_reason": rd.get("reason"), "elapsed_seconds": rd.get("elapsed_seconds"),
        "qemu_exit": rd.get("qemu_exit"), "receipt_fault_markers": fault_markers,
        "receipt_empty_faults_while_serial_has_segv": fault_markers == [] and "SEGV (PC=" in serial,
        "serial": fingerprint(run / "serial.log"),
        "serial_sha_matches_receipt": sha(run / "serial.log") == rd.get("logs", {}).get("serial.log", {}).get("sha256"),
        "observed_lines": interesting,
        "segv_monitor_count": len(re.findall(r"SEGV \(PC=", serial)),
        "explicit_appfw_segv_count": serial.count("APPFW_SEGV"),
        "appfw_dlsym_failure_count": len(re.findall(r"appfw-launch: stub dlsym failed", serial)),
        "captures": captures,
        "native_ui_pass": False,
        "native_ui_verdict_basis": "No bound native screen/model/frame and key confirmation evidence; zero or nonzero pixels alone cannot prove an original menu.",
    }
    keyerr = run / "keyinject-error.txt"
    if keyerr.exists():
        result["keyinject_error"] = keyerr.read_text()
    result["source_files_unchanged_during_read"] = before == [
        (p.stat().st_mtime_ns, p.stat().st_size) for p in watched]
    return result


def frontend_summary(path):
    before = (path.stat().st_mtime_ns, path.stat().st_size)
    raw = path.read_bytes()
    src = raw.decode()
    tree = ast.parse(src)
    methods = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods[node.name] = {
                "line": node.lineno, "end_line": node.end_lineno,
                "calls": sorted({ast.unparse(c.func) for c in ast.walk(node) if isinstance(c, ast.Call)}),
            }
    assignments = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(ast.unparse(t) == "self._current_png" for t in node.targets):
            assignments.append({"line": node.lineno, "value": ast.unparse(node.value)})
    return {
        "source": {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()},
        "source_unchanged_during_read": before == (path.stat().st_mtime_ns, path.stat().st_size),
        "methods": {k: methods.get(k) for k in (
            "render_current_screen_png", "get_png", "do_GET", "set_page", "apply_key",
            "select_box_or_param", "start_live_vm", "_vm_worker", "write_mailbox_and_key")},
        "frame_assignments": sorted(assignments, key=lambda x: x["line"]),
        "frame_origin": "host Python renderer in this source revision",
        "guest_model_confirmation": "not implemented in the audited source paths",
        "guest_memory_operations_in_mailbox_method": [l.strip() for l in src.splitlines()
            if 'self.packet(f"M' in l or 'self.packet("Qqemu.PhyMemMode' in l],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--frontend", type=Path, required=True)
    p.add_argument("--candidates", type=int, nargs="+", default=[273, 280, 283, 286])
    args = p.parse_args()
    result = {"schema": "fx6-readonly-evidence-review-v1", "runs": [run_summary(args.root, n) for n in args.candidates],
              "frontend": frontend_summary(args.frontend),
              "limitations": ["No QEMU, GDB, sockets or cameras controlled.",
                  "Member fingerprints cover the first newc archive only. Bytes after its first TRAILER!!! are included in whole-CPIO SHA, but are not parsed; appended duplicates may affect effective guest files. Use the coordinator's inspect_cpio_binding.py for the full container/appendix audit.",
                  "Current on-disk manifests and CPIO members are rehashed; a completed receipt's matching manifest hash binds the recorded paths, but does not independently prove the historical loader verified payload bytes.",
                  "Only selected completed runs reviewed; absence of a marker is not a proof of absent execution."]}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
