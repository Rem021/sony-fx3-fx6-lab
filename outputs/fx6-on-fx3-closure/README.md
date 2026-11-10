# `fx6-on-fx3-closure` — Phase 8 Compatibility Closure, `cxd90057.dtb` FDT Auditor, `.ko` `vermagic`/`__versions` Integrity, `U5`/`U3`/`U4`/`BK4\0` & CPIO Suite

Pure source-only engineering package for deterministic FX6-on-FX3 binary compatibility adaptation (`P1..P9` 9/9 full matrix + `Fan`), `VFAT` loopback image generation, UIPC completion synthesis, dual-kernel Backup Sync100 signature & trampoline verification, **Blueprint §3 5-Core-Camera-Feature Routing & Cross-Model ELF Dynamic Symbol Closure verification**, **Phase 6 Storage Mount-Failure Tolerance (`U4` Closure) & RAM-Only Shadow `BK4\0` Backup Schema Synthesis**, **Phase 7 Boot-Selector Single-Shot Fallback Contract (`U5` Closure) & `0xfa0080` Bank 0/1 DDR Load-Map Non-Overlap Verifier (`U3` Advancement)**, **Phase 8 Flattened Device Tree (`cxd90057.dtb` `0xd00dfeed`) SoC MMIO/Carveout Compatibility Auditor & Kernel Module `.modinfo` (`vermagic`) / `__versions` (`modversion_info`) CRC Integrity Verifier**, Unicorn AArch64 instruction-level emulation, freestanding Tier-0 two-pass read-only backup verification, RAM-Overlay `cpio newc` packaging, 4-Layer Fail-Safe automatic rollback sandbox drills, and 12-Gate pre-flash safety evaluation.

## Cleanroom & Safety Guarantees

- **Zero binary persistence**: All adapted binaries, compiled `.so` artifacts, `.vfat` images, `.cube` 3D LUT test tables, RAM-shadow `BK4\0` containers, synthetic `__versions`-instrumented `.ko` test images, and `.cpio` archives are synthesized strictly in memory or inside `tempfile.TemporaryDirectory()` and removed automatically on exit (`flash_write_allowed = False`; physical `p2:/setting/Backup.bin`, `p2:/setting/updater/mode*`, and `p1:/updater` are never modified).
- **100% deterministic SHA-256 rollback & reproducibility**: Every binary adaptation specification (`ET_DYN` shared libraries, `ET_REL` `.ko` kernel modules, and in-memory 16-byte kernel entry hooks) enforces segment/section bounds, context byte verification, and bit-exact SHA-256 restoration; both the pure-Python `cpio newc` (`070701`) builder and the RAM-shadow `BK4\0` synthesizer produce 100% reproducible SHA-256 digests.
- **Sandboxed zero-host-side-effect rollback drills**: All POSIX `/bin/sh` fail-safe drills inject an isolated `TemporaryDirectory` via `PREFIX`, enforce a host-OS guard + sandbox `busybox` path lock (never touching host `/dev` or `/tmp`), and verify **0 writes** across simulated eMMC partitions (`sector0`, `p2`, `p6`, `p15`, `p18`).
- **Zero hardware or VM side effects**: Strictly offline static, memory, POSIX sandbox, and Unicorn AArch64 emulation; `persistent_write_release` remains unconditionally `False`.

## Module Structure

- `fx6_closure/elf_verify.py` — ELF64 `PT_LOAD` (`ET_DYN`/`ET_EXEC`) and `ET_REL` section-header file-offset mapper.
- `fx6_closure/patcher.py` — Compatibility adaptation & rollback specs for P1 (`libInfraSetupFile.so`, `libInfraMediaCommon.so`, `libInfraMediaConfig.so`, `appFw.so`), P3 (`libInfraAppRemoteBoard.so`), P4 (`appFw.so` ND Clear lock), P8 (`appFw.so` `0x2159c50` non-blocking async log wait), P9 (`upm.ko` `.text+0x136b8` null-callback guard), and Fan (`libfan.so` `0x1dec` `_Z19fan_i_bkup_is_validv`).
- `fx6_closure/vfat_builder.py` — Deterministic pure-Python `FAT16` / `FAT32` image builder (`8m_ram`, `16m_log`, `44.5m_log`, `44.5m_fat32`) and BPB / dual-FAT / `/OPE/{00,01}` auditor (P2).
- `fx6_closure/nd_unicorn_verifier.py` — Unicorn AArch64 instruction-level verifiers for P3, P4 (576-combination sweep), P8, P9, and Fan.
- `fx6_closure/uipc_completion_verifier.py` — P5 (`0x032d -> 0x132d`) & P6 (`0x0400 -> 0x1400`, `0x0402 -> 0x1402`, `0x0404 -> 0x1404`, `0x0152 -> 0x1152`) byte-exact UIPC completion synthesizer on queue `0x92840747` and Unicorn AArch64 verifier for `appFw.so` `send_and_wait_cmp_i` (`0x20ef604`..`0x20ef7ec`) + `0x20edd1c` status mapper.
- `fx6_closure/backup_bridge_verifier.py` — P7 kernel-space Backup Sync100 address-agnostic bridge verifier: dual-kernel `pcidma_transfer_async` 16-byte prologue (`b4000b00, a9bb7bfd, 910003fd, a90153f3`), `fallback_zero = api + 0x160` / `fallback_nonzero = api + 0x10` Unicorn trampoline on FX3 (`0xffffff80083220c8`) and FX6 (`0xffffff8008322f70`), 40-byte `dst = 0x903e0811` / `op = 0x30` schema, and synchronous `backupfile_cb_getcp` DMA callback contract.
- `fx6_closure/feature_routing_verifier.py` — **Phase 5 Blueprint §3 5-Core-Feature Routing & Cross-Model ELF Dynamic Symbol Closure Verifier** (43-node `DT_NEEDED` transitive closure, 16x `33^3` `.cube` `p30` budget, and Cine EI / AF / `libmpr.so` Dual-Slot Unicorn contracts).
- `fx6_closure/backup_mount_tolerance_verifier.py` — **Phase 6 Storage Mount-Failure Tolerance (`U4` Closure) & RAM-Shadow `BK4\0` Synthesizer** (Unicorn verification of `SetupFile::RcvThread` @ `0x19650` & `KikiLogGenerator_res_ope` @ `0x3cb0` + `20,588 B` RAM-Shadow `BK4\0` synthesis).
- `fx6_closure/boot_selector_and_bank_verifier.py` — **Phase 7 Boot-Selector Single-Shot Fallback Contract (`U5` Closure) & `0xfa0080` Bank 0/1 DDR Load-Map Verifier (`U3` Advancement)** (`up.sh` + `ud_send_lsi.elf` 10-case Unicorn + `loader_nor.bin` arbitrator + 64-slot `0xfa0080` Bank 0/1 pairwise non-overlap & `+0xE0000` / `+0x14000` calibration shifts).
- `fx6_closure/kernel_dtb_compatibility_verifier.py` — **Phase 8 Flattened Device Tree (`cxd90057.dtb`) SoC Compatibility Auditor & Kernel Module `vermagic` / `__versions` CRC Integrity Verifier**:
  - **Dimension A (Pure-Python `0xd00dfeed` FDT Parser & `cxd90057.dtb` SoC Audit)**: Dependency-free Devicetree v0.4 parser validating big-endian header bounds, 4B/8B alignment, `/memreserve/` sentinel termination, balanced token streams (`FDT_BEGIN_NODE` / `FDT_END_NODE` / `FDT_PROP` / `FDT_NOP` / `FDT_END`), and string offsets. Audits FX3 vs FX6 `cxd90057.dtb` (`17,131 B`, `87abb2b7...`), proving **100% byte-for-byte identity across all 68 FDT nodes and 493 properties** (`cxd,cxd90057`, 4x Cortex-A35, `memory@400000000` `8 GiB` capped via `mem=2G`, static `iomap` `/esram@0xfe000000` + `/iomem*`, `/pcie_ep_dummy` `phandle=0x7`, `arm,gic-400`, 5x `arm,pl011` UARTs, `arasan,sdhci` eMMC, 5x `snps,dw-pcie` + 5x `cxd900xx-pcie-ep` IPC endpoints), **100% `loadaddr.txt` identity**, and **100% identity across all 7 `kemco.txt` `memrsv=` DDR carveouts** (documenting the exact 2-line `ramdisk_size` / `initrd` ceiling delta).
  - **Dimension B (`.ko` `.modinfo` `vermagic` & `__versions` `modversion_info` CRC Verifier)**: Parses ELF64 `ET_REL` `.modinfo` (`vermagic`, `name`, `depends`), `.gnu.linkonce.this_module` (`768 B`), `__versions` (`struct modversion_info`: `8B LE crc + 56B name = 64B`), `SHN_UNDEF` imports, and `__ksymtab_strings` exports across all 9 FX3 host `.ko` modules and FX6 `p15`/`p3`/`p1` `.ko` modules. Proves Sony compiled `4.9.337-scel+` with `!CONFIG_MODVERSIONS`, proves `P9` (`upm.ko` `.text+0x136b8`) preserves **100% of `.modinfo`, `.gnu.linkonce.this_module`, `SHN_UNDEF`/`__ksymtab` symbols, and 100% of `61` `modversion_info` CRCs** (never triggering `ENOEXEC`), and quantifies the two cross-kernel `.ko` mixing hazards (`p1` `4.9.186-scel` `vermagic` mismatch across 8 modules + `p15` `backup.ko`/`upm.ko` `SHN_UNDEF` symbol drift on `Backup_sync_subsystem_for_senser_local` & `pcie_link_width_check_dev_state_ch0`).
- `fx6_closure/ram_overlay_packager.py` — Pure-Python deterministic SVR4 `cpio newc` (`070701` magic, 4-byte alignment, `TRAILER!!!` sentinel) builder & parser/auditor assembling `etc/fx6_overlay/{setup_fx6_compat.sh,init2_guard.sh,overlay_manifest.json}`.
- `fx6_closure/rollback_drill.py` — Deterministic 4-Layer Fail-Safe state machine and `PREFIX`-isolated POSIX `/bin/sh` subprocess drill runner covering all 4 mandatory scenarios.
- `native/tier0_backup_worker.c` & `fx6_closure/tier0_unicorn_verifier.py` — Freestanding zero-import AArch64 Linux two-pass read-only backup worker (`svc #0`) and Unicorn syscall emulator.
- `fx6_closure/candidate_builder.py` — Ephemeral end-to-end offline candidate assembler (`P1..P9` 9/9 + `Fan` + `5-Feature Routing` + `U4/RAM-Shadow BK4` + `U5/U3 Boot-Selector & Bank DDR` + `Phase 8 DTB/.ko Integrity` + `CPIO` + `Rollback Drill` + `Tier-0`) and `fx3_safety` 12-Gate evaluator (`Gate G12` `backup_mount_tolerance_ok`, `boot_selector_and_banks_ok`, and `kernel_dtb_ok`) integration.
- `fx6_closure/__main__.py` — CLI entrypoint (`verify-donors`, `run-unicorn-audit`, `run-rollback-drill`, `verify-feature-routing`, `verify-backup-mount-contracts`, `verify-boot-selector-banks`, `verify-kernel-dtb`, `dry-run-candidate`).

## CLI & Unit Test Commands

```sh
# 1. Verify all 7 binary targets (P1, P3, P4, P8, P9, Fan), 100% SHA-256 rollback & P7 dual-kernel signatures
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure verify-donors

# 2. Run Unicorn AArch64 instruction-level (P3, P4, P5, P6, P7, P8, P9, Fan) & Tier-0 syscall audit
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure run-unicorn-audit

# 3. Build RAM-Overlay CPIO newc package & execute all 4 sandboxed fail-safe rollback scenarios
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure run-rollback-drill

# 4. Verify Blueprint §3 5-core-feature routing, 43-node ELF64 symbol closure, 16x .cube p30 budget & dual-slot Unicorn contracts
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure verify-feature-routing

# 5. Verify Phase 6 U4 storage mount-failure tolerance in Unicorn & synthesize/audit RAM-shadow BK4\0 contracts
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure verify-backup-mount-contracts

# 6. Verify Phase 7 U5 boot-selector contract (ud_send_lsi.elf Unicorn + loader_nor.bin) & U3 Bank 0/1 DDR non-overlap maps
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure verify-boot-selector-banks

# 7. Verify Phase 8 cxd90057.dtb FDT (0xd00dfeed) SoC MMIO/carveouts & .ko vermagic/__versions CRC integrity
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure verify-kernel-dtb

# 8. Assemble full P1..P9 + Fan + 5-Feature Routing + U4/BK4 + U5/U3 + DTB/.ko + CPIO candidate & evaluate all 12 safety gates
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure dry-run-candidate

# 9. Run full unit test suites (40/40 + 13/13)
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -v
PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -v
```
