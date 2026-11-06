# Kernel and `/proc/<pid>/maps` evidence

## Fixed kernel

- Frozen kernel: `/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage47-runtime-provider-binding/official-files/nflasha3/vmlinux.bin`
- SHA-256: `da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c`, 6,610,952 bytes (frozen baseline).
- Embedded version string: `Linux version 4.9.337-scel+ (jp10239@dic-build-scm-u20-028) ... #1 SMP PREEMPT Thu Dec 25 08:15:40 JST 2025`; the failed run serial shows the same line. Platform: AArch64, FX3 kernel/DTB/QEMU unchanged.

## Official maps/smaps reference

The task supplied this official reference:

`https://www.kernel.org/doc/html/v5.7/filesystems/proc.html`

This host could not fetch it: DNS resolution returned a non-public address. No quotation is fabricated here. The task-supplied reference states that `/proc/<pid>/maps`/`smaps` are live views, and multiple reads can observe different states; therefore a loop of reads cannot be presented as an atomic snapshot.

## Observed failure is not cap exhaustion

The failed run's serial (`fx6-framed-map-20261106T083817Z/run/serial.log`, SHA `6a397851b49ce874c8acccb3b1c6d72ee6ed6ab1d10e87b43d394ed0f220571a`) contains exactly:

```
FX3MS1 ERROR pid=237 starttime=1490 seq=1 reason=short_read_more_data
```

In the frozen helper source (`fx3-map-observer-integration-candidate/fx3_map_snapshot.c`):

- `short_read_more_data` is emitted only after `io_data()` returned `n < cap` and the one-byte EOF probe returned `pr > 0`.
- `cap_exceeded` is a different branch, reached only when `n >= cap`.
- `emit()` is never reached in the `short_read_more_data` branch; the helper deliberately refuses to emit a truncated `BEGIN`/`DATA`/`END` frame.

Thus the observed failure is a short-read-plus-more-data condition, not the cap branch. Expanding `262144` blindly would not fix the state machine.

## Measured real maps size

The accepted r6 stop-only serial (`.../runs/r6-stop-only-20261106T2005Z/run/serial.log`, SHA `bf5b667bb0b774871f513745662e86951ff83b0858465a4baca835702755831a`, 3,812,875 bytes) contains four full `FX3_AP_EARLY_MAPS_239_<epoch>` blocks:

| epoch | rows | map row bytes | rows + framing |
|---:|---:|---:|---:|
| 2 | 281 | 28,805 | ~28,885 |
| 3 | 352 | 35,914 | ~35,994 |
| 4 | 411 | 41,791 | ~41,871 |
| 5 | 428 | 43,509 | ~43,589 |

The largest full maps block is **43,509 bytes**, far below the unchanged 262,144-byte cap. That is supporting evidence that cap expansion is not the fix; it is a different guest/run, so it is not substituted for the failed run's missing snapshot.

## 4.9 `seq_file` read behavior

On Linux 4.9, `/proc/<pid>/maps` is a `seq_file` view. A `read()` may return fewer bytes than requested even when more data remains; a single `read()` plus a one-byte probe is not a complete transfer. The corrected state machine therefore reads until `read()` returns 0 (EOF), under the explicit bounds in `collector_core.h`. It does not use a second read to "append" to a frame after an error, and it does not fall back to the old raw maps parser.

The transfer is explicitly **non-atomic**: the protocol emits `snapshot_atomic=0`. The host contract is discussed in `ADMISSION.md`.

## Boundaries

- No target ELF was executed and no VM/QMP/RSP/guest was started in this task.
- The measured r6 maps block is from a different accepted run; it is used only as size/behavior evidence, not as a runtime result for the new candidate.
