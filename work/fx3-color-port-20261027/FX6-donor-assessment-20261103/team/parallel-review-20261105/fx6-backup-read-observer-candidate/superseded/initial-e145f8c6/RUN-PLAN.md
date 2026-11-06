# RUN-PLAN — AppFw two-key Backup read observer (future, not authorized now)

## Approval gate

- This directory contains **host-only code and fixtures**. No VM was started.
- Required explicit token: `APPROVE_GRMREAL46_TWO_KEYS_0214_0218`.
- Default entry is disabled: `python3 observer/run_candidate.py` prints `DISABLED` and exits 2.
- `--approved-token` only produces a plan; the host-only candidate intentionally has no QEMU-start adapter. A new run must be separately authorized and use the reviewed runner; do not treat this plan as approval.

## Exact future preflight (no VM)

```sh
python3 observer/baseline_binding.py
python3 observer/run_candidate.py --plan \
  --serial <new-run>/serial.log
python3 tests/test_host.py
```

Preconditions: baseline SHA `854e58f…`, target CPIO `3a08f89d…`, appFw `b1fe2274…`, current serial complete `FX3_AP_EARLY_MAPS` block with all `/usr/lib/appFw.so` PT_LOAD rows; no historical ASLR.

## Future one-start observation

- One Start of the existing frozen FX3 baseline; **zero keys**.
- Observation window <=150 s, total <=180 s.
- At most **2 simultaneous Z1**; initially only the two key thunk entries.
- On entry: require current ELF header/PHDR and all four pinned words; require `x0 == x29+0xb4` (key 214) or `x29+0xc4` (key 218); require `x30 == bias+0x11f67d4` / `+0x11f67f4`; capture 4B before.
- Replace that entry Z1 with the exact return Z1; on return require same TID, TLS, x29, return PC/machine word; capture w0 and 4B after; then z1 return.
- Max 4 entry/return hits, 8 stops, 16 data reads of 4 B; identity reads <=128 B-reads. If any budget/identity/TLS/read/return check fails: **unknown, stop**, no guest resume.
- Cleanup: QMP stop; `z1` every remaining address; require exact z1 OK; close RSP; stop/quit/reap only own QEMU; if residual Z1 -> keep stopped, quit own QEMU, `API16_restored=false`, no guest resume. No memory/register write, no API16 restore, no software step, no patch/stub/veneer.

## What the run would answer

- For each of `0x02cf0214` and `0x02cf0218`: entry buffer pointer and capacity 4; return `w0` signed/hex; before/after 4 B; PID/TID/TLS/x29 pairing; whether the exact callsite executed twice.

## What it cannot answer

- Which receiver/OSAL callback handles `0x3e014d`.
- Whether `92fe` Backup is the appFw source, or whether the bytes are semantically valid for FX6.
- Menu/boot success, FX3 shared-consumer safety, producer ownership, or any migration.

## Risks

- QEMU TCG hardware breakpoint behavior and current QEMU binary must be re-verified against the frozen baseline; no runtime proof this turn.
- `x0` may not be the intended buffer if the compiler/callsite differs; exact LR/slot checks make that unknown, not success.
- TLS reader may be unavailable -> unknown.
- The thunk may be shared; exact return PC check restricts to the two reviewed callsites.
- Two-key order and timing are not assumed; both are required for complete result.
