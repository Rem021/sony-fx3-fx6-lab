# Phase 124 — CXD90057 Mask-BootROM USB Cold-Plug Recovery Enumeration Verifier, JEDEC eMMC BOOT0/BOOT1 Hardware Boot-Partition (`EXT_CSD[179]` `PART_CONFIG` & `EXT_CSD[177]` `BOOT_BUS_CONDITIONS`) Anti-Corruption Triage, & 13-Pillar Recovery Master Suite

> **Date**: `2026-11-14` · **Phase**: `124`  
> **Primary Module**: [`outputs/fx3-recovery-adapter/fx3_recovery/bootrom_usb_and_emmc_bootpart_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/bootrom_usb_and_emmc_bootpart_verifier.py)  
> **Unit Tests**: [`outputs/fx3-recovery-adapter/tests/test_bootrom_usb_and_emmc_bootpart_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_bootrom_usb_and_emmc_bootpart_verifier.py) (`40` fast dual-mode tests)  
> **Safety Redlines**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `ALLOW_BOOT_PARTITION_TARGETING = False`, `ALLOW_DESTRUCTIVE_FASTBOOT = False`, `OTP_FUSE_TOUCHES = 0`, `PASSIVE_TX_BYTES_EMITTED = 0`, `PHYSICAL_DEVICE_WRITES = 0`, `EMMC_PERSISTENT_PROGRAM_COMMANDS = 0` (hard-locked)

---

## 1. Executive Summary (English)

Phase 124 adds Pillar 13 (`verify-bootrom-bootpart` & `verify-all-recovery --with-phase124`) to the `fx3_recovery` suite for Sony `ILME-FX3` (`0x91030080` / `ALCIN_UUD`, `CXD90057`), achieving **13/13** green pillars in both `LOCAL_DONOR_O_RDONLY` and `CLEAN_ROOM_SYNTHETIC` modes:

| Pillar / Deliverable | Key Entrypoints | Core Invariants & Fail-Closed Gates |
| :--- | :--- | :--- |
| **0. Read-Only (`O_RDONLY`) FX3/FX6 Bootloader & Partition-Config Donor Inspection** | [`inspect_bootrom_and_bootpart_donors_readonly`](../../outputs/fx3-recovery-adapter/fx3_recovery/bootrom_usb_and_emmc_bootpart_verifier.py) | Opens local FX3 `v7.02` (`loader_nor.bin` `101,888` B `4358c839...`, `pformat_config.txt` `1,274` B `21cd5b29...` `awake_memaddr=0xFE040800`/`load=0xFE049000`, `loader_nor.tar` `112,640` B `913d1a32...`, `partinf.conf` `3,999` B `3d96228d...`) and FX6 `v6.01` (`loader_nor.tar` `102,400` B `67e7b9cd...` containing internal `loader_nor.bin` `92,448` B `d91d21a8...`, `partinf.conf` `3,990` B `e05b53d1...`) strictly via `os.O_RDONLY \| O_NOFOLLOW \| O_NONBLOCK`; verifies cross-SKU separation and deterministically falls back to `CLEAN_ROOM_SYNTHETIC` when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor paths are absent. |
| **Pillar A — JEDEC `eMMC 5.1` `BOOT0 / BOOT1` Hardware Boot-Partition & `EXT_CSD` Triage** | [`parse_ext_csd_boot_config`](../../outputs/fx3-recovery-adapter/fx3_recovery/bootrom_usb_and_emmc_bootpart_verifier.py), [`audit_boot_wp_script_or_profile`](../../outputs/fx3-recovery-adapter/fx3_recovery/bootrom_usb_and_emmc_bootpart_verifier.py), [`triage_emmc_boot_partitions_and_ext_csd`](../../outputs/fx3-recovery-adapter/fx3_recovery/bootrom_usb_and_emmc_bootpart_verifier.py), [`run_emmc_bootpart_6_scenario_triage`](../../outputs/fx3-recovery-adapter/fx3_recovery/bootrom_usb_and_emmc_bootpart_verifier.py) | Models 512B `EXT_CSD` boot configuration (`EXT_CSD[179]` `PART_CONFIG`, `EXT_CSD[177]` `BOOT_BUS_CONDITIONS`, `EXT_CSD[173]` `BOOT_WP`, `EXT_CSD[226]` `BOOT_SIZE_MULT == 32` for `4 MiB` `BOOT0`/`BOOT1`) and detects fail-closed: `BOOT_PART_DISABLED_DEAD_BOOT_TRAP` (`BOOT_PARTITION_ENABLE == 0x0` or `0x7` UDA mismatch or reserved `0x3..0x6`), `BOOT0_CORRUPTED_FAILOVER_TO_BOOT1_AVAILABLE` (`BOOT0` SHA-256/header mismatch while redundant `BOOT1` is intact), `BLOCKED_PERMANENT_BOOT_WP_FUSE_HAZARD` (any profile or command attempting `EXT_CSD[173]` `B_PERM_WP_EN` `bit 2` or `bit 6`), `PARTITION_ACCESS_NONZERO_LEAK` (`PART_CONFIG[2:0] != 0`), plus dual-slot corruption escalation to Mask-BootROM fallback (`6/6` scenarios green, `physical_device_writes == 0`). |
| **Pillar B — `CXD90057` Mask-BootROM USB `0x054C` Cold-Plug Enumeration & `RAM_LOAD_ONLY` Sandbox** | [`verify_bootrom_usb_coldplug_and_ram_sandbox`](../../outputs/fx3-recovery-adapter/fx3_recovery/bootrom_usb_and_emmc_bootpart_verifier.py), [`run_bootrom_usb_5_scenario_sandbox`](../../outputs/fx3-recovery-adapter/fx3_recovery/bootrom_usb_and_emmc_bootpart_verifier.py) | Validates Sony `USB VID 0x054C` (`PID 0x0C90/0x0336/0x0DA1`) cold-plug descriptor and bulk IN/OUT endpoints under legitimate recovery triggers, enforces strictly `RAM_LOAD_ONLY` execution inside CXD90057 SRAM (`0xFE040000..0xFE100000`) or DRAM (`0x40000000..0xC0000000`), and blocks non-Sony VIDs, cross-SKU FX6 payloads, non-RAM target modes, and persistent eMMC/NOR/OTP program commands (`emmc_persistent_program_commands == 0`, `5/5` scenarios green). |
| **Pillar C — 13-Pillar Recovery Master Suite & 40 Dual-Mode Unit Tests** | [`fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py), [`fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py), [`test_bootrom_usb_and_emmc_bootpart_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_bootrom_usb_and_emmc_bootpart_verifier.py) | Registers `verify-bootrom-bootpart [--clean-room] [--json] [--out ...]` and opt-in `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124` (`13/13` green in both modes while preserving default `7/7` behavior), exports all Phase 124 symbols in `__all__`, and passes `40` fast dual-mode tests (`>= 13` pillar assertions). |

---

## 2. 中文摘要 (Chinese Summary)

Phase 124 在严格只读、纯内存（RAM-only）安全红线（`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`ALLOW_BOOT_PARTITION_TARGETING = False`、`ALLOW_DESTRUCTIVE_FASTBOOT = False`、`OTP_FUSE_TOUCHES = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`EMMC_PERSISTENT_PROGRAM_COMMANDS = 0`）下，为 Sony `ILME-FX3`（`0x91030080` / `ALCIN_UUD`，`CXD90057`）交付 Mask-BootROM USB 冷插拔与 JEDEC eMMC `BOOT0/BOOT1` 防损坏分诊支柱并接入 **13 支柱**恢复总检门禁：

1. **供体只读（`os.O_RDONLY`）检查与确定性净室回退**：严格以 `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 读取本地 FX3 `v7.02`（`loader_nor.bin` `101,888 B` SRAM `0xFE049000`、`pformat_config.txt` `awake_memaddr=0xFE040800`、`loader_nor.tar`、`partinf.conf`）与 FX6 `v6.01`（`loader_nor.tar` 内含 `92,448 B` `loader_nor.bin`、`partinf.conf`）并校验跨机型隔离；当 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体文件缺失时确定性回退至 `CLEAN_ROOM_SYNTHETIC`。
2. **支柱 A — JEDEC `eMMC 5.1` `BOOT0 / BOOT1` 硬件引导分区与 `EXT_CSD` 配置分诊**：建模 `CXD90057` 一级引导程序驻留的 `4 MiB` `BOOT0` 与冗余 `4 MiB` `BOOT1` 分区、校验 `EXT_CSD[179]`（`PART_CONFIG`）、`EXT_CSD[177]`（`BOOT_BUS_CONDITIONS`）、`EXT_CSD[173]`（`BOOT_WP`）及 `EXT_CSD[226]`（`4 MiB`），精准检出 `BOOT_PART_DISABLED_DEAD_BOOT_TRAP`（`BOOT_PARTITION_ENABLE == 0x0` 或 `0x7`）、`BOOT0_CORRUPTED_FAILOVER_TO_BOOT1_AVAILABLE`（主 `BOOT0` 损坏而冗余 `BOOT1` 完好）、`BLOCKED_PERMANENT_BOOT_WP_FUSE_HAZARD`（任何试图置位永久写保护 `EXT_CSD[173]` `B_PERM_WP_EN` `bit 2` 或 `bit 6` 的配置或命令）与 `PARTITION_ACCESS_NONZERO_LEAK`（`PART_CONFIG[2:0] != 0` 泄漏），并在双分区损坏时自动分诊升级至 Mask-BootROM。
3. **支柱 B — `CXD90057` Mask-BootROM USB `0x054C` 冷插拔枚举与 `RAM_LOAD_ONLY` 沙盒校验**：建模 `USB VID 0x054C`（`PID 0x0C90/0x0336/0x0DA1`）冷插拔描述符与 Bulk IN/OUT 端点握手，强制校验恢复载荷仅能定址 CXD90057 SRAM（`0xFE040000..0xFE100000`）/DRAM（`0x40000000..0xC0000000`）原地执行（`RAM_LOAD_ONLY`），100% 阻断任何跨机型 FX6 载荷、非 Sony VID 与持久 eMMC/NOR/OTP 刷写命令（`emmc_persistent_program_commands == 0`）。
4. **支柱 C — CLI 与 13 支柱恢复总检集成**：注册 `verify-bootrom-bootpart` 与 `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124`（双模式下均达成 **13/13** 绿色通过，无参数默认仍保持 `7/7` 向后兼容）。

---

## 3. Owned Files (Strict 6-File Scope)

1. [`outputs/fx3-recovery-adapter/fx3_recovery/bootrom_usb_and_emmc_bootpart_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/bootrom_usb_and_emmc_bootpart_verifier.py) *(NEW)*
2. [`outputs/fx3-recovery-adapter/fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) *(UPDATED — Phase 124 symbol exports)*
3. [`outputs/fx3-recovery-adapter/fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py) *(UPDATED — `verify-bootrom-bootpart` & `verify-all-recovery --with-phase124`)*
4. [`outputs/fx3-recovery-adapter/README.md`](../../outputs/fx3-recovery-adapter/README.md) *(UPDATED — Phase 124 13th pillar documentation)*
5. [`outputs/fx3-recovery-adapter/tests/test_bootrom_usb_and_emmc_bootpart_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_bootrom_usb_and_emmc_bootpart_verifier.py) *(NEW — 40 fast dual-mode unit tests)*
6. [`reports/2026-11-14-phase124-bootrom-usb-emmc-bootpart-recovery/README.md`](README.md) *(NEW — this bilingual report)*

---

## 4. Verification Commands & Observed Results

- **Phase 124 Unit Tests (`test_bootrom_usb_and_emmc_bootpart_verifier.py`, 40 tests)**:
  - Local Donor mode (`os.O_RDONLY`): **40 tests** in **1.752s** (`OK`).
  - Clean-Room mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **40 tests** in **1.312s** (`OK`).
- **Full `outputs/fx3-recovery-adapter/tests` Suite**:
  - Local Donor mode (`os.O_RDONLY`): **557 tests** in **42.084s** (`OK`, `skipped=1`).
  - Clean-Room mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **499 tests** in **9.902s** (`OK`, `skipped=9`).
- **CLI Entrypoint Verification (`verify-bootrom-bootpart` & `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124`)**:
  - Local Donor `verify-bootrom-bootpart --json`: `exit 0` (`status=VERIFIED_BOOTROM_USB_AND_EMMC_BOOTPART_GATE`, `verification_mode=LOCAL_DONOR_O_RDONLY`, `all_passed=True`, `bootpart=6/6`, `bootrom=5/5`, `emmc_persistent_program_commands=0`, `suite_sha256=cee42099f9aece6b...`).
  - Clean-Room `verify-bootrom-bootpart --json` (`FX3_FX6_FORCE_CLEAN_ROOM=1`): `exit 0` (`status=VERIFIED_BOOTROM_USB_AND_EMMC_BOOTPART_GATE`, `verification_mode=CLEAN_ROOM_SYNTHETIC`, `all_passed=True`, `bootpart=6/6`, `bootrom=5/5`, `emmc_persistent_program_commands=0`, `suite_sha256=eb51c0cc85dc7da9...`).
  - Local Donor `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124 --json`: `exit 0` (`status=VERIFIED_RECOVERY_MASTER_SUITE`, `all_passed=True`, `pillars=13/13`, `recovery_master_sha256=0630b15eeaff85be...`).
  - Clean-Room `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124 --json`: `exit 0` (`status=VERIFIED_RECOVERY_MASTER_SUITE`, `all_passed=True`, `pillars=13/13`, `recovery_master_sha256=07b2c16ad97e1ac5...`).
- **Clean-Room Lab Master Gate & JSON Regex Hygiene**:
  - `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` -> `[hygiene] git status --porcelain binary/pyc audit: CLEAN` (`ALL GREEN in 0.05s`).
  - Regex `r'(?<![0-9A-Za-z_/.-])b[\x27"]'` across JSON outputs in both modes -> `0` matches (`CLEAN`).
