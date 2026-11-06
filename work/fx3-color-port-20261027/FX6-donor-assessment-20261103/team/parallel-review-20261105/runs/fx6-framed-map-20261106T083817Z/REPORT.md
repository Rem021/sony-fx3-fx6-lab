# FX6 framed-map observation — one authorized start

- Task: `task_442d30198774`
- Dispatch: `ctx_f1fed7ed32e7`
- Authorization: `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/fx6-framed-map-approval-20261106T083425Z.json` (SHA `f5c7bb754544a6093178d43b4e8632ea5e85c08e6fb5e0c9e726801104b01589`), new framed-map allowance, **not** the old r6 allowance
- Plan: `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/fx6-framed-map-observation-run-plan.json` (SHA `3e23cf6c2021592333af96a717f34b019d15bd8115e17911d7b8eb68f96912b8`)
- Status: **ONE_START_USED; OBSERVATION FAILED (collector short-read error); HOST CLEANUP OK; GUEST RESTORE UNKNOWN; NOT BOOT/MENU PASS**
- Run root: `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/runs/fx6-framed-map-20261106T083817Z/run`

## Authorization and allowance

- Token used: `APPROVE_FX6_FRAMED_MAP_OBSERVER_20261106` with `--new-run-approval` and a fresh private run root.
- `starts_max=1`, `keys_max=0`, observation max 150 s, launch-to-cleanup max 180 s, FX3 platform fixed, no deploy, no automatic retry.
- `starts_used=1` in `launch-allowance.json` / `approval-consumption.json`.
- The team approval JSON is left exactly as issued (`starts_used=0`, pending); its original bytes are preserved at `authorization.json`. Consumption is recorded separately so the coordinator can update its own ledger.

## Start, PID and time

- Python/entry PID: **23055**; QEMU PID: **23106** (QEMU ppid `23055`).
- CLI start: `2026-11-06T08:40:15.988197+00:00`; end: `2026-11-06T08:40:53.073802+00:00`; CLI wall: **37.086 s**; CLI exit **1**.
- QEMU first/last seen: `2026-11-06T08:40:19.346415+00:00` / `2026-11-06T08:40:52.142328+00:00`; visible upper bound **32.796 s**.
- Within the 150 s observation and 180 s launch-to-cleanup limits (conservative CLI wall bound). One start only; zero keys; no second start.

## Actual result

`cli.stdout` status: **FAILED**.

Native receipt `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/runs/fx6-framed-map-20261106T083817Z/run/receipt.json` (SHA `a1a2ad2fc15fcc0d005ad0eaf4d4cca53d68ce6fb8e7494394ccbbff95c556a6`):

- `status=error`
- `error=ProtocolError('collector ERROR: FX3MS1 ERROR pid=237 starttime=1490 seq=1 reason=short_read_more_data')`
- `records=[]`, `two_keys_observed=false`
- `host_cleanup_complete=true`, `clean=false` (stop-only)
- `qemu_exit=0`, `qemu_reaped=true`, `lock_released=true`
- `breakpoints.all_removed=true`, `residual=[]`
- `inherited=not_attempted_stop_only`
- `guest_restore_status=unknown_not_attempted`, `boot_menu_passed=false`
- `input_unchanged_after=true`; target CPIO/appFw postflight hashes match; `verification_failed=false`

## Framed-map completeness / ELF identity

The guest **did execute the diagnostic helper**, but the only framed record is a complete, newline-terminated error:

```
FX3MS1 ERROR pid=237 starttime=1490 seq=1 reason=short_read_more_data
```

- PID/starttime/seq: `237` / `1490` / `1`; reason `short_read_more_data`; serial LF line 12761, byte offset 2022599.
- `FX3MS1 BEGIN=0`, `DATA=0`, `END=0`, `ERROR=1`; **no maps payload**.
- Strict decoder/provider result: `REJECTED` / `REJECTED` with `collector ERROR: FX3MS1 ERROR pid=237 starttime=1490 seq=1 reason=short_read_more_data`. The explicit collector error is rejected immediately; there is no legacy raw-map fallback.
- Therefore no appFw map was selected, no ELF header/PHDR/code identity check was reached, no breakpoint was armed, and no two-key entry/return stop occurred. **Framed maps完整性 and appFw ELF identity are NOT observed.**
- Source semantics: `fx3_map_snapshot.c` performs one bounded read of up to 262144 bytes, then a one-byte EOF probe. If the probe finds more data after a short read, it emits `FX3MS1 ERROR ... reason=short_read_more_data` and deliberately does not emit a truncated frame. This run hit that path.

The target helper static identity is bound by the manifest: `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-map-observer-integration-candidate/work/fx3-map-snapshot-aarch64` SHA `9df5a10a2d22f49e5a2313bcbb0f829cefc26c51cb7e629e5f259a4808c9fed2`, 122264 bytes, ET_EXEC/AArch64, no PT_INTERP/PT_DYNAMIC; the CPIO member matched it. Its entry is `0x210ab0`; the accepted REPORT text says `0x210a80` (stale text; hashes/CPIO member match).

## Two-key result

No two-key result exists. The mapping wait failed before `QMP stop`/RSP arm; the receipt has `records=[]`. This is the precise failure, not a timeout and not a partial-frame wait.

## Independent serial fault scan

Using the accepted `detect_serial_faults.py`:

- status `asserts_detected`; exit 1 (asserts present); `line_terminated=True`, `capture_complete=None`
- **2 assert(s)**: `model_api.cpp:3147`, `model_api.cpp:3176`; **0 kernel fault markers**
- screen markers `{'FX3_AP89_SCREEN_CREATE': 0, 'FX3_AP89_UUD_DECISION': 0, 'FX3_MENU': 0}`
- This does not prove boot/menu or a functional run.

## Inputs, argv, locks

- Volume UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B` (expected `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`).
- Candidate manifest self `59d83b282ce5e614377d7655176c16eddba4e900f841426c3891de89a5c9317e` / 59 items; unchanged after run.
- Frozen r6 manifest self `85d6097c8b13c7d9820630bf29835745ce0d55a64e4f7de28aa751b5079b9d49` / 337 items; unchanged.
- New CPIO `9d4f255b0a3995b0e056e210ae4d27c8129e2c853b35904a688b6ffe149529ae` / 453306948 bytes; target helper `9df5a10a2d22f49e5a2313bcbb0f829cefc26c51cb7e629e5f259a4808c9fed2`; appFw `b1fe2274e19d50b6d7ee12886dc233a742358772383f5cf79523de15cf0b55be`; baseline `854e58f0485537e4644f81daa51d532eea5fa1f5e30887c684e9356e542b9669`; QEMU `bf4d46481998b8fb0644da3e17a333d5fc8a7b6aeb0035f1b4e03aa25c98c70d`; kernel `da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c`; DTB `b6f9f4c04d0da101565d67244629a0ad7a3954c8af004f353c16ae0c8b499de7`; old 3a08 CPIO `3a08f89d89cfc6db8b12158a0a1147410e42d98713c445c3c38c07eefad8d03b`; all unchanged before/after.
- Independent `baseline_binding.verify_artifacts()`: `True`.
- 34-argv command; difference from frozen baseline only indexes **[20, 31]** (private serial index 20, new CPIO index 31). Model env exactly five keys.
- After our run the locks were observed held by external PID(s) 26883 / QEMU 26889; that run was not touched. Our receipt lock_released=true and our PID is absent, so our own release is independently True.

## Cleanup

- Owned QEMU 23106 exited 0 and was reaped (`qemu_reaped=true`); our PIDs 23055/23106 are absent now (`own_processes_absent=True`); receipt `lock_released=true`; during our run `lsof` showed our Python PID 23055 holding both locks.
- At this postrun pass a different run holds both fixed locks: holder PIDs 26883, QEMU 26889, serial /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic/runs/cp-bind-3855152a/serial.log. It is not ours and was not touched. Our own lock release is separately True (receipt true, our PID absent, no holder equals our PID); external-run-observation.json preserves the earlier pass too.
- Run-dir sockets `q`/`g` absent; breakpoints `residual=[]`; observer never armed.
- Guest restore not attempted: `guest_restore_status=unknown_not_attempted`; `boot_menu_passed=false`.
- No deployment; no second start; no retry; no interference with the external run.

## Evidence

- `run/receipt.json`, `run/command.json`, `run/serial.log` (SHA `6a397851b49ce874c8acccb3b1c6d72ee6ed6ab1d10e87b43d394ed0f220571a`, 2026572 bytes, newline-terminated)
- `preflight.json`, `timing.json`, `runtime-pids.json`, `ps-first.txt`, `ps-final.txt`, `frame-analysis.json`, `serial-faults.json`, `postrun.json` (generated with this report), `RESULT.json`, `SHA256SUMS`, `SEAL.json`
- `authorization.json` (original approval copy), `authorization-context.json`, `launch-allowance.json`, `approval-consumption.json`

## Limits / left to do

- The observation produced **no framed map** and **no two-key values**; the diagnostic package needs a collector fix (bounded read/cap protocol) and a new candidate/new authorization before another observation. Do not retry this consumed allowance.
- Actual TLS/Sysregs two-key read path was not exercised; no boot/menu/functional pass is claimed. The earlier host fake E2E used a fixture TLS reader, so it cannot be cited as actual Sysregs verification.
- `target_io` write retries have no independent write deadline and rely on the existing HostRunner lifecycle; this failure occurred before the write path, and cleanup needed no action beyond the owned QEMU 23106 (exit 0, reaped).
- Guest restore remains unknown; host cleanup only.
