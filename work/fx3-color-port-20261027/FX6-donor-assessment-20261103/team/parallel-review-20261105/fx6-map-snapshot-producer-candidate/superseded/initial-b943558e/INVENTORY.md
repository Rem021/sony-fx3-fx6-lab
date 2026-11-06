# `/init` map-print inventory and minimal insertion

Source: frozen grmreal46 CPIO `:/init`; extracted read-only to `work/init.original`. Patch is **unapplied**.

| init lines | body | trigger/window | producer-owned content |
|---|---|---|---|
| 59-62 | `IM_ENDMAPS_<pid>_BEGIN; uptime; grep '/usr/bin/im.elf' maps; END` | background/early while loops, 1s cadence | im.elf rows only |
| 158-161 | same IM loop | alternate module-probe while branch | im.elf only |
| 193-196 | same IM loop | ABI/library-probe while branch | im.elf only |
| 230-233 | same IM loop | stream/DMM branch | im.elf only |
| 324-327 | same IM loop | `FX3_BACKUP_CP_LIVE_OBSERVER` background loop | im.elf only |
| 410-413 | same IM loop | later native/free loop | im.elf only |
| 349-351 | `EARLY_MAPS_<pid>_<early>_BEGIN; cat uptime maps; END` | `for early in 1..5`, sleep 1 each | full maps; appFw may appear |
| 367-371 | scan `/proc/[0-9]*`, if maps contains im.elf: `cat cmdline; status maps wchan` | `for turn in 1..3`, sleep 10 each | full maps/status; console-mixed |

## Minimal insertion

At **line 371** in the turn snapshot loop, replace only the maps component of the
existing `cat` with one bounded collector call; keep status/wchan and all other
startup/business commands unchanged:

```diff
-    /bin/busybox cat "$procdir/status" "$procdir/maps" "$procdir/wchan"
+    /bin/busybox cat "$procdir/status" "$procdir/wchan"
+    /simulation/fx3-map-snapshot "${procdir##*/}" "${turn}"
```

Rationale: this is the only place that (a) has already discovered the
same-pid `im.elf` process, (b) runs after the 10s turn waits rather than the
1s early window, and (c) currently prints the full maps stream directly to the
shared console. The helper emits one framed, bounded snapshot; it does not
change sleeps, assertions, return codes, libraries, kernel, DTB, QEMU, CPU,
memory or model env.

This does **not** prove appFw is loaded at a chosen turn; a future approved
diagnostic run must show that. The patch is not applied and no CPIO is built or
installed.

## Protocol

`fx3_map_snapshot.c` (C11, stdlib, one `read()` on `/proc/<pid>/maps`, max
262144 bytes; overflow/truncation rejected) emits `FX3MS1`:

- `BEGIN pid= starttime= seq= cap= single_read=1 capture=bounded_single_read`
- base64 `DATA <chunk> ...` in order
- `END pid= starttime= seq= bytes= lines= digest=fnv1a64:... line_terminated= complete=1 snapshot_atomic=0`

`decode_snapshot.py` requires exactly one frame, matching pid/starttime/seq,
contiguous DATA chunks, length/line-count/FNV digest, terminated final line,
`snapshot_atomic=0`; it ignores non-`FX3MS1` console noise but never stitches it
into the maps buffer. It rejects mixed/duplicate/out-of-order/missing/overflow.

Consistency boundary: one read is a **bounded single-read capture**, not an
atomic kernel snapshot; Linux `proc(5)` documents that maps can change across
reads. `snapshot_atomic=0` is required. No second read is appended.
