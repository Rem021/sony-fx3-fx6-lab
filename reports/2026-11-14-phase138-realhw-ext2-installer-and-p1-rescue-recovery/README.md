# Phase 138 — Reversible A7C-II-Style `/dev/nflasha15` (`ext2` `/usr`) File-Level Atomic Stage-B Installer Dry-Run, Hash-Rollback Engine & `p1` Single-Shot Emergency Rescue Verifier (`outputs/fx3-recovery-adapter/`, Pillar 16)

> **Date**: `2026-11-14` · **Phase**: `138`  
> **Primary Module**: [`outputs/fx3-recovery-adapter/fx3_recovery/realhw_ext2_installer_and_p1_rescue_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_ext2_installer_and_p1_rescue_verifier.py)  
> **Unit Tests**: [`outputs/fx3-recovery-adapter/tests/test_realhw_ext2_installer_and_p1_rescue_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_realhw_ext2_installer_and_p1_rescue_verifier.py) (`44` fast dual-mode tests)  
> **Safety Redlines**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `ALLOW_BOOT_PARTITION_TARGETING = False`, `ALLOW_DESTRUCTIVE_FASTBOOT = False`, `OTP_FUSE_TOUCHES = 0`, `OTP_FUSE_WRITES = 0`, `PASSIVE_TX_BYTES_EMITTED = 0`, `PHYSICAL_DEVICE_WRITES = 0` (hard-locked)

---

## 1. Executive Summary (English)

Phase 138 adds **Pillar 16** (`verify-realhw-ext2-installer` & `verify-all-recovery --with-phase138`) to `fx3_recovery` on top of `codex/fx6-system-port-research` (`3944fea8`, preserving all 15 prior pillars), delivering real-hardware readiness dry-run verification for an A7C-II-style reversible file-level `/dev/nflasha15` (`ext2` `/usr`) Stage-B installer and a `p1`/`p3` mutually-exclusive single-shot emergency rescue workflow — achieving **16/16** green recovery pillars in both `LOCAL_DONOR_O_RDONLY` and `CLEAN_ROOM_SYNTHETIC` modes with zero physical device writes:

| Pillar / Deliverable | Key Entrypoints | Core Invariants & Fail-Closed Gates |
| :--- | :--- | :--- |
| **0. Read-Only (`O_RDONLY`) FX3/FX6 Donor & `ext2` Superblock Inspection** | [`inspect_realhw_ext2_and_p1_donors_readonly`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_ext2_installer_and_p1_rescue_verifier.py), [`parse_ext2_superblock_bytes`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_ext2_installer_and_p1_rescue_verifier.py) | Inspects 12 local FX3 `v7.02` & FX6 `v6.01` donor artifacts strictly via `os.O_RDONLY \| O_NOFOLLOW \| O_NONBLOCK` (`fx3_p15_bytes = 479,846,400`, `s_magic == 0xef53`, `fx3_p15_free_inodes = 116,467`, `fx3_p15_effective_headroom_bytes = 68,433,920` >= `32 MiB`; `fx6_p15_bytes = 445,843,456`, `fx6_p15_effective_headroom_bytes = 112,722,944`; `fx3_im_elf_sha256 = 5171f576d8b7...`, `fx6_im_elf_sha256 = 87d672bd6abb...`, `fx3_p2_cfg_uart = 1` vs `fx6_p1_cfg_uart = 9`, `cross_sku_distinct = True`). Deterministic clean-room fallback (`FX3_FX6_FORCE_CLEAN_ROOM=1`) emits zero raw proprietary firmware bytes (`snapshot_sha256 = 783ee93969b7...`). |
| **Pillar A (`EXT2_NFLASHA15_ATOMIC_INSTALLER_AND_ROLLBACK`)** | [`InMemoryExt2Filesystem`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_ext2_installer_and_p1_rescue_verifier.py), [`audit_crypto_block_device_path`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_ext2_installer_and_p1_rescue_verifier.py), [`validate_sd_escape_hatch_wrapper`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_ext2_installer_and_p1_rescue_verifier.py), [`simulate_atomic_ext2_install_and_rollback`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_ext2_installer_and_p1_rescue_verifier.py), [`run_ext2_atomic_installer_6_scenario_suite`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_ext2_installer_and_p1_rescue_verifier.py) | Enforces transparent crypto block-device routing (`/dev/nflasha15` / `/dev/cnflasha15`), **hard-blocks** raw plaintext `/dev/pnflasha15` writes (`BLOCKED_RAW_PNFLASHA_PLAINTEXT_WRITE`), enforces SD escape-hatch wrapper (`if [ ! -f /mnt/sd/FX6_STAGEB_BOOT.MANIFEST ]; then exec /usr/bin/im.elf.orig "$@"; fi`), and simulates full `remount rw -> verify stock SHA-256 -> save .orig -> write wrapper + hook -> read-back SHA-256 verify -> rollback on bit-flip/short-write -> remount ro`, proving 100% byte-identical stock restoration (`6/6` scenarios green). |
| **Pillar B (`P1_P3_MUTUAL_EXCLUSION_AND_ONESHOT_RESCUE_INITRD`)** | [`audit_p1_p3_mutual_exclusion`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_ext2_installer_and_p1_rescue_verifier.py), [`audit_p1_oneshot_rescue_proposal`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_ext2_installer_and_p1_rescue_verifier.py), [`run_p1_rescue_and_mutual_exclusion_6_scenario_suite`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_ext2_installer_and_p1_rescue_verifier.py) | Enforces the **Golden Mutual-Exclusion Law** (never modify `p1` and `p3` in the same transaction so at least one bootable bank remains untouched), verifies `p1:/dat2 == "91030080"` and `p1:/dat3` preservation, `p1:/boot/kemco.txt` enforcing `cfg.uart=1` & `console=ttyAMA0,460800n8` (hard-blocking FX6 `cfg.uart=9` blind UART blackout), and `/sbin/init` line-1 `rm -f /setting/updater/mode* && sync` (`6/6` scenarios green). |
| **Pillar C (`TIER0_PRECONDITION_AND_HARDWARE_WRITE_LOCK`)** | [`verify_tier0_backup_precondition`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_ext2_installer_and_p1_rescue_verifier.py), [`run_tier0_precondition_and_lock_4_scenario_suite`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_ext2_installer_and_p1_rescue_verifier.py), [`run_realhw_ext2_installer_and_p1_rescue_suite`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_ext2_installer_and_p1_rescue_verifier.py) | Requires a verified 7-artifact Tier-0 backup receipt (`Sector 0`, `p1`, `p2`, `p6`, `p12`, `p18`, SPI NOR `ddrtraining.dat`) before even dry-run readiness passes, while keeping `persistent_emmc_writes_authorized = False` hard-locked (`4/4` scenarios green). |
| **16-Pillar Recovery Master Suite & 44 Dual-Mode Unit Tests** | [`fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py), [`fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py), [`test_realhw_ext2_installer_and_p1_rescue_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_realhw_ext2_installer_and_p1_rescue_verifier.py) | Registers `verify-realhw-ext2-installer [--clean-room] [--json] [--out ...]` and opt-in `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124 --with-phase126 --with-phase134 --with-phase138` (**16/16** green in both modes while preserving default `7/7` and `--with-phase134` `15/15` callers), exports all Phase 138 symbols in `__all__`, and passes `44` fast dual-mode tests. |

---

## 2. 中文摘要 (Chinese Summary)

Phase 138 在严格零持久写入、零物理设备操作红线（`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`ALLOW_BOOT_PARTITION_TARGETING = False`、`ALLOW_DESTRUCTIVE_FASTBOOT = False`、`OTP_FUSE_TOUCHES = 0`、`OTP_FUSE_WRITES = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`）下，基于 `codex/fx6-system-port-research`（`3944fea8`）接入第 **16** 根恢复支柱，针对真实 `ILME-FX3`（`7.02`，`0x91030080`）验证 A7C-II 风格可逆 `/dev/nflasha15`（`ext2` `/usr`）文件级原子安装干跑、哈希回滚与 `p1`/`p3` 互斥单次应急救援门禁：

1. **供体只读（`os.O_RDONLY`）检查与确定性净室回退**：通过 `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 核验 12 项本地 FX3 `7.02` 与 FX6 `6.01` 供体元数据（FX3 `nflasha15` `479,846,400 B`、`s_magic == 0xef53`、可用 inode `116,467`、有效余量 `68,433,920 B >= 32 MiB`；FX6 `nflasha15` `445,843,456 B`、有效余量 `112,722,944 B`；`fx3_p2_cfg_uart = 1` 对比 `fx6_p1_cfg_uart = 9`，`cross_sku_distinct = True`）；`FX3_FX6_FORCE_CLEAN_ROOM=1` 下与本地读取 12/12 完全一致（`diffs: []`），JSON 输出零原始固件字节。
2. **支柱 A — `EXT2_NFLASHA15_ATOMIC_INSTALLER_AND_ROLLBACK`（`6/6`）**：强制通过 `/dev/nflasha15` / `/dev/cnflasha15` 透明加密通道操作，**硬拦截** `/dev/pnflasha15` 原始明文写入破坏风险；强制 `/mnt/sd/FX6_STAGEB_BOOT.MANIFEST` SD 卡逃生开关包装器（缺失时直通 `exec /usr/bin/im.elf.orig "$@"`）；在纯内存 `InMemoryExt2Filesystem` 中完整演练 `remount rw -> stock SHA-256 校验 -> .orig 备份 -> 写入脚本/载荷 -> 全量回读校验 -> 注入位翻转/短写触发自动回滚 -> remount ro`，证明 100% 字节级还原至出厂 SHA-256。
3. **支柱 B — `P1_P3_MUTUAL_EXCLUSION_AND_ONESHOT_RESCUE_INITRD`（`6/6`）**：强制执行 **`p1`/`p3` 黄金互斥律**（同一事务绝不同时修改 `p1` 与 `p3`，保证至少一个可启动分区完好）；核验 `p1` 单次诊断配置保留 `p1:/dat2 == "91030080"` 与 `p1:/dat3`、`p1:/boot/kemco.txt` 强制 `cfg.uart=1` 与 `console=ttyAMA0,460800n8`（拦截 FX6 `cfg.uart=9` 串口失明风险）及 `/sbin/init` 首行 `rm -f /setting/updater/mode* && sync`。
4. **支柱 C — `TIER0_PRECONDITION_AND_HARDWARE_WRITE_LOCK`（`4/4`）与 16 支柱总检集成**：要求 Tier-0 七件套备份回执（`Sector 0`、`p1`、`p2`、`p6`、`p12`、`p18`、SPI NOR `ddrtraining.dat`）校验通过后才允许干跑通过，同时 `persistent_emmc_writes_authorized = False` 保持硬锁；注册 `verify-realhw-ext2-installer` 与 `verify-all-recovery --with-phase138`（双模式均达 **16/16** 全绿，且不破坏既有 `7/7` 与 `--with-phase134` `15/15` 调用方）。

---

## 3. Owned Files (Strict 6-File Scope)

1. [`outputs/fx3-recovery-adapter/fx3_recovery/realhw_ext2_installer_and_p1_rescue_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_ext2_installer_and_p1_rescue_verifier.py) *(NEW — Pillar 16)*
2. [`outputs/fx3-recovery-adapter/fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) *(UPDATED — Phase 138 symbol exports)*
3. [`outputs/fx3-recovery-adapter/fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py) *(UPDATED — `verify-realhw-ext2-installer` & `verify-all-recovery --with-phase138`)*
4. [`outputs/fx3-recovery-adapter/README.md`](../../outputs/fx3-recovery-adapter/README.md) *(UPDATED — Phase 138 Pillar 16 documentation)*
5. [`outputs/fx3-recovery-adapter/tests/test_realhw_ext2_installer_and_p1_rescue_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_realhw_ext2_installer_and_p1_rescue_verifier.py) *(NEW — 44 dual-mode unit tests)*
6. [`reports/2026-11-14-phase138-realhw-ext2-installer-and-p1-rescue-recovery/README.md`](README.md) *(NEW — this bilingual report)*

---

## 4. Verification Commands & Observed Results

- **Phase 138 Unit Tests (`test_realhw_ext2_installer_and_p1_rescue_verifier.py`, 44 dual-mode tests)**:
  - Normal (`LOCAL_DONOR_O_RDONLY`) + Clean-Room (`FX3_FX6_FORCE_CLEAN_ROOM=1`) back-to-back: **44 tests** in **7.402s** (`OK`).
- **Full `outputs/fx3-recovery-adapter/tests` Suite**:
  - Local Donor mode (`os.O_RDONLY`): **683 tests** in **48.744s** (`OK`, `skipped=1`).
  - Clean-Room mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **625 tests** in **16.750s** (`OK`, `skipped=9`).
- **Phase 130 Milestone Master Gate (`outputs/fx6-on-fx3-closure/tests`, `test_phase130_*.py`)**:
  - `PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -p "test_phase130_*.py"`: **42 tests** in **4.352s** (`OK`).
- **CLI Entrypoint Verification (`verify-realhw-ext2-installer` & `verify-all-recovery --with-phase94 ... --with-phase138`)**:
  - Local Donor `verify-realhw-ext2-installer --json`: `exit 0` (`status=VERIFIED_REALHW_EXT2_INSTALLER_AND_P1_RESCUE_GATE`, `verification_mode=LOCAL_DONOR_O_RDONLY`, `all_passed=True`, `pillar_a=6/6`, `pillar_b=6/6`, `pillar_c=4/4`, `suite_sha256=4008aab5a21865349b2a8abfe64b6e69fac1ad2467e166444a5d91f854f638d0`).
  - Clean-Room `verify-realhw-ext2-installer --clean-room --json` (`FX3_FX6_FORCE_CLEAN_ROOM=1`): `exit 0` (`status=VERIFIED_REALHW_EXT2_INSTALLER_AND_P1_RESCUE_GATE`, `verification_mode=CLEAN_ROOM_SYNTHETIC`, `all_passed=True`, `suite_sha256=3924668b6e373401628e1d8304767c3a17c47edd8f5cb29546e2de2c7987060f`).
  - Local Donor `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124 --with-phase126 --with-phase134 --with-phase138 --json`: `exit 0` (`status=VERIFIED_RECOVERY_MASTER_SUITE`, `all_passed=True`, `pillars=16/16`, `recovery_master_sha256=0630b15eeaff85befe0bae3632b739f6fde559f62cad3aa4b373d09135374bad`).
  - Clean-Room `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --with-phase124 --with-phase126 --with-phase134 --with-phase138 --clean-room --json`: `exit 0` (`status=VERIFIED_RECOVERY_MASTER_SUITE`, `all_passed=True`, `pillars=16/16`, `recovery_master_sha256=07b2c16ad97e1ac5b4adbda8b3373b32405a2c01f4af7d257afe7937f3e88cde`).
- **Clean-Room Lab Master Gate, Donor-vs-Clean-Room Parity & JSON Regex Hygiene**:
  - `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` -> `[hygiene] git status --porcelain binary/pyc audit: CLEAN` (`ALL GREEN`).
  - 12-Artifact Donor (`LOCAL_DONOR_O_RDONLY`) vs Clean-Room (`CLEAN_ROOM_SYNTHETIC`) parity check -> `diffs: []`.
  - Regex `r'(?<![0-9A-Za-z_/.-])b[\\'\\\"]'` across JSON outputs in both modes -> `0` matches (`CLEAN`).
