# Phase 134 — `CXD90057` `IPL / BLoader / ATF BL31 / Kernel` Secure-Boot Chain-of-Trust Envelope Verifier, `nflasha1..nflasha20` `4 KiB / 512 KiB` Erase-Group Partition-Boundary Overlap Firewall, & 15-Pillar Recovery Master Suite

> **Date**: `2026-11-14` · **Phase**: `134`  
> **Primary Module**: [`outputs/fx3-recovery-adapter/fx3_recovery/secureboot_chain_and_partition_align_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/secureboot_chain_and_partition_align_verifier.py)  
> **Unit Tests**: [`outputs/fx3-recovery-adapter/tests/test_secureboot_chain_and_partition_align_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_secureboot_chain_and_partition_align_verifier.py) (`42` fast dual-mode tests)  
> **Safety Redlines**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `ALLOW_BOOT_PARTITION_TARGETING = False`, `ALLOW_DESTRUCTIVE_FASTBOOT = False`, `OTP_FUSE_TOUCHES = 0`, `OTP_FUSE_WRITES = 0`, `SPACC_KEY_READS = 0`, `PASSIVE_TX_BYTES_EMITTED = 0`, `PHYSICAL_DEVICE_WRITES = 0` (hard-locked)

---

## 1. Executive Summary (English)

Phase 134 adds Pillar 15 (`verify-secureboot-partalign` & `verify-all-recovery --with-phase134`) to the `fx3_recovery` suite for Sony `ILME-FX3` (`0x91030080` / `ALCIN_UUD`, `CXD90057`), achieving **15/15** green pillars in both `LOCAL_DONOR_O_RDONLY` and `CLEAN_ROOM_SYNTHETIC` modes:

| Pillar / Deliverable | Key Entrypoints | Core Invariants & Fail-Closed Gates |
| :--- | :--- | :--- |
| **0. Read-Only (`O_RDONLY`) FX3/FX6 Boot, Partition & Crypto Donor Inspection** | [`inspect_secureboot_and_partalign_donors_readonly`](../../outputs/fx3-recovery-adapter/fx3_recovery/secureboot_chain_and_partition_align_verifier.py) | Opens local FX3 `v7.02` (`loader_nor.bin` `101,888` B `4358c839...`, `partinf.conf` `3,999` B `3d96228d...` `LensData @ 0x0031C000`, `vmlinux.bin` `6,610,952` B `da4a66fa...`) and FX6 `v6.01` (`loader_nor.tar` -> `loader_nor.bin` `92,448` B `d91d21a8...`, `partinf.conf` `3,990` B `e05b53d1...` `LensData @ 0x00312000`, `vmlinux.bin` `6,610,952` B `bc4925e7...`) strictly via `os.O_RDONLY \| O_NOFOLLOW \| O_NONBLOCK`; verifies boot/partition/`SPAcc`/`eFuse`/`OTP`/`PSCI`/`SMC` symbol anchors and cross-SKU divergence with zero raw firmware bytes or hardware keys emitted, falling back deterministically to `CLEAN_ROOM_SYNTHETIC` when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor files are absent. |
| **Pillar A — `CXD90057` `IPL -> BLoader -> BL31 -> Kernel` Secure-Boot Envelope & Cross-SKU Signature Mismatch Firewall** | [`verify_cxd90057_secureboot_envelope`](../../outputs/fx3-recovery-adapter/fx3_recovery/secureboot_chain_and_partition_align_verifier.py), [`audit_otp_efuse_and_spacc_operation`](../../outputs/fx3-recovery-adapter/fx3_recovery/secureboot_chain_and_partition_align_verifier.py), [`run_secureboot_envelope_6_scenario_firewall`](../../outputs/fx3-recovery-adapter/fx3_recovery/secureboot_chain_and_partition_align_verifier.py) | Models signed stage envelopes (monotonic epoch, payload vs partition capacity, RSA/ECDSA signature-block structure without reading keys, `Model ID` `0x91030080` FX3 vs `0x91040086` FX6 SKU check) and enforces fail-closed: `BLOCKED_UNSIGNED_OR_PATCHED_BOOT_STAGE_ON_LOCKED_SOC` (whereas Stage-B volatile `QEMU` / post-kernel userland bind-mount leaves signed boot stages untouched and passes), `BLOCKED_CROSS_SKU_FX6_BOOTLOADER_ON_FX3_SOC`, and `BLOCKED_OTP_EFUSE_OR_SPACC_KEYSLOT_ACCESS` (`6/6` scenarios green, `otp_fuse_writes == 0`, `spacc_key_reads == 0`). |
| **Pillar B — `nflasha1..nflasha20` `eMMC` `512 B / 4 KiB / 512 KiB` Erase-Group Interval Tree & Bleed Firewall** | [`LbaIntervalTree`](../../outputs/fx3-recovery-adapter/fx3_recovery/secureboot_chain_and_partition_align_verifier.py), [`find_partition_lba_overlaps`](../../outputs/fx3-recovery-adapter/fx3_recovery/secureboot_chain_and_partition_align_verifier.py), [`verify_partition_map_and_flash_ops`](../../outputs/fx3-recovery-adapter/fx3_recovery/secureboot_chain_and_partition_align_verifier.py), [`run_partition_align_6_scenario_firewall`](../../outputs/fx3-recovery-adapter/fx3_recovery/secureboot_chain_and_partition_align_verifier.py) | Deterministic interval-tree verifier (`erase_group_lba_multiple = 1024` sectors = `512 KiB`) across `nflasha1..nflasha20` + `BOOT0`/`BOOT1`/`RPMB` catching `PARTITION_LBA_OVERLAP_DETECTED` across overlapping partitions, `UNALIGNED_ERASE_GROUP_BLEED_HAZARD` on off-by-one `dd seek=` / non-`512 KiB` `TRIM/ERASE` or sector-count overflow bleeding into neighbor `nvs`/`cnflasha` partitions, and `PROTECTED_PARTITION_WRITE_ATTEMPT_BLOCKED` on `BOOT0`, `BOOT1`, `RPMB`, `nvs`, `adj`, `cnflasha` (`6/6` scenarios green). |
| **Pillar C — 15-Pillar Recovery Master Suite & 42 Dual-Mode Unit Tests** | [`fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py), [`fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py), [`test_secureboot_chain_and_partition_align_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_secureboot_chain_and_partition_align_verifier.py) | Registers `verify-secureboot-partalign [--clean-room] [--json] [--out ...]` and opt-in `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124 --with-phase126 --with-phase134` (**15/15** green in both modes while preserving default `7/7` behavior), exports all Phase 134 symbols in `__all__`, and passes `42` fast dual-mode tests (`>= 15` pillar assertions). |

---

## 2. 中文摘要 (Chinese Summary)

Phase 134 在严格只读、零持久写入、零密钥读取红线（`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`ALLOW_BOOT_PARTITION_TARGETING = False`、`ALLOW_DESTRUCTIVE_FASTBOOT = False`、`OTP_FUSE_TOUCHES = 0`、`OTP_FUSE_WRITES = 0`、`SPACC_KEY_READS = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`）下，为 Sony `ILME-FX3`（`0x91030080` / `ALCIN_UUD`，`CXD90057`）交付 `CXD90057` 安全启动信任链信封校验、分区 `512 KiB` 擦除组边界与邻分区串写防火墙，并接入 **15 支柱**恢复总检门禁：

1. **供体只读（`os.O_RDONLY`）检查与确定性净室回退**：严格经 `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 核验本地 FX3 `v7.02`（`loader_nor.bin` `101,888 B`、`partinf.conf` `3,999 B` `LensData @ 0x0031C000`、`vmlinux.bin` `6,610,952 B`）与 FX6 `v6.01`（`loader_nor.tar` 内含 `92,448 B` `loader_nor.bin`、`partinf.conf` `3,990 B` `LensData @ 0x00312000`、`vmlinux.bin` `6,610,952 B`）符号锚点与跨机型隔离摘要，零原始固件字节或硬件私钥输出；`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺失时确定性回退至 `CLEAN_ROOM_SYNTHETIC`。
2. **支柱 A — `CXD90057` `IPL -> BLoader -> BL31 -> Kernel` 安全启动信封与跨机型防火墙**：fail-closed 拦截锁定 SoC 上的未签名/改写摘要/容量溢出/代次回滚引导阶段（`BLOCKED_UNSIGNED_OR_PATCHED_BOOT_STAGE_ON_LOCKED_SOC`，同时放行不触碰已签名引导阶段的 Stage-B `QEMU` / 用户态 bind-mount 易失覆盖）、跨机型 FX6 引导/PMIC 镜像（`BLOCKED_CROSS_SKU_FX6_BOOTLOADER_ON_FX3_SOC`）及 `eFuse/OTP` 烧断或 `SPAcc` 密钥槽转储请求（`BLOCKED_OTP_EFUSE_OR_SPACC_KEYSLOT_ACCESS`，`6/6` 场景全绿，`otp_fuse_writes == 0`、`spacc_key_reads == 0`）。
3. **支柱 B — `nflasha1..nflasha20` `eMMC` `512 B / 4 KiB / 512 KiB` 擦除组边界与邻分区串写防火墙**：基于增强区间树（`LbaIntervalTree`，`erase_group_lba_multiple = 1024` 扇区 = `512 KiB`）捕获分区重叠（`PARTITION_LBA_OVERLAP_DETECTED`）、差一 `dd seek=` / 非 `512 KiB` 对齐擦除或越界串写邻近 `nvs`/`cnflasha` 校准分区（`UNALIGNED_ERASE_GROUP_BLEED_HAZARD`）以及对 `BOOT0`/`BOOT1`/`RPMB`/`nvs`/`adj`/`cnflasha` 的写入/擦除尝试（`PROTECTED_PARTITION_WRITE_ATTEMPT_BLOCKED`，`6/6` 场景全绿）。
4. **支柱 C — CLI 与 15 支柱恢复总检集成**：注册 `verify-secureboot-partalign` 与 `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124 --with-phase126 --with-phase134`（双模式下均达成 **15/15** 绿色通过，无标志默认仍保持 `7/7` 向后兼容）。

---

## 3. Owned Files (Strict 6-File Scope)

1. [`outputs/fx3-recovery-adapter/fx3_recovery/secureboot_chain_and_partition_align_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/secureboot_chain_and_partition_align_verifier.py) *(NEW)*
2. [`outputs/fx3-recovery-adapter/fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) *(UPDATED — Phase 134 symbol exports)*
3. [`outputs/fx3-recovery-adapter/fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py) *(UPDATED — `verify-secureboot-partalign` & `verify-all-recovery --with-phase134`)*
4. [`outputs/fx3-recovery-adapter/README.md`](../../outputs/fx3-recovery-adapter/README.md) *(UPDATED — Phase 134 15th pillar documentation)*
5. [`outputs/fx3-recovery-adapter/tests/test_secureboot_chain_and_partition_align_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_secureboot_chain_and_partition_align_verifier.py) *(NEW — 42 fast dual-mode unit tests)*
6. [`reports/2026-11-14-phase134-secureboot-chain-partalign-recovery/README.md`](README.md) *(NEW — this bilingual report)*

---

## 4. Verification Commands & Observed Results

- **Phase 134 Unit Tests (`test_secureboot_chain_and_partition_align_verifier.py`, 42 tests)**:
  - Local Donor mode (`os.O_RDONLY`): **42 tests** in **2.221s** (`OK`).
  - Clean-Room mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **42 tests** in **1.811s** (`OK`).
- **Full `outputs/fx3-recovery-adapter/tests` Suite**:
  - Local Donor mode (`os.O_RDONLY`): **639 tests** in **47.063s** (`OK`, `skipped=1`).
  - Clean-Room mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **581 tests** in **17.922s** (`OK`, `skipped=9`).
- **CLI Entrypoint Verification (`verify-secureboot-partalign` & `verify-all-recovery --with-phase94 ... --with-phase134`)**:
  - Local Donor `verify-secureboot-partalign --json`: `exit 0` (`status=VERIFIED_SECUREBOOT_CHAIN_AND_PARTALIGN_GATE`, `verification_mode=LOCAL_DONOR_O_RDONLY`, `all_passed=True`, `secureboot=6/6`, `partalign=6/6`, `suite_sha256=fd275cf1131bda8b...`).
  - Clean-Room `verify-secureboot-partalign --json` (`FX3_FX6_FORCE_CLEAN_ROOM=1`): `exit 0` (`status=VERIFIED_SECUREBOOT_CHAIN_AND_PARTALIGN_GATE`, `verification_mode=CLEAN_ROOM_SYNTHETIC`, `all_passed=True`, `secureboot=6/6`, `partalign=6/6`, `suite_sha256=d829ba840d0fe62d...`).
  - Local Donor `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124 --with-phase126 --with-phase134 --json`: `exit 0` (`status=VERIFIED_RECOVERY_MASTER_SUITE`, `verification_mode=LOCAL_DONOR_O_RDONLY`, `all_passed=True`, `pillars=15/15`, `recovery_master_sha256=0630b15eeaff85be...`).
  - Clean-Room `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124 --with-phase126 --with-phase134 --json`: `exit 0` (`status=VERIFIED_RECOVERY_MASTER_SUITE`, `verification_mode=CLEAN_ROOM_SYNTHETIC`, `all_passed=True`, `pillars=15/15`, `recovery_master_sha256=07b2c16ad97e1ac5...`).
- **Clean-Room Lab Master Gate & JSON Regex Hygiene**:
  - `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` -> `[hygiene] git status --porcelain binary/pyc audit: CLEAN` (`ALL GREEN in 0.06s`).
  - Regex `r'(?<![0-9A-Za-z_/.-])b[\'\"]'` across JSON outputs in both modes -> `0` matches (`CLEAN`).
