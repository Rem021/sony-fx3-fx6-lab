# RUN-PLAN — corrected two-key host observer

Status: **not authorized/run**. Default entry disabled.

## Preconditions

- New VM/run authorization; old token not approval.
- Re-run `observer/baseline_binding.py`; baseline `854e…`, target CPIO `3a08…`, APP `b1fe…`, env five, all frozen artifacts.
- Fresh private run root/serial; current complete latest AppFw map; no historical ASLR/old serial.
- Inherited API16/unbind contract must be separately established and approved; current 3a08 audit is **not established**, so a real run cannot claim clean.
- RSP strict checksum/T05; QMP `stop`+`query-status` paused; max 2 Z1; 4 entry/return hits, 8 stops, 16 data reads ×4B; identity+data 128×4B; 150s observe/180s total.

## One-start future path

1. QMP greeting + `qmp_capabilities`; confirm `-S` prelaunch paused.
2. QMP `cont` to allow original boot; wait current serial complete maps.
3. QMP stop + query paused; arm two AppFw thunk Z1; possibly_installed before each send.
4. RSP addressless `c` to start observation; every entry/return stop resumes with another `c`; identity at first entry; capture/budget/deadline.
5. On completion/timeout/error: QMP stop+query; if paused z1 all possibly; if stop unconfirmed do not touch breakpoints; quit before wait/reap; only own child terminate/kill; locks only if child reaped; inherited only if target protocol established/callback cancellable and contract passes.
6. No guest writes by observer itself; any inherited control is separate and unestablished.

## Commands

```sh
python3 observer/baseline_binding.py
python3 observer/run_candidate.py --plan --serial <current>/serial.log
python3 tests/test_host.py
python3 tests/test_rsp_host.py
python3 tests/test_adapter.py
python3 tests/test_runner.py
python3 observer/run_lifecycle.py   # DISABLED
```

No QEMU launch in this preparation. Actual run requires reviewed dependencies and separate authorization.
