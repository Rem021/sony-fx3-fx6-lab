# `fx6-on-fx3-closure` — Phase 12 Compatibility Closure, `U1..U5` Blueprint Unknowns Closure, `nflasha3-initrd` Boot-Chain & WBI (`p5`) Hibernation Redline, Atomic Stage-A Orchestrator, Cross-Package `p1` Bridge & 12-Gate Suite

Pure source-only engineering package for deterministic FX6-on-FX3 binary compatibility adaptation (`P1..P9` 9/9 full matrix + `Fan`), `VFAT` loopback image generation, UIPC completion synthesis, dual-kernel Backup Sync100 signature & trampoline verification, **Blueprint §3 5-Core-Camera-Feature Routing & Cross-Model ELF Dynamic Symbol Closure verification**, **Phase 6 Storage Mount-Failure Tolerance (`U4` Closure) & RAM-Only Shadow `BK4\0` Backup Schema Synthesis**, **Phase 7 Boot-Selector Single-Shot Fallback Contract (`U5` Closure) & `0xfa0080` Bank 0/1 DDR Load-Map Non-Overlap Verifier (`U3` Closure Foundation)**, **Phase 8 Flattened Device Tree (`cxd90057.dtb` `0xd00dfeed`) SoC MMIO/Carveout Compatibility Auditor & Kernel Module `.modinfo` (`vermagic`) / `__versions` (`modversion_info`) CRC Integrity Verifier**, **Phase 9 30-Partition Zero-Repartition Storage/`p15` (`/usr`) Footprint (`U1` Zero-Repartition Closure) & CXD90057 Linux DDR / Stage-A `tmpfs` RAM-Overlay Budget Verifier**, **Phase 10 CP RTOS (`cpapp-b.bin`) & `nflasha8` (`tomco.txt`) Cross-Model Compatibility Verifier (`U2` Closure & Stage-A Stock-CP Redline)**, **Phase 11 Cross-Package `p1` Recovery & Tier-0 Bridge Verifier (`fx3_recovery` ↔ `fx3_safety` ↔ `fx6_closure`)**, **Phase 12 `nflasha3-initrd` Boot-Chain, WBI (`p5:/wbi`) Hibernation Safety Redline & Atomic Verify-Before-Mount Stage-A Boot Orchestrator (`30-stage-a-orchestrator.sh`)**, Unicorn AArch64 instruction-level emulation, freestanding Tier-0 two-pass read-only backup verification, RAM-Overlay `cpio newc` packaging, 4-Layer Fail-Safe automatic rollback sandbox drills, and 12-Gate pre-flash safety evaluation.

## Clean-Room & Safety Guarantees

- **Zero binary persistence**: All adapted binaries, compiled `.so` artifacts, `.vfat` images, `.cube` 3D LUT test tables, RAM-shadow `BK4\0` containers, synthetic `__versions`-instrumented `.ko` test images, and `.cpio` archives are synthesized strictly in memory or inside `tempfile.TemporaryDirectory()` and removed automatically on exit (`flash_write_allowed = False`; `edisx_repartition_forbidden = True`; `sector0_mutation_bytes = 0`; `p8_cp_mutation_forbidden = True`; `cp_mutation_bytes = 0`; `wbi_p5_write_and_hibernation_forbidden = True`; `wbi_mutation_bytes = 0`; physical `p2:/setting/Backup.bin`, `p2:/setting/updater/mode*`, `p1:/updater`, `p5:/wbi`, and `p8:/cpapp-b.bin` are never modified).
- **100% deterministic SHA-256 rollback & reproducibility**: Every binary adaptation specification (`ET_DYN` shared libraries, `ET_REL` `.ko` kernel modules, and in-memory 16-byte kernel entry hooks) enforces segment/section bounds, context byte verification, and bit-exact SHA-256 restoration; both the pure-Python `cpio newc` (`070701`, `30,860 B`, 6 entries) builder and the RAM-shadow `BK4\0` synthesizer produce 100% reproducible SHA-256 digests.
- **Sandboxed zero-host-side-effect rollback & orchestrator drills**: All POSIX `/bin/sh` fail-safe and Stage-A orchestrator drills inject an isolated `TemporaryDirectory` via `PREFIX` / `STAGE_A_PREFIX`, enforce a host-OS guard + sandbox `busybox` path lock (never touching host `/dev` or `/tmp`), and verify **0 writes** across simulated eMMC partitions (`sector0`, `p2`, `p5`, `p6`, `p8`, `p15`, `p18`).
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
- `fx6_closure/boot_selector_and_bank_verifier.py` — **Phase 7 Boot-Selector Single-Shot Fallback Contract (`U5` Closure) & `0xfa0080` Bank 0/1 DDR Load-Map Verifier (`U3` Foundation)** (`up.sh` + `ud_send_lsi.elf` 10-case Unicorn + `loader_nor.bin` arbitrator + 64-slot `0xfa0080` Bank 0/1 pairwise non-overlap & `+0xE0000` / `+0x14000` calibration shifts).
- `fx6_closure/kernel_dtb_compatibility_verifier.py` — **Phase 8 Flattened Device Tree (`cxd90057.dtb`) SoC Compatibility Auditor & Kernel Module `vermagic` / `__versions` CRC Integrity Verifier** (68-node / 493-property `0xd00dfeed` FDT identity + 7 `kemco.txt` `memrsv=` carveouts + `.ko` `vermagic` & `modversion_info` CRC integrity).
- `fx6_closure/storage_and_ram_budget_verifier.py` — **Phase 9 30-Partition Zero-Repartition Topology (`U1` Closure), `edisx.elf` Redline, `p15` (`/usr`) Footprint & CXD90057 Linux DDR / Stage-A `tmpfs` RAM-Overlay Budget Verifier** (`+138.76 MiB` raw / `+74.81 MiB` ext2-image headroom on `500.00 MiB` `p15`, and `57.46 MiB`–`130.76 MiB` peak `tmpfs` within `256.00 MiB` safe ceiling).
- `fx6_closure/cp_rtos_compatibility_verifier.py` — **Phase 10 CP RTOS (`cpapp-b.bin`) & `nflasha8` (`tomco.txt`) Cross-Model Compatibility Verifier (`U2` Closure & Stage-A Stock-CP Redline)** (100% identical 4x `memcfg=` `1,724.00 MiB` & 20 IPC keys in `tomco.txt`, `@ 0x00108000` ARM32 load contract, 8 FX6-exclusive `Darwin`/`Mew` CP hardware hazards, and `p8_cp_mutation_forbidden = True` / `cp_mutation_bytes = 0`).
- `fx6_closure/p1_recovery_bridge_verifier.py` — **Phase 11 Cross-Package `p1` Recovery & Tier-0 Bridge Verifier (`fx3_recovery` ↔ `fx3_safety` ↔ `fx6_closure`)** (Tier-0 ↔ `fx3_p1_reader`/`fx3_boot_reader` `O_RDONLY` Unicorn alignment, FX6 `nflasha1` FAT16/SquashFS/`p1chksum` container audit, and mandatory 2-step `U5` Bank 0 exit guarantee).
- `fx6_closure/stage_a_boot_orchestrator.py` — **Phase 12 `nflasha3-initrd` Boot-Chain, WBI (`p5:/wbi`) Hibernation Safety Redline & Atomic Verify-Before-Mount Stage-A Boot Orchestrator**:
  - **Dimension A (`nflasha3-initrd` → `/usr` → `im.elf` & `p5:/wbi` Safety Audit)**: Pins 27 boot-chain SHA-256 digests (`sbin/init` → `insmod_drv1` 4 `.ko`s → `setup_nflash` → `sbin/init2` → `fstab` `/usr` `ext2 ro` → `insmod_drv2` 39 `.ko`s with `upm.ko` at slot `#24` → `setup_bis || setup_senser` → `bootin.elf &` → `im.elf`), parses the live `88 B` `WBI2` header of FX6 `0700_part_image/dev/nflasha5` (`202,677,056 B`, `1,197` sections, `resume_vector = 0x4004a87f0`, `wbimem` `+13.47 MiB` DDR collision vs FX3 `0x00BA0000@0x410524000`), and enforces `wbi_p5_write_and_hibernation_forbidden = True` / `wbi_mutation_bytes = 0` (`Gate G12` `BLOCKED_BY_STAGE_A_ORCHESTRATOR_OR_WBI_REDLINE`).
  - **Dimension B (`30-stage-a-orchestrator.sh` & 6-Scenario POSIX `/bin/sh` Sandbox Verifier)**: Synthesizes deterministic `10,931 B` `etc/fx6_overlay/30-stage-a-orchestrator.sh` and verifies 10 isolated `/bin/sh` runs across nominal 11-digest Verify-Before-Mount + 10-step activation + reverse `10..1` LIFO teardown (`S1`), corrupted `appFw.so` / `opelog.vfat` pre-mount abort (`S2`), mid-sequence step-3 / step-9 LIFO rollback (`S3`), WBI `BIS`/RW/trigger guard (`S4`), idempotent re-entry lock (`S5`), and cold-boot passthrough (`S6`).
- `fx6_closure/ram_overlay_packager.py` — Pure-Python deterministic SVR4 `cpio newc` (`070701` magic, 4-byte alignment, `TRAILER!!!` sentinel, `30,860 B`, 6 entries including `30-stage-a-orchestrator.sh`) builder & parser/auditor.
- `fx6_closure/rollback_drill.py` — Deterministic 4-Layer Fail-Safe state machine and `PREFIX`-isolated POSIX `/bin/sh` subprocess drill runner covering all 4 mandatory scenarios.
- `native/tier0_backup_worker.c` & `fx6_closure/tier0_unicorn_verifier.py` — Freestanding zero-import AArch64 Linux two-pass read-only backup worker (`svc #0`) and Unicorn syscall emulator.
- `fx6_closure/candidate_builder.py` — Ephemeral end-to-end offline candidate assembler and `fx3_safety` 12-Gate evaluator (`Gate G12` `backup_mount_tolerance_ok`, `boot_selector_and_banks_ok`, `kernel_dtb_ok`, `storage_and_ram_budget_ok`, `cp_rtos_ok`, `p1_recovery_bridge_ok`, and `stage_a_orchestrator_ok`) integration.
- `fx6_closure/__main__.py` — CLI entrypoint (`verify-donors`, `run-unicorn-audit`, `run-rollback-drill`, `verify-feature-routing`, `verify-backup-mount-contracts`, `verify-boot-selector-banks`, `verify-kernel-dtb`, `verify-storage-ram-budget`, `verify-cp-rtos`, `verify-p1-recovery-bridge`, `verify-stage-a-orchestrator`, `dry-run-candidate`).

## `U1..U5` Blueprint Unknowns Closure Summary Table

| Blueprint ID | Original Compatibility Unknown | Closure Module & Phase | Quantitative Proof & Enforced Safety Contract | Status |
| :---: | --- | --- | --- | :---: |
| **`U1`** | FX3 eMMC UDA total physical sector span vs FX6 `+76.50 MiB` (`0x35E000` vs `0x384400`) & write-protect state | `storage_and_ram_budget_verifier.py` (Phase 9) + `tier0_backup_worker.c` | Zero repartitioning required: `edisx_repartition_forbidden = True`, `sector0_mutation_bytes = 0`. `p20 -> p30` (`48.00 MiB` via `P1`, `+32.04 MiB` headroom for 16x `33^3` `.cube`), `p21 -> /tmp/opelog.vfat` (`8/16 MiB` loopback via `P2`), and FX6 `p15` (`361.24 MiB` raw / `425.19 MiB` ext2) fits FX3 stock `500.00 MiB` `p15` (`+138.76 MiB` raw / `+74.81 MiB` image headroom). Physical `/sys/block/nflasha/size` readback pinned in Tier-0 (`Gate G10`). | **CLOSED** (`edisx_repartition_forbidden=True`) |
| **`U2`** | FX6 `cpapp-b.bin` (`@ 0x00108000` CP RTOS) & `nflasha8` (`tomco.txt`) peripheral compatibility on FX3 mainboard | `cp_rtos_compatibility_verifier.py` (Phase 10) | FX3 & FX6 `tomco.txt` share **100% identical** 4x `memcfg=` pools (`1,724.00 MiB`, 0 overlap) & 20 IPC/telemetry keys, while FX6 `cpapp-b.bin` (`+1.88 MiB`) embeds **8 FX6-exclusive hardware hazards** (`Darwin` variable ND + `Mew` SDI/Genlock FPGA) & GPIO `0:22` reset flags. Enforces **Stage-A Stock-CP Redline (`p8_cp_mutation_forbidden = True`, `cp_mutation_bytes = 0`)**: stock FX3 `p8:/cpapp-b.bin` + AP `P1..P9 + Fan` achieves zero-brick-risk hybrid execution. | **CLOSED** (`u2_closed=True`) |
| **`U3`** | Per-body calibration files (`psd.bin`, `defdet.bin`, `lensfile.bin`, `p6:Jiritsu`) & `0xfa0080` Bank 0/1 DDR compatibility | `boot_selector_and_bank_verifier.py` (Phase 7) + `cp_rtos_compatibility_verifier.py` (Phase 10) | All 64-slot (`9,216 B`) `0xfa0080` Bank 0/1 maps have **0 bytes of pairwise DDR overlap**; Bank 0 shared AP slots have `0x0` shift; Bank 1 `+0xE0000` / `+0x14000` shifts exist solely for FX6's larger `cpapp-b.bin`. Under the Stock-CP Redline (`p8` & `p2:/Backup.bin` untouched + `P7` Sync100 + `P9` `upm.ko`), stock FX3 CP consumes its own native calibration formats at stock Bank 1 addresses. Same-body readback gated by Tier-0 (`G10`). | **CLOSED** (`u3_advanced=True` + Stock-CP) |
| **`U4`** | FX6 `appFw.so` / `libInfraSetupFile.so` / `libInfraKikiLogGenerator.so` behavior when `p20` or `p21` mount fails | `backup_mount_tolerance_verifier.py` (Phase 6) | Static instruction pinning + 6 Unicorn AArch64 runs prove `SetupFile::RcvThread` (`0x19650`) logs line `304` and enters `osal_rcv_msg_tmo(0x01de05a5)` without aborting, and `KikiLogGenerator_res_ope` (`0x3cb0`) returns cleanly on `EROFS != EEXIST` (`abort_or_fault = False`), while `P1` + `P2` provide `mount_rc = 0`. | **CLOSED** (`u4_closed=True`) |
| **`U5`** | `up.sh` / `ud_send_lsi.elf` (`queue 0x804b0376`) consumer & single-shot `p1` -> `p3` fallback guarantee | `boot_selector_and_bank_verifier.py` (Phase 7) + `p1_recovery_bridge_verifier.py` (Phase 11) | 10 Unicorn AArch64 cases on `ud_send_lsi.elf` (`0x400990`, 100% identical `PT_LOAD`) + `loader_nor.bin` (`0xFE049000`) + Phase 11 `fx3_recovery` `p1` FAT16/SquashFS/`p1chksum` bridge prove the 3-way boot arbitrator (Sub-LSI ANK latch + `p2:\updater\mode` -> `0xFE170028` + `BK4\0` `byte8 == 0x00`). Stage-A touches `0` bytes of `p1`/`p2`, and any `p1` exit enforces atomic 2-step reset (`rm -f /setting/updater/mode* && sync` + `ud_send_lsi.elf 0`). | **CLOSED** (`u5_closed=True` + `p1_recovery_bridge_ok=True`) |

## CLI & Unified Verification Commands

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

# 8. Verify Phase 9 30-partition zero-repartition topology, edisx.elf redline, p15 (/usr) footprint & CXD90057 DDR/tmpfs budget
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure verify-storage-ram-budget

# 9. Verify Phase 10 U2 CP RTOS (cpapp-b.bin @ 0x00108000), cross-model tomco.txt shared-memory/IPC & Stage-A Stock-CP Redline
PYTHONPATH=outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure verify-cp-rtos

# 10. Verify Phase 11 Cross-Package p1 Recovery & Tier-0 Bridge (fx3_recovery <-> fx3_safety <-> fx6_closure)
PYTHONPATH=outputs/fx3-recovery-adapter:outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure verify-p1-recovery-bridge

# 11. Verify Phase 12 nflasha3-initrd boot chain, WBI (p5) hibernation safety redline & 6-scenario POSIX /bin/sh Stage-A orchestrator
PYTHONPATH=outputs/fx3-recovery-adapter:outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure verify-stage-a-orchestrator

# 12. Assemble full P1..P9 + Fan + U1..U5 + DTB/.ko + Storage/RAM Budget + CP RTOS + p1 Bridge + Stage-A Orchestrator/WBI + CPIO candidate & evaluate all 12 safety gates
PYTHONPATH=outputs/fx3-recovery-adapter:outputs/fx3-safety:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m fx6_closure dry-run-candidate

# 13. Run Unified Lab Verification Runner across all 3 suites (58 + 17 + 56 = 131 tests) + BYOF manifest audit + clean-room binary/pyc audit
/usr/bin/python3 -B scripts/run_all_lab_tests.py
make test
make verify-byof
```
