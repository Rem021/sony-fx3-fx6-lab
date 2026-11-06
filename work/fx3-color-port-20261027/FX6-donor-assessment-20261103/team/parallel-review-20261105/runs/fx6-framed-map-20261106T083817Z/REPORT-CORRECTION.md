# Correction addendum — framed-map run fx6-framed-map-20261106T083817Z

- New task / dispatch: `task_7ce9fcff3fe6` / `ctx_93f279790a19`
- Original task / dispatch: `task_442d30198774` / `ctx_f1fed7ed32e7`
- Generated: `2026-11-06T08:54:51.508902+00:00`
- Scope: **documentation/seal correction only**; no new VM, QMP, RSP, guest, target ELF execution, retry, deployment, or modification of the original receipt/serial.

## 1. Manifest discrepancy and appended correction

The original `SHA256SUMS` (SHA `679145f9fde899aff679873caec936585199eb5dc43f64a6651a7de2a7939aab`) lists `postrun.stdout.txt` as the empty-file SHA `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (the expected empty-file value), while the final file is `c7c7faf05134caa055f05d548aff770b7722a33fa3d711cb9e71e2e598187d5a` (1542 bytes).

Cause: `postrun.py` wrote its own SHA256SUMS while its stdout was still buffered by the outer shell pipeline `python3 ... | tee postrun.stdout.txt`. At manifest-generation time the file was still empty; after the Python process exited, the buffered postrun JSON was flushed into the file. The run had already ended; no run evidence or receipt/serial content was regenerated.

All original evidence is preserved and unchanged:

- original `SHA256SUMS`: `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/runs/fx6-framed-map-20261106T083817Z/SHA256SUMS` — SHA `679145f9fde899aff679873caec936585199eb5dc43f64a6651a7de2a7939aab`, entries 35
- original `SEAL.json`: SHA `a2bc053c124880e5e8937ab78fd530811bda07e34e76477d72fc5a3c41187a5a`
- original `run/receipt.json`: SHA `a1a2ad2fc15fcc0d005ad0eaf4d4cca53d68ce6fb8e7494394ccbbff95c556a6` (matches old SEAL)
- original `run/serial.log`: SHA `6a397851b49ce874c8acccb3b1c6d72ee6ed6ab1d10e87b43d394ed0f220571a` (matches old SEAL)
- original `REPORT.md`: SHA `eb65cf4a02d7d9eda65d7bb95173f04934165a30930ac875a2fd2674f2486833`
- original `RESULT.json`: SHA `e9fa7164bd4af33c97eb8133ce5486b5b52d32cdd9997d36888b2eb8770ee8e5`

The only original-manifest mismatch is the buffered `postrun.stdout.txt` entry: [{"path": "postrun.stdout.txt", "old_manifest_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "actual_sha256": "c7c7faf05134caa055f05d548aff770b7722a33fa3d711cb9e71e2e598187d5a", "bytes": 1542}].

A complete corrected manifest is appended as `SHA256SUMS.CORRECTED`; its self hash is in `SHA256SUMS.CORRECTED.sha256` and `SEAL-CORRECTION.json`. The old manifest, old seal, old `.sha256`, receipt and serial are not overwritten. `SEAL-CORRECTION.json` is intentionally not listed in the corrected manifest because it contains the corrected-manifest hash (avoiding a circular dependency).

## 2. Corrected write-path statement

The original report's limit text said the failure occurred "before the write path". That is inaccurate. The guest collector emitted the `FX3MS1 ERROR pid=237 starttime=1490 seq=1 reason=short_read_more_data` record through the helper's successful output path (`fail()` -> `printf`/`putchar` -> target write path). The failure was in the **read/probe decision before a complete `BEGIN`/`DATA`/`END` map frame**: the helper's single bounded read returned a short read, the one-byte EOF probe found more data, and the helper deliberately refused to emit a truncated frame. The error record itself was written and reached the host.

Correct wording: **the collector's read/probe policy aborted the map capture before any complete map frame; it did not abort before the output path.**

## 3. Corrected target-ELF entry text

The manifest-bound target ELF is SHA `9df5a10a2d22f49e5a2313bcbb0f829cefc26c51cb7e629e5f259a4808c9fed2` (122264 bytes), `ET_EXEC`, AArch64, static, no `PT_INTERP`, no `PT_DYNAMIC`. Its actual ELF entry is **`0x210ab0`**. The accepted package's earlier `REPORT.md` text said `0x210a80`; that text is stale. The bytes/hash and the CPIO member are unchanged; this correction is documentation only.

## 4. QEMU reclamation vs external worker lock occupancy

- Our authorized run: Python PID `23055`, QEMU PID `23106`, QEMU exit `0`, `qemu_reaped=true`; our PIDs are absent; receipt `lock_released=true`; during our run `lsof` showed our Python PID holding both fixed locks.
- After our run, separate worker runs were observed holding the same two fixed locks (earlier holder PIDs `24645` / QEMU `24648` with serial `.../cp-bind-0cbb3d0f/serial.log`; final recorded pass holder PIDs `26883` / QEMU `26889`). They are **not ours** and were **not touched**. Because the fixed locks were externally occupied at that pass, our own release is proven by the receipt, our absent PID, and the holder PID change—not by a free-lock probe.
- The external occupancy does not change our run's own reclamation evidence; it is recorded separately in `external-run-observation.json` and `RESULT.json`.

## 5. No new runtime

This correction task did not start QEMU, QMP, RSP or a guest, did not execute the target ELF, did not retry the consumed observation, and did not alter the fixed FX3 platform, original diagnostic package, frozen r6, or run policy. FX6 boot/menu remains **not passed**.
