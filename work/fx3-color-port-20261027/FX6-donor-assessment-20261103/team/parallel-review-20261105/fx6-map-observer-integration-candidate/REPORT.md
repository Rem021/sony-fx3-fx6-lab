# FX6 map observer integration — offline target + CPIO + host candidate

- Task：`task_bb14b0c979a1`
- Dispatch：`ctx_4010383815e7`
- Status：**OFFLINE_INTEGRATION_CANDIDATE_BUILT; TARGET LIVE/RUN UNPROVEN; NOT DEPLOYED**
- No VM/QMP/RSP/guest/live process/browser/camera/USB/SD; no target ELF execution; no default-entry install. r6, original 3a08 CPIO, firmware/helper/kernel/DTB/QEMU/CPU/memory/modelenv unchanged.

## AArch64 static reader

Toolchain cache: `work/toolchain` (musl 1.2.6 archive 1,082,499 bytes / SHA `d585fd3b…`; license retained). Source URL `https://musl.libc.org/releases/musl-1.2.6.tar.gz`; GPG signature **not verified** (`gpg` unavailable), not claimed. Compiler `/usr/bin/clang`, linker LLD 23.1.1 path recorded in `receipts/toolchain-provenance.json`; no toolchain download beyond musl.

Built production mode (no `FX3_MAP_SNAPSHOT_TEST`, no fake/env parameters):

```
clang --target=aarch64-linux-musl -march=armv8-a -O2 -fno-stack-protector -fno-pic
ld.lld -static -nostdlib -e _start --gc-sections
```

Target `work/fx3-map-snapshot-aarch64`:

- ELF64 LSB, `e_machine=183` AArch64, `ET_EXEC`, entry `0x210a80`;
- **no PT_INTERP, no PT_DYNAMIC**, static; 4 PT_LOAD; SHA `9df5a10a…`;
- `work/target_io.c` is a minimal write/format layer used only to avoid unavailable cross compiler-rt soft-float printf; collector read/identity semantics unchanged.
- Target ELF was **not executed**.

## New CPIO (diagnostic only)

`work/fx6-map-observer-grmreal46.cpio`, SHA `9d4f255b…`, 453,306,948 bytes, built by `build_cpio.py` (newc parser/rebuilder; actual reparse vs original and 25,746,348B original zero tail preserved).

`receipts/cpio-diff.json`:

- original 1157 members, new 1158;
- only `init` changed (21,195→21,239 bytes) and new `simulation/fx3-map-snapshot` (122,264 bytes);
- **1156 other members content+header unchanged**, `only_expected_changes=true`;
- `work/init.patched` differs from original only at the reviewed line 371 maps diagnostic replacement; patch file `patch-init-map-snapshot.diff` is unapplied to the source CPIO.
- Original CPIO SHA `3a08f89d…` unchanged; config hashes in `receipts/config-invariance.json`.
- Not installed, not default, not deployed.

## Host integration

- `framed_provider.py`: consumes `FX3MS1` stream via strict decoder, selects latest same-identity frame, parses appFw intervals, runs parser map/ELF/PT_LOAD/code/static-word checks; **no legacy raw-maps fallback**; provider binds new CPIO hash/size.
- `live_runner.py`: adapter around frozen r6 `HostRunner`; binds new CPIO constants and framed provider; no QEMU start on import. Frozen r6 not modified.
- `run_map_observer.py`: new default-disabled token `APPROVE_FX6_FRAMED_MAP_OBSERVER_20261106`, requires `--new-run-approval` and fresh `--run-root`; without gates no launch; original 150/180/zero-key policy remains in frozen HostRunner.
- Fake tests **10/10**: provider accepts framed fixture, corrupt/missing END rejected no fallback, CLI unauthorized/no token/approval rejects, fake runner called once only after gates.
- Actual HostRunner E2E **1/1** (`tests/test_e2e_hostrunner.py`): actual frozen Observer/QMP/RSP/Sysregs four stops through current entry/provider, empty→partial→complete serial, receipt/quit/reap/locks. Host diff `HOST-DIFF.txt`; no VM/live Guest execution and no QMP/RSP. A real future run needs separate authorization; r6 one-start authorization exhausted/not inherited.

## Limits

This proves offline target compile/ELF/CPIO construction/provider logic; it does **not** prove target Linux execution, `/proc` availability, live map capture, two keys, guest restore, boot or menu. No source-safe runtime admission is claimed from old mixed serial.
