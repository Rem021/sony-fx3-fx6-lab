# FX6 map collector short-read candidate — offline design

- Task: `task_7ce9fcff3fe6`
- Dispatch: `ctx_93f279790a19`
- Status: **OFFLINE_COLLECTOR_CANDIDATE_BUILT; ADMISSION BLOCKED; NOT RUN; NOT DEPLOYED**
- No VM, QEMU, real QMP/RSP, guest, target ELF execution, installation, deployment, or new observation in this task.
- FX6 boot/menu remains **not passed**.

## 1. Previous run seal correction (completed first)

The completed one-start run `fx6-framed-map-20261106T083817Z` is preserved unchanged. Its original `SHA256SUMS` (SHA `679145f9fde899aff679873caec936585199eb5dc43f64a6651a7de2a7939aab`) listed `postrun.stdout.txt` as the empty-file SHA `e3b0c442...`; the actual flushed file is `c7c7faf05134caa055f05d548aff770b7722a33fa3d711cb9e71e2e598187d5a` (1,542 bytes). Cause: `postrun.py` generated its manifest while its stdout was still buffered by the outer `tee`; the JSON was flushed after process exit. The run had already ended.

- Original `SHA256SUMS`, `SEAL.json`, receipt and serial are unchanged.
- Appended correction: `SHA256SUMS.CORRECTED` SHA `d875de596338fb9c34e93ef1cec8380e8c4ebd409578c4482740bf1ca4cb74d8` (40 entries), `SHA256SUMS.CORRECTED.sha256`, `SEAL-CORRECTION.json`, `REPORT-CORRECTION.md`.
- Corrected write-path statement: the `FX3MS1 ERROR` record was written through the helper's output path. The failure was in the **read/probe decision before a complete map frame**, not before the write path.
- Corrected ELF entry: the manifest-bound helper's actual entry is `0x210ab0`; the old accepted report text `0x210a80` is stale. The ELF/CPIO hashes are unchanged.
- QEMU/locks: our QEMU 23106 exited 0/reaped; our PIDs 23055/23106 are absent; receipt `lock_released=true`. Separate worker runs later held the same fixed locks (earlier 24645/24648; final recorded 26883/26889); they were not ours and were not touched. Our own release is evidenced by the receipt, our absent PID, and the holder PID change; a free-lock probe was unavailable while the external run held them.

Correction files live in the old run directory; the original manifest/SEAL are not overwritten.

## 2. Root cause: short read, not cap exhaustion

- Fixed kernel: `vmlinux.bin` SHA `da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c`, embedded `Linux version 4.9.337-scel+`.
- Failed run serial: SHA `6a397851b49ce874c8acccb3b1c6d72ee6ed6ab1d10e87b43d394ed0f220571a`; the only framed line is `FX3MS1 ERROR pid=237 starttime=1490 seq=1 reason=short_read_more_data`.
- In the frozen helper, `short_read_more_data` is the branch where the first read returned `< cap` and the one-byte EOF probe returned more data. `cap_exceeded` is a separate branch. The failure is therefore **not** cap exhaustion.
- Measured r6 full maps blocks (same guest application, earlier accepted run, SHA `bf5b667b...`): 281/352/411/428 rows, 28,805/35,914/41,791/43,509 row bytes; max **43,509 bytes**, far below 262,144. This is supporting evidence only, not a substitute for the failed run's missing snapshot.
- The task-supplied official reference `https://www.kernel.org/doc/html/v5.7/filesystems/proc.html` could not be fetched here (DNS returned a non-public address); no quote is fabricated. The candidate treats maps as a live `seq_file` view and does not claim atomicity.
- The cap is **unchanged** at 262,144 bytes. The fix is the state machine, not a blind expansion.

## 3. New collector: FX3MS2

`target/fx3_map_snapshot_v2.c` + `target/collector_core.{c,h}`:

- reads `/proc/<pid>/maps` repeatedly until `read()` returns 0 (EOF);
- explicit bounds: cap 262,144 bytes, max 64 data reads, 1,000 ms, 64 KiB per read, 8 EINTR/read and 32 total;
- opens one `/proc/<pid>` directory and the `stat`/`maps` entries through it; reads pid/starttime before and after; requires the same pid/starttime and same requested pid;
- requires the payload to be non-empty and end in newline;
- emits `FX3MS2 BEGIN`/`DATA`/`END` only after a complete capture; failures emit a complete `FX3MS2 ERROR` line with a precise reason;
- `END` carries bytes/lines/FNV digest, read/eintr/attempt counts, identity before/after, `snapshot_atomic=0`, `eof_observed=1`, and zero cap/read/time-limit flags;
- no libc, no malloc, no printf; raw Linux syscalls and a freestanding static ELF;
- no `SIGSTOP`, `ptrace`, `process_vm_*`, or guest-application modification.

## 4. Host provider and stream frontier

`host/fx3ms2.py`:

- strict state machine; rejects legacy `FX3MS1` frames explicitly and never falls back to raw maps;
- ignores non-`FX3MS2` console noise only when it does not start with the protocol prefix;
- validates exact fields, sequence, pid/starttime, base64 chunks, index order, byte/line count, digest, identity, EOF, `snapshot_atomic=0`, flags, and read-attempt accounting (`read_count + eintr_count + 1`);
- a complete malformed frame or collector ERROR is rejected immediately; a complete frame with no appFw rows is retryable (wait for a later increasing sequence), never a fallback to an older frame;
- the wait loop holds a non-empty unterminated tail and does not accept an older frame while the tail is present.

## 5. Post-pause identity gate (before arming)

`host/live_runner_v2.py` wraps the frozen r6 HostRunner's RSP factory. After QMP `stop` and before the Observer is constructed/armed, it reads back through the real RSP:

1. full 64-byte appFw ELF header;
2. full PHDR table;
3. all four thunk/return machine words;

and compares them with the pinned `appFw-future-skip.so` (`b1fe2274...`). A mismatch closes RSP and raises; no `Z1` is sent. The E2E corrupts the first header word and asserts that no `Z1` appears and no pre-arm identity record is written.

This proves the gate ordering and the paused-state byte/address identity. It does **not** prove the multi-read map was atomic or that code pages are currently executable; see the admission blocker.

## 6. Tests (offline; host only)

- Collector production state machine: **19/19 PASS**, including the actual 10,563-byte accepted maps payload split at 1024-byte boundaries with 8 sustained EINTR; shortread+moredata, arbitrary line splits, EOF, EINTR limits, cap/read/time exhaustion, PID/starttime change, read error, empty/unterminated payload, open/stat failures.
- Host FX3MS2 parser/wait: **16/16 PASS**, including valid accept, legacy rejection, partial chunk frontier, complete corrupt rejection, collector-ERROR rejection, no-appFw retry, later-seq selection, duplicate sequence, valid-then-corrupt no-fallback, partial tail, flags/digest/mapping-range rejection.
- Entry gates: **2/2 PASS** (default-disabled, wrong token, missing approval, fake success/failure).
- Actual frozen r6 HostRunner/Observer/QMP/RSP four-stop E2E: **2/2 PASS** (success + pre-arm identity failure aborts before `Z1`). Uses socketpair fake QMP/RSP, fake launcher/locks/clock, and a **fixture TLS reader**; it is not target runtime.
- No target ELF execution and no VM.

## 7. Target ELF and CPIO

- Target ELF: `work/fx3-map-snapshot-v2-aarch64`, **15,800 bytes**, SHA `1286759f2662e0af43f054cce72b700b24588bdd96532a6ff5a910b4af341eb9`, `ET_EXEC` AArch64, static, no `PT_INTERP`/`PT_DYNAMIC`, entry `0x2108e4`, 3 `PT_LOAD`, GNU_STACK RW. Built with existing host clang 21 / LLD 23.1.1, freestanding; never executed.
- New CPIO: `work/fx6-map-collector-shortread-grmreal46.cpio`, SHA `79a87f32059cd3fa7bd2b1fa6484559ce5b2b2cacdad1dba6c456e13a64cf92d`, **453,200,484 bytes**, 1,158 members.
- From frozen 3a08 CPIO: 1,156 other members header+content unchanged; only `init` and the new helper differ; zero tail 25,746,348 bytes preserved; actual reparse true.
- From the previous accepted candidate CPIO: only `simulation/fx3-map-snapshot` changes (`init` header/data identical).
- `init` is the same reviewed 21,239-byte call-site patch (`6c0c8dd7...`).
- CPIO is not installed, deployed, or made default.

## 8. Admission decision: BLOCKED

The complete FX3MS2 frame is explicitly non-atomic. After the QMP pause, the host can prove the pinned ELF header/PHDR/code words at the derived bias. It cannot prove through the allowed RSP/QMP surface that the code pages are currently executable, nor that the appFw mapping did not change across the multi-read interval. The old admission's `x` permission came from the map rows, which a multi-read frame cannot make authoritative. Because `SIGSTOP`/`ptrace`/guest modification are prohibited, the strict breakpoint contract (address + bytes + current executable mapping) is **not established**.

Therefore this candidate is delivered as a **design blocker**, not a runtime admission:

- no fallback to legacy raw maps;
- no removal of `snapshot_atomic=0`;
- no loosening of the host identity gate;
- a future reviewer must either explicitly accept the residual permission/continuity risk under a documented conditional contract, or add a permitted mechanism that establishes current executable mappings at the paused state.

This is a separate admission-semantics change and is not approved by this task.

## 9. Limits

- Host fixture/E2E only; the TLS reader is a fixture; actual target Sysregs is not verified.
- Target ELF was built and statically audited, but not executed; no target `/proc` read, no live framed map, no two keys, no boot/menu.
- The measured r6 maps block is from a different run; it is size/behavior evidence, not a runtime result for this candidate.
- No new observation is authorized; the previous one-start allowance remains consumed; FX6 menu is not passed.
- No platform/CPIO/init/r6/policy changes; original diagnostic package remains intact.

## 10. Evidence

- Source: `target/`, `host/`, `tests/`, `fixtures/`, `tools/`
- Receipts: `receipts/` (collector/host/E2E/entry tests, CPIO diff, target audit, toolchain provenance, source provenance, no-runtime)
- Build: `work/fx3-map-snapshot-v2-aarch64`, `work/fx6-map-collector-shortread-grmreal46.cpio`, `work/init.patched`, `work/cpio-binding.json`
- Reports: `REPORT.md`, `RESULT.json`, `KERNEL-EVIDENCE.md`, `ADMISSION.md`, `RUN-PLAN.md`
- SHA: `SHA256SUMS`, `SHA256SUMS.sha256`, `SEAL.json`
- Previous-run correction: `runs/fx6-framed-map-20261106T083817Z/REPORT-CORRECTION.md`, `SEAL-CORRECTION.json`, `SHA256SUMS.CORRECTED`
