# Phase 119 — SquashFS 4.0 (`hsqs` `0x73717368`) Partition Superblock / Compression / Table-Bounds Verifier, Sony Warp-Boot `hibdrv` (`WBI2` Hibernation Snapshot) Stale-Resume Poisoning Triage & Ephemeral `noresume` RAM-Boot Bypass Verifier, & 12-Pillar Recovery Master Suite

> **Date**: `2026-11-14` · **Phase**: `119`  
> **Primary Module**: [`outputs/fx3-recovery-adapter/fx3_recovery/squashfs_and_hibdrv_wbi_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/squashfs_and_hibdrv_wbi_verifier.py)  
> **Unit Tests**: [`outputs/fx3-recovery-adapter/tests/test_squashfs_and_hibdrv_wbi_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_squashfs_and_hibdrv_wbi_verifier.py) (`40` fast dual-mode tests)  
> **Safety Redlines**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `ALLOW_BOOT_PARTITION_TARGETING = False`, `ALLOW_DESTRUCTIVE_FASTBOOT = False`, `OTP_FUSE_TOUCHES = 0`, `PASSIVE_TX_BYTES_EMITTED = 0`, `PHYSICAL_DEVICE_WRITES = 0`, `WBI_PARTITION_WRITES = 0` (hard-locked)

---

## 1. Executive Summary (English)

Phase 119 adds Pillar 12 (`verify-squashfs-wbi-triage` & `verify-all-recovery --with-phase119`) to the `fx3_recovery` suite for Sony `ILME-FX3` (`0x91030080` / `ALCIN_UUD`, `CXD90057` Linux `4.9.337-scel+`), achieving **12/12** green pillars in both `LOCAL_DONOR_O_RDONLY` and `CLEAN_ROOM_SYNTHETIC` modes:

| Pillar / Deliverable | Key Entrypoints | Core Invariants & Fail-Closed Gates |
| :--- | :--- | :--- |
| **0. Read-Only (`O_RDONLY`) FX3/FX6 Donor Inspection & Clean-Room Fallback** | [`inspect_squashfs_and_wbi_donors_readonly`](../../outputs/fx3-recovery-adapter/fx3_recovery/squashfs_and_hibdrv_wbi_verifier.py) | Opens local FX3 `2.05/nflasha1` `/boot/initrd.img` SquashFS (`9,097,216` B, `d5c4795c...`), `udtrbody.squashfs` (`1,253,376` B, `62e86fad...`), FX6 `updater.img` (`1,253,376` B, `d204fcf2...`), bounded 512B header + section-table reads on FX3 `nflasha5.img` (`209,112,512` B, `1399` `WBI2` sections, hdr `11ae3977...`, tbl `7286ddb0...`) and FX6 `nflasha5` (`202,677,056` B, `1197` `WBI2` sections, hdr `afa13951...`, tbl `38d12419...`), plus FX3/FX6 `vmlinux.bin` (`da4a66fa...` / `bc4925e7...`, `4.9.337-scel+` & `WBI:invalid param`/`hibernate`) strictly via `os.O_RDONLY \| O_NOFOLLOW \| O_NONBLOCK`; deterministically falls back to `CLEAN_ROOM_SYNTHETIC` when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor paths are absent. |
| **Pillar A — SquashFS 4.0 (`hsqs` `0x73717368`) Partition Superblock & Table-Bounds Verifier** | [`verify_squashfs_partition_bytes`](../../outputs/fx3-recovery-adapter/fx3_recovery/squashfs_and_hibdrv_wbi_verifier.py), [`build_synthetic_squashfs_superblock`](../../outputs/fx3-recovery-adapter/fx3_recovery/squashfs_and_hibdrv_wbi_verifier.py) | Pure-Python 96-byte `<5I6H8Q` superblock parser & validator checking little-endian `s_magic == 0x73717368` (rejecting big-endian `sqsh` `0x68737173` and blank `0x00`/`0xFF` flash), `s_major == 4, s_minor == 0`, `inodes`, power-of-two `block_size` `4 KiB..1 MiB` (`block_size == 1 << block_log`), `compression_id` in `{1:GZIP, 2:LZMA, 3:LZO, 4:XZ, 5:LZ4, 6:ZSTD}`, `no_ids >= 1`, `96 < bytes_used <= partition_size`, `actual_bytes >= bytes_used`, strict monotonic table offsets (`inode_table_start < directory_table_start <= fragment <= export <= id <= xattr <= bytes_used`), and `root_inode` block offset bounds—catching truncated `rootfs`/`app` flashes offline before `/sbin/init2` `SIGBUS` or `VFS: Unable to mount root fs` boot-loops. |
| **Pillar B — Sony `Warp-Boot` / `hibdrv` (`WBI2`) Stale-Resume Poisoning Triage & Ephemeral `noresume` Bypass Verifier** | [`parse_wbi2_header_and_table`](../../outputs/fx3-recovery-adapter/fx3_recovery/squashfs_and_hibdrv_wbi_verifier.py), [`triage_wbi_hibdrv_snapshot`](../../outputs/fx3-recovery-adapter/fx3_recovery/squashfs_and_hibdrv_wbi_verifier.py), [`verify_ephemeral_noresume_bootargs_bypass`](../../outputs/fx3-recovery-adapter/fx3_recovery/squashfs_and_hibdrv_wbi_verifier.py), [`audit_wbi_partition_write_attempt`](../../outputs/fx3-recovery-adapter/fx3_recovery/squashfs_and_hibdrv_wbi_verifier.py), [`run_wbi_hibdrv_6_scenario_triage`](../../outputs/fx3-recovery-adapter/fx3_recovery/squashfs_and_hibdrv_wbi_verifier.py) | Models 88B/512B `WBI2` hibernation header + 64B section table (`0x0f0f0f0f` XOR metadata checksum, 4K alignment, `resume_vector` coverage, non-overlap) and detects `WBI_SNAPSHOT_TRUNCATED_OR_CRC_MISMATCH`, `WBI_KERNEL_ABI_FINGERPRINT_MISMATCH`, and `WBI_EPHEMERAL_NORESUME_REQUIRED`. Enforces strictly RAM-only `bootargs` (`noresume` / `hibdrv.resume=0`, `ro rootwait`, rejecting `rw` on eMMC, `mtdparts`, `nowatchdog`, and unverified `init=`) with **zero persistent eMMC `WBI` partition erase/writes** (`wbi_partition_writes == 0`) via `audit_wbi_partition_write_attempt`. |
| **Pillar C — 12-Pillar Recovery Master Suite & 40 Dual-Mode Unit Tests** | [`fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py), [`fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py), [`test_squashfs_and_hibdrv_wbi_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_squashfs_and_hibdrv_wbi_verifier.py) | Registers `verify-squashfs-wbi-triage [--clean-room] [--json] [--out ...]` and opt-in `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119` (`12/12` green in both modes while preserving default `7/7` behavior), exports all Phase 119 symbols in `__all__`, and passes `40` fast dual-mode tests (`>= 12` pillar check). |

---

## 2. 中文摘要 (Chinese Summary)

Phase 119 在严格只读、纯内存（RAM-only）安全红线（`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`ALLOW_BOOT_PARTITION_TARGETING = False`、`ALLOW_DESTRUCTIVE_FASTBOOT = False`、`OTP_FUSE_TOUCHES = 0`、`PASSIVE_TX_BYTES_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`WBI_PARTITION_WRITES = 0`）下，为 `ILME-FX3`（`0x91030080` / `ALCIN_UUD`，`CXD90057` Linux `4.9.337-scel+`）交付 SquashFS 4.0 与 Sony `Warp-Boot` `hibdrv`/`WBI2` 验证支柱并接入 **12 支柱**恢复总检门禁：

1. **供体只读（`os.O_RDONLY`）检查与确定性净室回退**：严格以 `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 打开本地 FX3 `v7.02`/`2.05` 与 FX6 `v6.01` 供体 SquashFS（`initrd.img`、`udtrbody.squashfs`、`updater.img`）、有界读取 `nflasha5` `WBI2` 头与节表（FX3 `1399` 节 / FX6 `1197` 节）及 `vmlinux.bin` 内核 `UTS_VERSION` 与 `WBI:invalid param`/`hibernate` 符号；当 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺失时确定性回退至 `CLEAN_ROOM_SYNTHETIC`。
2. **支柱 A — SquashFS 4.0（`hsqs` `0x73717368`）分区超级块、压缩算法与表边界校验器**：纯 Python 解析 96 字节 `<5I6H8Q` 超级块，校验 `s_magic == 0x73717368`（拦截大端 `sqsh` 及全 `0x00`/全 `0xFF` 擦除态）、`s_major == 4, s_minor == 0`、`block_size` 2 的幂（`4 KiB..1 MiB` 且 `block_size == 1 << block_log`）、`compression_id` ∈ `{1:GZIP, 2:LZMA, 3:LZO, 4:XZ, 5:LZ4, 6:ZSTD}`、`bytes_used <= partition_size`、`actual_bytes >= bytes_used` 以及表偏移严格单调递增，离线拦截截断 `rootfs`/`app` 刷写导致的 `/sbin/init2` `SIGBUS` 与 `VFS: Unable to mount root fs` 启动死循环。
3. **支柱 B — Sony `Warp-Boot` / `hibdrv`（`WBI2` 休眠快照）过期恢复中毒分诊与易失 `noresume` RAM 旁路验证器**：建模 88B/512B `WBI2` 头与 64B 节表（`0x0f0f0f0f` 元数据 XOR 校验和、4K 对齐、`resume_vector` 覆盖与重叠检查），精准检测 `WBI_SNAPSHOT_TRUNCATED_OR_CRC_MISMATCH`、`WBI_KERNEL_ABI_FINGERPRINT_MISMATCH` 与 `WBI_EPHEMERAL_NORESUME_REQUIRED`，并验证修复仅使用 RAM-only `bootargs`（`noresume` / `hibdrv.resume=0`，`ro rootwait`），通过防火墙 `audit_wbi_partition_write_attempt` 确保零持久 eMMC `WBI` 分区写入或擦除（`wbi_partition_writes == 0`）。
4. **支柱 C — CLI 与 12 支柱恢复总检集成**：注册 `verify-squashfs-wbi-triage` 及 `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119`（双模式均达 **12/12** 绿色通过，无参数默认仍兼容 `7/7`）。

---

## 3. Owned Files (Strict 6-File Scope)

1. [`outputs/fx3-recovery-adapter/fx3_recovery/squashfs_and_hibdrv_wbi_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/squashfs_and_hibdrv_wbi_verifier.py) *(NEW)*
2. [`outputs/fx3-recovery-adapter/fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) *(UPDATED — Phase 119 symbol exports)*
3. [`outputs/fx3-recovery-adapter/fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py) *(UPDATED — `verify-squashfs-wbi-triage` & `verify-all-recovery --with-phase119`)*
4. [`outputs/fx3-recovery-adapter/README.md`](../../outputs/fx3-recovery-adapter/README.md) *(UPDATED — Phase 119 12th pillar documentation)*
5. [`outputs/fx3-recovery-adapter/tests/test_squashfs_and_hibdrv_wbi_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_squashfs_and_hibdrv_wbi_verifier.py) *(NEW — 40 fast dual-mode unit tests)*
6. [`reports/2026-11-14-phase119-squashfs-wbi-hibdrv-recovery/README.md`](README.md) *(NEW — this bilingual report)*

---

## 4. Verification Commands & Observed Results

- **Phase 119 Unit Tests (`test_squashfs_and_hibdrv_wbi_verifier.py`, 40 tests)**:
  - Local Donor mode (`os.O_RDONLY`): **40 tests** in **2.099s** (`OK`).
  - Clean-Room mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **40 tests** in **1.726s** (`OK`).
- **Full `outputs/fx3-recovery-adapter/tests` Suite**:
  - Local Donor mode (`os.O_RDONLY`): **517 tests** in **41.083s** (`OK`, `skipped=1`).
  - Clean-Room mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **459 tests** in **11.224s** (`OK`, `skipped=9`).
- **CLI Entrypoint Verification (`verify-squashfs-wbi-triage` & `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119`)**:
  - Local Donor `verify-squashfs-wbi-triage --json`: `exit 0` (`status=VERIFIED_SQUASHFS_AND_HIBDRV_WBI_GATE`, `verification_mode=LOCAL_DONOR_O_RDONLY`, `all_passed=True`, `squashfs_compressions=6`, `wbi_scenarios=6/6`, `wbi_partition_writes=0`, `suite_sha256=267c1a2025cf9c80...`).
  - Clean-Room `verify-squashfs-wbi-triage --json` (`FX3_FX6_FORCE_CLEAN_ROOM=1`): `exit 0` (`status=VERIFIED_SQUASHFS_AND_HIBDRV_WBI_GATE`, `verification_mode=CLEAN_ROOM_SYNTHETIC`, `all_passed=True`, `suite_sha256=a2887e282ce52a42...`).
  - Local Donor `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --json`: `exit 0` (`status=VERIFIED_RECOVERY_MASTER_SUITE`, `all_passed=True`, `pillars=12/12`, `recovery_master_sha256=0630b15eeaff85be...`).
  - Clean-Room `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119 --json`: `exit 0` (`status=VERIFIED_RECOVERY_MASTER_SUITE`, `all_passed=True`, `pillars=12/12`, `recovery_master_sha256=07b2c16ad97e1ac5...`).
- **Clean-Room Lab Master Gate & JSON Regex Hygiene**:
  - `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` -> `[hygiene] git status --porcelain binary/pyc audit: CLEAN` (`ALL GREEN in 0.05s`).
  - Regex `r'(?<![0-9A-Za-z_/.-])b[\x27"]'` across JSON outputs in both modes -> `0` matches (`CLEAN`).
