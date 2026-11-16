# Phase 57 — Non-Journaled `exFAT` (`BootChecksum` / `VolumeDirty` / `.RSV`) & Dual CFexpress Type A Production Footage Isolation Firewall

# 第 57 阶段 — 非日志 `exFAT`（12 扇区 `BootChecksum` / `VolumeDirty` / `.RSV` 未封口视频）与双槽位 CFexpress 生产素材隔离防火墙

> **Date / 日期**: `2026-11-14`  
> **Owner / 负责代理**: Hydrogen-50 (`antigravity`, isolated child worktree)  
> **Primary Module / 核心模块**: [`outputs/fx3-safety/fx3_safety/exfat_media_integrity_guard.py`](../../outputs/fx3-safety/fx3_safety/exfat_media_integrity_guard.py)  
> **Unit Tests / 单元测试**: [`outputs/fx3-safety/tests/test_exfat_media_integrity_guard.py`](../../outputs/fx3-safety/tests/test_exfat_media_integrity_guard.py)  
> **Safety Redlines / 硬件安全红线**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `os.O_RDONLY` only, zero raw `bytes` repr output (`.hex()` only).

---

## 1. Executive Summary / 阶段总览

**English**:  
Phase 57 operationalizes our Wave-4 Phase 50 non-journaled `exFAT` media-safety research (`exfat_media_hygiene_ok`) into an executable, fail-closed media integrity & production-footage isolation firewall inside `outputs/fx3-safety/`. Before any `H0`/`H1` hardware rehearsal or Stage-A/B trial can proceed, [`evaluate_exfat_media_integrity_guard`](../../outputs/fx3-safety/fx3_safety/exfat_media_integrity_guard.py) verifies:
1. **Pure-Python Microsoft/SDA `exFAT` VBR & 12-Sector `BootChecksum` Integrity** across Main (`Sectors 0..11`) and Backup (`Sectors 12..23`) Boot Regions, explicitly skipping `VolumeFlags` (`106..107`) and `PercentInUse` (`112`) and enforcing `VolumeDirty` (`0x0002`) / `MediaFailure` (`0x0004`) fail-closed rejection.
2. **Sony Camera Media Tree & Dual-Slot (`Slot A` / `Slot B`) Production Card Firewall**, blocking `H0`/`H1` trial entry if any inserted CFexpress Type A / SDXC card contains live client footage (`XDROOT/Clip/*.MXF` for FX6, `PRIVATE/M4ROOT/CLIP/*.MP4` or `M4ROOT/CLIP/*.MP4` for FX3, `DCIM/*`), unfinalized `.RSV` power-loss recovery files, or `FOUND.000/*.CHK` `chkdsk /f` remnants.
3. **Strict `p1` (`FAT12`/`FAT16`) vs External `exFAT` Filesystem Separation**, auditing internal `p1` failsafe VBR (`nflasha1` via `os.O_RDONLY` in Local Donor mode or deterministic synthetic `FAT12` in `FX3_FX6_FORCE_CLEAN_ROOM=1` mode) and rejecting any device/mount overlap or cross-domain write onto internal eMMC.

**中文摘要**:  
第 57 阶段将 Wave-4（Phase 50）的非日志 `exFAT` 介质安全研究落地为可执行、失效关闭（fail-closed）的存储卡完整性与生产素材隔离防火墙（[`exfat_media_integrity_guard.py`](../../outputs/fx3-safety/fx3_safety/exfat_media_integrity_guard.py)）：
1. **纯 Python `exFAT` VBR 与 12 扇区 `BootChecksum` 校验**：完整解析主引导区（`0..11` 扇区）与备份引导区（`12..23` 扇区），严格遵循 Microsoft exFAT 规范跳过 `VolumeFlags`（偏移 `106..107`）和 `PercentInUse`（偏移 `112`），拦截 `VolumeDirty`（`0x0002`）与 `MediaFailure`（`0x0004`）。
2. **Sony 机内介质目录树（FX6 `XDROOT` / FX3 `M4ROOT` / `.RSV`）与双卡槽隔离防火墙**：同时检查 `Slot A` 与 `Slot B`，若存在未清空客户素材（`XDROOT/Clip/*.MXF`、`PRIVATE/M4ROOT/CLIP/*.MP4`、`M4ROOT/CLIP/*.MP4`、`DCIM/*`）、掉电未封口 `.RSV` 恢复文件或 `FOUND.000/*.CHK`，强制阻断 `H0`/`H1` 试验入口，仅放行专用空白/实验介质卡。
3. **内部 `p1`（`FAT12`/`FAT16`）与外部 `exFAT` 严格文件系统隔离**：基于 `os.O_RDONLY` 只读核验 `nflasha1` 维持 `FAT12`/`FAT16`（禁止 `EXFAT   ` 与交叉挂载/写入），硬锁定 `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`。

---

## 2. Technical Deliverables & Architecture / 技术交付详情

| Component / 模块 | Entrypoints / 关键接口 | Verified Invariants / 校验不变量 |
| :--- | :--- | :--- |
| **1. `exFAT` VBR & 12-Sector `BootChecksum`** | `compute_exfat_boot_checksum`, `parse_exfat_vbr`, `verify_exfat_boot_region`, `verify_exfat_image_file` | `FileSystemName == b"EXFAT   "`, `MustBeZero[11:64] == 0`, `BytesPerSectorShift in 9..12` (`512..4096 B` power-of-two), `SectorsPerClusterShift <= 25 - bps_shift`, `BootSignature == 0xAA55`, rolling 32-bit `BootChecksum` over 11 sectors skipping `(106, 107, 112)` uniform across all Sector 11 & Sector 23 slots, Main vs Backup consistency, `VolumeDirty` (`0x0002`) & `MediaFailure` (`0x0004`) fail-closed. |
| **2. Sony Media Tree & Dual-Slot Firewall** | `inspect_sony_media_tree`, `verify_dual_slot_media_firewall`, `MediaSlotConfig` | Scans `Slot A` & `Slot B` (read-only directory walk or manifest entries): detects FX6 `XDROOT/Clip/*.MXF` (`Sub`), FX3 `PRIVATE/M4ROOT/CLIP/*.MP4` & CFexpress `M4ROOT/CLIP/*.MP4`, unfinalized `*.RSV` (any size `>= 0`), `FOUND.000/*.CHK`, and `DCIM/*`; blocks `H0`/`H1` entry (`h0_h1_trial_entry_allowed = False`) unless dedicated blank/lab card is verified. |
| **3. `p1` `FAT12`/`FAT16` vs `exFAT` Separation** | `parse_p1_fat12_fat16_vbr`, `verify_p1_vs_exfat_filesystem_separation` | Verifies `p1` (`/dev/nflasha1`, `19,377,152 B` `FAT12` donor via `os.O_RDONLY` or clean-room `FAT12`/`FAT16` synthetic BPB), blocks `EXFAT   ` / `FAT32` on `p1`, forbids `Slot A`/`Slot B` overlap with `/dev/nflasha*` / `/dev/cnflasha*` / `/dev/mmcblk0*` / `/setting` / `/boot`, and keeps `persistent_emmc_writes_authorized = False`. |
| **4. CLI & Dual-Mode Tests** | `python3 -m fx3_safety verify-media-guard [--clean-room] [--json]`, `test_exfat_media_integrity_guard.py` | 30 new dual-mode unit tests (`0.132s`), raising `outputs/fx3-safety/tests` from 200 to **230 passing tests**. |

---

## 3. Verification Receipts / 实测验证记录

1. **CLI Verification (`verify-media-guard`)**:
   - Local Donor Mode:
     `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-media-guard` ->  
     `status=VERIFIED_SAFE mode=LOCAL_DONOR_O_RDONLY all_passed=True h0_h1_trial_entry_allowed=True p1_fs=FAT12 persistent_emmc_writes_authorized=False` (`rc=0`).
   - Clean-Room Mode:
     `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-media-guard --clean-room --json` ->  
     `schema="fx3-exfat-media-integrity-guard-v1"`, `verification_mode="CLEAN_ROOM_SYNTHETIC"`, `all_passed=true`, `h0_h1_trial_entry_allowed=true`, `persistent_emmc_writes_authorized=false` (`rc=0`).
2. **Unit Tests (Dual-Mode / 双模式单元测试)**:
   - `test_exfat_media_integrity_guard.py`: **30 tests in 0.132s — OK**.
   - Full `outputs/fx3-safety/tests` (Local Donor mode): **230 tests in 0.323s — OK**.
   - Full `outputs/fx3-safety/tests` (`FX3_FX6_FORCE_CLEAN_ROOM=1`): **230 tests in 0.309s — OK (skipped=1)**.
3. **Repository Hygiene**:
   - `make clean-audit` verified clean (zero untracked `.img`/`.exfat`/`.vfat`/`.bin`/`.so`/`.pyc` or `__pycache__` artifacts).
