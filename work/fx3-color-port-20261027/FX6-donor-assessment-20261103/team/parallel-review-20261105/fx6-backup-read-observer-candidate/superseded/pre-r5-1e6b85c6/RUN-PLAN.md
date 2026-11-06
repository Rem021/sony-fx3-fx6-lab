# RUN-PLAN — r4 two-key observer

Status: **host-only, not authorized/run**. Default disabled.

## Preconditions

- New specific VM/run authorization; old token is not approval.
- Baseline `854e…`, target CPIO `3a08…`, APP `b1fe…`, five env entries, frozen QEMU/kernel/DTB/CPU/memory.
- Fresh private run root/serial; no old serial; UUID guard.
- Complete current latest AppFw map after boot; current `prelaunch, running=false` accepted, boot with one QMP cont; after-map stop/query must paused.
- Inherited API16 restore contract on 3a08 is **not established**; full clean remains blocked unless separately approved. Stop-only mode is separate and does not claim guest restore.

## One-start sequence

1. QMP greeting + capabilities; query prelaunch/running=false.
2. One QMP cont boot; wait current serial maps.
3. QMP stop + query paused; arm two thunk Z1 (possibly set before send).
4. RSP addressless c; four stops (214 entry/return, 218 entry/return); c after every non-final stop; actual Observer identity/reads/TLS/capture.
5. Completion: stop/query; z1 all possibly; close RSP; full mode inherited only if contract/cancellable callback passes; QMP quit; bounded wait/reap; exit code; locks; receipt.
6. Stop-only mode: no inherited/no guest control; report `two_keys_observed` and `host_cleanup_complete` separately; `guest_restore_status=unknown_not_attempted`, `boot_menu_passed=false`.

Budgets: one start, zero keys, <=150s observation/<=180s total, 2 Z1, 4 hit/8 stop/16 data reads, identity+data <=128×4B; no Z0/software-step/writes.

## Commands

```sh
python3 observer/baseline_binding.py
python3 observer/run_candidate.py --plan --serial <current>/serial.log
python3 tests/test_host.py
python3 tests/test_rsp_host.py
python3 tests/test_runner.py
python3 tests/test_stateful_transport.py
python3 tests/test_e2e_stateful.py
python3 observer/run_lifecycle.py            # DISABLED
python3 observer/run_stop_only.py            # DISABLED
```

No actual QEMU launch in this preparation; separate approval required.
