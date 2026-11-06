"""Full ordinary-user helper/IPC integration for post-STOP 054C:096F transition compatibility."""
from pathlib import Path
from hashlib import sha256
import json, struct, subprocess, sys
sys.dont_write_bytecode = True
import supervisor as S
import receipt_receiver as R
import flow_receiver as F
import fixed_launch as P

H = Path(__file__).resolve().parent
assert not P.JOB.exists()

# 1. Build and run C transition_unit test
t_out = H / "artifacts/transition-unit"
t_argv = [
    "/usr/bin/xcrun", "clang", "-std=c11", "-O1", "-g", "-Wall", "-Wextra", "-Werror",
    "-Wno-deprecated-declarations", "-fsanitize=address,undefined", "-fno-sanitize-recover=all",
    "-I", str(H), str(H / "transition_identity.c"), str(H / "transition_unit.c"), "-o", str(t_out),
]
tp = subprocess.run(t_argv, capture_output=True, text=True, check=True)
tr = subprocess.run([str(t_out)], capture_output=True, text=True, check=True)
assert "096F return-window BUSY and original return serial" in tr.stdout, tr.stdout

rows = [{
    "case": "c-transition-unit-096f-and-bounds",
    "status": "PASS",
    "stdout": tr.stdout.strip(),
    "sha256": sha256(t_out.read_bytes()).hexdigest(),
}]

# 2. Case A: Transient 054C:096F (2 samples BUSY) -> 054C:0DA1 (OK) -> COMPLETE
name = "post-stop-096f-transient-complete"
d = H / "runs" / (name + "-seed")
d.mkdir(mode=0o700, parents=True)
guard = d / "old.journal"
spec = d / "recovery.bin"
seed = subprocess.Popen(
    [str(H / "artifacts/recovery-seed"), str(guard), str(spec), "0"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
)
assert seed.stdout.readline() == "ready\n"
seed.stdin.write("x")
seed.stdin.flush()
assert seed.wait(timeout=3) == 0
before = guard.read_bytes()

opt_transient = (1 << 23) | 67108864
j = S.Job.fixture(name=name, fixture_option=opt_transient, guard=guard, recovery_spec=spec)
try:
    res = j.wait(5)
    assert res["status"] == "HOST_RETURN_CONTROLLED_PORT_ASSOCIATION", res
    assert res["bounded_service_read_observed"] is True
    assert j.receipt["phase"] == "COMPLETE" and j.receipt["native_return"] == 0
    assert j.receipt["global_guard_result"] == 0 and j.receipt["manual_recovery"]["stage"] == 2
    assert j.flow_state.complete is True and j.flow_state.body_bytes == 88
    assert j.flow_state.return_node == 300
    op63_rows = [r for r in j.flow_state.rows if r["op"] == 63 and r["point"] == 2]
    assert len(op63_rows) == 3, op63_rows
    assert [r["status"] for r in op63_rows] == [2, 2, 0], op63_rows
    # Verify raw frames for the two 096F samples have pid=0x096f and registry=250
    op63_indices = [i for i, r in enumerate(j.flow_state.rows) if r["op"] == 63 and r["point"] == 2]
    for idx in op63_indices[:2]:
        reg, loc, prod = struct.unpack_from("<QII", j.flow_frames[idx], 160)
        assert reg == 250 and (prod & 0xFFFF) == 0x054C and (prod >> 16) == 0x096F
    reg3, loc3, prod3 = struct.unpack_from("<QII", j.flow_frames[op63_indices[2]], 160)
    assert reg3 == 300 and (prod3 & 0xFFFF) == 0x054C and (prod3 >> 16) == 0x0DA1
    assert len(guard.read_bytes()) == 4 * 256 and guard.read_bytes()[:len(before)] == before
    saved_complete = (list(j.flow_frames), j.verified.identity, bytes(j.frame.nonce), op63_indices[0])
    rows.append({
        "case": name,
        "status": "PASS",
        "frames": len(j.flow_frames),
        "op63_statuses": [r["status"] for r in op63_rows],
        "return_node": j.flow_state.return_node,
        "complete": True,
    })
finally:
    j.close_observer()

# 3. Case B: Wrong-serial 054C:096F rejected with FX3T_DENIED -> HELD
name_bad = "post-stop-096f-wrong-serial-held"
d_bad = H / "runs" / (name_bad + "-seed")
d_bad.mkdir(mode=0o700, parents=True)
guard_bad = d_bad / "old.journal"
spec_bad = d_bad / "recovery.bin"
seed = subprocess.Popen(
    [str(H / "artifacts/recovery-seed"), str(guard_bad), str(spec_bad), "0"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
)
assert seed.stdout.readline() == "ready\n"
seed.stdin.write("x")
seed.stdin.flush()
assert seed.wait(timeout=3) == 0
opt_bad_serial = (1 << 23) | (1 << 29) | 67108864
j = S.Job.fixture(name=name_bad, fixture_option=opt_bad_serial, guard=guard_bad, recovery_spec=spec_bad)
try:
    res = j.wait(5)
    assert res["status"] == "OWNER_RETAINED", res
    assert j.receipt["phase"] == "HELD" and j.receipt["native_return"] == 4
    op63_rows = [r for r in j.flow_state.rows if r["op"] == 63 and r["point"] == 2]
    assert len(op63_rows) == 1 and op63_rows[0]["status"] == 1, op63_rows
    rows.append({
        "case": name_bad,
        "status": "PASS",
        "frames": len(j.flow_frames),
        "op63_statuses": [r["status"] for r in op63_rows],
        "held": True,
    })
finally:
    j.frame.fixture_gate(2)
    assert j.runner.wait(timeout=5) == 90
    j.close_observer()

# 4. Case C: Persistent 054C:096F across all 50 samples -> HELD after 50 BUSY samples
name_pers = "post-stop-096f-persistent-menu-held"
d_pers = H / "runs" / (name_pers + "-seed")
d_pers.mkdir(mode=0o700, parents=True)
guard_pers = d_pers / "old.journal"
spec_pers = d_pers / "recovery.bin"
seed = subprocess.Popen(
    [str(H / "artifacts/recovery-seed"), str(guard_pers), str(spec_pers), "0"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
)
assert seed.stdout.readline() == "ready\n"
seed.stdin.write("x")
seed.stdin.flush()
assert seed.wait(timeout=3) == 0
opt_pers = (1 << 31) | 67108864
j = S.Job.fixture(name=name_pers, fixture_option=opt_pers, guard=guard_pers, recovery_spec=spec_pers)
try:
    res = j.wait(5)
    assert res["status"] == "OWNER_RETAINED", res
    assert j.receipt["phase"] == "HELD" and j.receipt["native_return"] == 4
    op63_rows = [r for r in j.flow_state.rows if r["op"] == 63 and r["point"] == 2]
    assert len(op63_rows) == 50 and all(r["status"] == 2 for r in op63_rows), len(op63_rows)
    rows.append({
        "case": name_pers,
        "status": "PASS",
        "frames": len(j.flow_frames),
        "op63_busy_samples": len(op63_rows),
        "held": True,
    })
finally:
    j.frame.fixture_gate(2)
    assert j.runner.wait(timeout=5) == 90
    j.close_observer()

# 5. Direct FlowReceiver forgery checks on saved 054C:096F frame
frames, identity, nonce, idx096f = saved_complete
for label, patch in [
    ("096f-status-ok-rejected", lambda b: struct.pack_into("<I", b, 28, 0)),
    ("096f-kind-controlled-port-rejected", lambda b: struct.pack_into("<I", b, 464, 2)),
    ("096f-wrong-serial-tag-rejected", lambda b: b.__setitem__(slice(176, 208), b"Z" * 32)),
    ("096f-wrong-location-rejected", lambda b: struct.pack_into("<I", b, 168, 0x02200000)),
    ("096f-reused-source-node-rejected", lambda b: struct.pack_into("<Q", b, 160, 100)),
    ("096f-reused-service-node-rejected", lambda b: struct.pack_into("<Q", b, 160, 200)),
]:
    receiver = F.FlowReceiver(identity, nonce, R.GRANT_ID)
    for fr in frames[:idx096f]:
        receiver.accept(fr)
    bad = bytearray(frames[idx096f])
    patch(bad)
    bad[640:] = sha256(bad[:640]).digest()
    try:
        receiver.accept(bytes(bad))
    except R.Rejected:
        pass
    else:
        raise AssertionError(label + " accepted")

rows.append({
    "case": "saved-frame-096f-forgeries-denied",
    "status": "PASS",
    "variants": 6,
})

out_receipt = {
    "status": "POST_STOP_096F_TRANSITION_COMPATIBILITY_PASS",
    "checks": len(rows),
    "rows": rows,
    "native_helper_executed": False,
    "actual_root_journal_modified": False,
    "new_root_or_USB_operations": 0,
}
with (H / "post-stop-096f-check.json").open("x", encoding="utf-8") as f:
    json.dump(out_receipt, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(json.dumps({"status": out_receipt["status"], "checks": len(rows)}))
