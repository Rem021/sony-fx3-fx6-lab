# RUN-PLAN — corrected AppFw two-key observer

Status: host-only; **not authorized/run**. Default entry disabled.

## Preconditions

- New specific VM/run authorization; no old authorization reuse.
- `observer/baseline_binding.py` revalidates baseline `854e…`, QEMU/kernel/DTB/CPU/memory/model-env and target CPIO `3a08…`.
- Full APP_ELF `b1fe…`; target serial for fixture `3771…`; future run serial must be new private file; never historical output.
- Current run complete `FX3_AP_EARLY_MAPS` latest block with all AppFw PT_LOADs; no fallback.
- Inherited cleanup callback for existing API16/unbind contract (source `restore_api103_v2.py`, SHA `8fb5…`) must be supplied and acknowledged. Without it, adapter reports `inherited_cleanup_required`.

## Planned one start

- One Start, zero keys, private cwd/run dir; QMP `q`, GDB `g`, 4 vCPU, fixed baseline parameters; index20 private serial; index31 target CPIO; no other argv delta.
- Observation <=150 s; total QMP/connect/cleanup <=180 s; 2 simultaneous Z1 max; 4 entry/return hits; 8 stops; 16 data reads ×4B; identity+data total <=128×4B.
- Entry: current ELF header/PHDR/4 words; T05 unique; `gdb_cpu_thread` recorded; `guest_tid` unknown; x0=frame slot, x30=exact return, TLS available; read before4.
- Return: same gdb CPU thread/TLS/x29, exact return word; read w0+after4.
- Cleanup: QMP stop; z1 all possibly-installed; residual -> QMP quit/own reap only, no guest resume; inherited cleanup required; no self API16 write.
- Any identity/budget/QMP/stop/TLS/read/timeout mismatch -> unknown and stop; no resume.

## Commands

```sh
python3 observer/baseline_binding.py
python3 observer/run_candidate.py --plan --serial <new-run>/serial.log
python3 tests/test_host.py
python3 tests/test_rsp_host.py
python3 tests/test_adapter.py
# default-disabled:
python3 observer/run_lifecycle.py            # DISABLED
python3 observer/run_lifecycle.py --approved-token APPROVE_GRMREAL46_TWO_KEYS_0214_0218
# -> READY_FOR_REVIEW only; no launch adapter is wired here and no VM is started
```

Actual QEMU execution remains unavailable until a separately reviewed runner adapter and specific VM authorization exist.

## Limits

- Cannot answer guest OS TID, receiver, Backup source, menu, FX3 consumers, or data semantics.
- No guest/memory/register writes by this observer; inherited cleanup is an external reviewed contract, not a new write.
