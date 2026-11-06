# FX6 map-block parser — isolated offline candidate

- Task：`task_8f5be8c859b0`
- Dispatch：`ctx_ee9fb5d365bf`
- Status：**BLOCKED_SOURCE_CONTRACT_NOT_ACCEPTED; NO VM/RSP/GUEST**
- Workdir only: `.../fx6-backup-map-parser-candidate`; frozen r6, run, inputs, platform/firmware/CPIO/helper unchanged.
- Volume UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`; input 6 items before/after unchanged.
- This is an offline parsing candidate, not boot/menu evidence; no run authorization altered.

## Producer source / boundary

Extracted read-only from the actual CPIO `/init` (hash in input seal):

- `IM_ENDMAPS` (project diagnostic script, init lines 58-62 and five other copies; not Sony official; the contract name official_im_elf below is a label for this project script, not a Sony claim):
  `echo BEGIN; cat /proc/uptime; grep '/usr/bin/im.elf' /proc/$im_pid/maps; echo END`.
  Therefore an project-diagnostic init IM block body is **im.elf only**. AppFw/lib rows between
  those markers are foreign/interleaved output, not owned by that block.
- `EARLY_MAPS` (project diagnostic script, init lines 349-351):
  `echo BEGIN; cat /proc/uptime /proc/$im_pid/maps; echo END`.
  EARLY is the full-map producer; a complete EARLY block may own appFw rows.

The parser closes any block interrupted by another BEGIN as incomplete, never
merges it, requires an exact same pid/epoch END, treats mismatched END as stray,
and selects only the **last marker block**. A later incomplete block is not
silently replaced by an older complete block.

## Current r6 serial (actual)

`.../runs/r6-stop-only-20261106T2005Z/run/serial.log`:

- 74 blocks; last block `IM_ENDMAPS_239` begins 47959, no END -> full-log
  `newest_block_incomplete`; conservative, no fallback.
- The only appFw-visible block starts at **8955**, ends **9222**, complete.
  It has 104 map rows, **4 appFw rows at lines 9078–9081**, 6 im.elf rows and
  **98 foreign rows** (libs). Official IM producer source is im.elf-only, so
  this complete block is **not source-owned**:
  `im_endmaps_source_is_imelf_only`.
- Incremental replay:
  - 9078/9081 (appFw rows visible while block open): `newest_block_incomplete`;
  - 9222 (END): `im_endmaps_source_is_imelf_only` (foreign98, appfw4);
  - 9223: same source rejection;
  - 10364: new block open, incomplete;
  - full 47966: latest block open, incomplete.
- **No cut admits the current project init producer block.** The previous observer's
  wait was not only “missing IM support”; the appFw rows are not owned by the
  project diagnostic init IM producer.

## 66ed fixture (old) — END exists, parser was wrong

`.../cp-bind-66ed0f78/serial.log`:

- `EARLY_MAPS_237_5` **begins 8029 and ends 8950**; appFw rows are lines
  **8039–8041** (3 rows), inside the early full-map producer.
- The nested `IM_ENDMAPS_237` at **8135–8678** is a same-pid child. The
  initial parser treated its BEGIN as interrupting the parent and discarded the
  parent; that was a parser bug. The corrected stack attributes rows only to the
  innermost block, resumes the parent after the child, and marks the parent
  complete at 8950 (`depth=0`, nested child complete, `overlap_with_previous`
  true on the child).
- Segment to 8950 has complete structural block/bias `0x7ed3ccc000` and 3 appFw rows, but this is **not source-safe runtime admission**: the early parent coexists with a nested IM writer, and outer `cat` rows can still land inside markers.
  Full log still has a later top-level block beginning 69489 with no END, so the
  **full-log** decision is `newest_block_incomplete`; no fallback.
- Distinction: the **source log has the END**; the initial parser **discarded**
  the block due to nested interleaving. Do not describe this as a missing source
  END.

## Future full IM (structural only)

`full_proc_maps` is an explicit producer contract, not inferred from current
log. On the 8955–9222 segment it structurally yields:

- bias `0x7efab5b000`;
- four appFw rows (lines 9078–9081); inode 1048; code pages r-xp;
- ELF PT_LOAD: 2 segments (fileoff 0/va0/filesz 0x2900000; fileoff 0x2901010/va0x291…);
- static machine words at 0x2169784/0x11f67d4/0x21697d4/0x11f67f4 match;
- code ranges mapped/readable/executable.

This is **not an actual admission**: source still greps im.elf, so default
`official_im_elf` blocks. A future changed producer must provide a new source
guarantee and complete same-pid block; offline time order cannot prove a future
real-time capture window.

## Interval coverage

`map_bias` now checks the sorted union of selected appFw rows from segment start to required page extent; an interior gap yields `coverage_gap`, not just a max endpoint check. Negative test removes the appFw `r--` row and must reject.

## Diagnostics / tests

- `mapping_parser.py` exposes `MapParserError(code, block, diagnostics)` and
  `MappingProvider.last_rejection`; no generic timeout swallowed. Diagnostic
  codes: `newest_block_incomplete`, `im_endmaps_source_is_imelf_only`,
  `mixed_inode`, `bad_bias`, `nonexec_code`, `no_appfw`, etc.
- `tests/test_parser.py` 13/13: actual current/66ed cuts, full end, producer
  source, pid/end/nesting/mixed inode/perms/offset/interval-gap/no-appfw negatives,
  nested overlap flag, synthetic full-contract mapping.
- `replay-current-official.json`, `replay-66ed-official.json`,
  `synthetic-full-contract-9222.json`, `synthetic-full-mapping.json`,
  `map-block-inventory.json`, `producer-contract.md`.

## Conclusion

No source-safe runtime appFw admission is claimed for r6 or 66ed. Current r6 has no parse; 66ed has only structural parent recovery. The correct
result is **blocked**, not a forced appFw map. No VM/QMP/RSP/guest/live-process,
browser, camera, USB or SD action; no platform/firmware/CPIO/helper changes.
