# FX6 map snapshot producer — offline C reader/protocol candidate

- Task：`task_6b15f33d8164`
- Dispatch：`ctx_d3e03abc555b`
- Status：**OFFLINE_PROTOCOL_CANDIDATE; PATCH UNAPPLIED; TARGET RUN UNPROVEN; NOT BOOT/MENU**
- Workdir only: `.../fx6-map-snapshot-producer-candidate`; no CPIO generated/installed, no guest execution, no VM/QMP/RSP/live process, no platform/firmware/helper/r6 change.
- Input 5 items before/after unchanged; volume UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`.

## Producer inventory / insertion

All `/init` map-print points (source: frozen grmreal46 CPIO `/init`, extracted read-only):

- lines **59-62, 158-161, 193-196, 230-233, 410-413**: IM_ENDMAPS loops; surrounding 1s cadence; body `grep '/usr/bin/im.elf' /proc/$pid/maps` only.
- lines **324-327**: same IM loop in `FX3_BACKUP_CP_LIVE_OBSERVER` background block.
- lines **349-351**: EARLY loop `for early in 1..5`, sleep 1; body `cat /proc/uptime /proc/$pid/maps` (full maps).
- lines **367-371**: snapshot loop `for turn in 1..3`, sleep 10; scans `/proc/[0-9]*`, detects `im.elf`, then `cat status maps wchan`; full maps mixed onto shared console.

Minimal insertion is **line 371** in the turn snapshot loop; exact unapplied
`patch-init-map-snapshot.diff` replaces only the maps component:

```diff
-    /bin/busybox cat "$procdir/status" "$procdir/maps" "$procdir/wchan"
+    /bin/busybox cat "$procdir/status" "$procdir/wchan"
+    /simulation/fx3-map-snapshot "${procdir##*/}" "${turn}"
```

This preserves status/wchan, sleeps, command/return/assert behavior, libraries,
kernel, DTB, QEMU, CPU/memory and model env. It does not change a business command
or create/install a CPIO. `patch --dry-run -p1` was validated against a copy; the
frozen init was not modified.

Insertion rationale: it is the first point where same-pid `im.elf` is already
known and a full maps read is attempted; the 1s IM loops only emit im.elf and
the EARLY five-turn window can precede appFw. **No live proof** that any chosen
turn has appFw; future guest diagnostic execution requires separate review and
approval.

## C reader / protocol

`fx3_map_snapshot.c` (C11, stdlib, no dynamic deps in source):

- argv `PID SEQ`, optional `--fixture` (offline tests), `--starttime`, `--cap`;
- one `open`+one `read` on `/proc/<pid>/maps` (or fixture); max 262144 bytes;
  `read==cap` is **cap_exceeded** and exits without data; empty/unterminated is
  rejected; no signal, no target-memory write, no repeated read appended;
- starttime read from `/proc/<pid>/stat` in production; PID/starttime/sequence
  carried in the frame;
- emits framed `FX3MS1 BEGIN`, base64 `DATA` chunks in order, `END` with bytes,
  line count, FNV-1a64 digest, `line_terminated`, `complete=1`,
  `snapshot_atomic=0`;
- host `decode_snapshot.py` requires exactly one frame, contiguous chunks,
  matching PID/starttime/seq, length/line/digest, terminated final line, and
  `snapshot_atomic=0`; non-`FX3MS1` console lines are ignored and never stitched.
- It rejects mixed frames/PID/starttime, duplicate/out-of-order/missing data,
  malformed base64, length/digest mismatch, overflow, incomplete END, and mixed
  console data. It does not claim a kernel-atomic snapshot.

Consistency boundary: Linux proc(5) documents that `/proc/<pid>/maps` can change
between reads; this candidate performs **one bounded read** and explicitly marks
`snapshot_atomic=0`. A future run must treat accepted data as a bounded stream,
not an atomic map proof.

Reference: https://www.kernel.org/doc/html/v5.7/filesystems/proc.html

## Tests / evidence

- `tests/test_protocol.py` **13/13**: C compiles locally, fixture accepted with
  byte/line/digest checks, console noise ignored, mixed/duplicate/out-of-order/
  missing/overflow/unterminated/identity/digest/length negatives, and the old
  real-log source rejection is not protocol success.
- C fixture output: `receipts/c-fixture-output.txt`; decoded:
  `receipts/decoded-fixture.json` (105 map lines, 10563 bytes; synthetic fixture
  derived from actual serial map rows, not a source guarantee).
- Old actual r6 source parser remains **blocked** (`im_endmaps_source_is_imelf_only`
  at 8955–9222); no old/new real snapshot accepted. Synthetic protocol success is
  distinct from real admission.
- `patch-init-map-snapshot.diff` is unapplied; no build/install.

## Remaining / authorization

A future diagnostic guest execution, CPIO assembly/install, and real capture
window are **not authorized** here and must be separately reviewed/approved; the
r6 one-start authorization is exhausted and is not inherited. No boot/menu or
appFw-read claim is made.
