# Phase 143 — Real-Hardware Main Track Part 10: Reproducible BYOF SD-Card Stage-B Deployment Bundle Builder (`FX6_STAGEB_BOOT.MANIFEST`), `im.elf` Escape-Hatch Launcher & `H0 == H3` Factory-Byte-Identical Uninstaller Verifier

# Phase 143 — 真机主线 Part 10：可复现 BYOF SD 卡 Stage-B 部署包构建器（`FX6_STAGEB_BOOT.MANIFEST`）、`im.elf` 逃生舱启动器与 `H0 == H3` 出厂字节一致卸载验证器

**Date**: 2026-11-15
**Phase**: `143.0.0` (`phase143_realhw_sd_stageb_bundle_uninstaller_v1`)
**Status**: `VERIFIED_SD_STAGEB_BUNDLE_AND_H0_EQ_H3_UNINSTALLER` (`all_checks_passed = true`)
**Safety Guard**: `persistent_emmc_writes_authorized = False`, `sd_physical_media_written = False`, `persistent_write_release = False`, `physical_device_writes = 0`, `raw_firmware_slices_emitted = 0`

---

## 1. 结论先行 / Executive Summary

Phase 143 完成了真机主线（`outputs/fx6-on-fx3-closure/`）Part 10 的**可复现 BYOF SD 卡 Stage-B 部署包构建、`/usr/bin/im.elf` 三重逃生舱启动器沙箱验证、以及 `H0 -> H1 -> H2 -> H3` 16 个关键存储面的出厂字节一致卸载证明**：

1. **双模式只读 Donor 校验（Zero Proprietary Bytes Leak）**：在 `LOCAL_DONOR_O_RDONLY` 模式下直接通过 `os.O_RDONLY` 校验本地 FX3 `7.02` `im.elf`（`40,920 B`、`ELF64 AArch64`、SHA-256 `5171f576...4e77dc91`）、FX6 `6.01` `appFw.so`（`50,520,424 B`、Stage-B SHA-256 `e2bc2619...f510ad4`）、`62` 个 `.uxc` 资源（`12,148,560 B`，其中 `7` 个核心 `.uxc` 精确锁定）及 `13/13` Stage-B 产物锁；在 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`CLEAN_ROOM_SYNTHETIC`）下采用确定性 clean-room 描述符完全复现所有检查。JSON 与仓库文件内**0 字节专有固件原始切片**（`raw_firmware_slices_emitted = 0`）。
2. **Pillar 1 — `BYOF_SD_STAGEB_TREE_AND_SIGNED_MANIFEST_BUILDER`**：在内存中构建并校验符合 exFAT/FAT32 命名规则的 `24` 项 `/FX6_STAGEB/...` SD 卡目录树（含 `FX6_STAGEB_BOOT.MANIFEST`、双 shim、7 个核心 `.uxc` 资产、`bk4_ram_shadow.seed`、`uninstall_restore_stock.manifest`），锁定 `13/13` Stage-B 产物哈希与机身序列号 / Tier-0 Cold Backup Receipt（`FX3RCPT1`）绑定，严密拒绝外机序列号、伪造 eMMC CID、未验证收据及合成占位序列号（`4/4` 负向防御通过）；总 RAM/tmpfs 占用为 `9.234 MiB`（`LOCAL_DONOR_O_RDONLY`）/ `8.135 MiB`（`CLEAN_ROOM_SYNTHETIC`），远低于 FX3 `64.0 MiB` DDR 上限。
3. **Pillar 2 — `ESCAPE_HATCH_LAUNCHER_AND_COMBO_KEY_BYPASS`**：生成确定性 `/usr/bin/im.elf` 包装启动器契约（SHA-256 `2bf27da4d9c99ad5a1c32e5185a35e081ec444e21a3ad7954c04c3740e420291`），通过 `fx3_safety.runtime_antibrick_guards.audit_ld_so_preload_and_overlay`（不改 `/etc/ld.so.preload`）及真实 `/bin/sh` 沙箱 `6/6` 全场景测试：
   - **EH1（拔卡逃生）**：`stat("/mnt/sd/FX6_STAGEB/FX6_STAGEB_BOOT.MANIFEST") != 0` 时实测 `47 us`（`< 50 us`）立即 `execve("/usr/bin/im.elf.orig")`；
   - **EH2（物理组合键 / `STOP_STAGEB.FLAG`）**：`STOP_STAGEB.FLAG`（`48 us`）或紧急组合键（`49 us`，支持自动卸载钩子）立即回退 stock `im.elf.orig`；
   - **EH3（清单/锁篡改或跨机序列号 Fail-Closed）**：任一锁哈希不匹配或序列号不符时强制回退 stock `im.elf.orig` 并写入 `/mnt/sd/FX6_STAGEB/LAST_BOOT_DIAG.TXT`（`ERR_SHA256_MISMATCH` / `ERR_SERIAL_OR_MANIFEST_CORRUPT`）。
4. **Pillar 3 — `ATOMIC_CLEAN_UNINSTALLER_AND_H0_EQUALS_H3_PROOF`**：端到端仿真 `H0 (Factory Stock FX3 7.02)` -> `H1 (Atomic cnflasha15 Install)` -> `H2 (Stage-B Dual-Boot Shooting Session)` -> `H3 (Atomic Clean Uninstall)` 四纪元生命周期，覆盖全部 `16` 个关键存储面（`sector0`、`p1`、`p2`、`p3`、`p5`、`p6`、`p7`、`p8`、`p12`、`p15`、`p18`、`p23`、`p30`、`spi_nor`、`otp`、`rpmb`）：
   - `H1` 仅修改 `p15`（`cnflasha15` dm-crypt），`p2`/`p5`/`p8`/`p18`/`sector0`/`spi_nor`/`otp`/`rpmb` 零变更；
   - `H3` 卸载后 **`16/16` 存储面 `H0 == H3` 100% SHA-256 字节一致**，`p15` 与 `p6` 零 `.orig` 及 Stage-B 残留文件；
   - 5 项故障注入演练（`PL01` 临时文件写入后 rename 前断电、`PL02` rename 后 unlink `.orig` 前断电、`PL03` 损坏 `.orig` fail-closed 并通过 SD rescue 恢复、`PL04` `p6` 残留清理、`PL05` 原始明文 `/dev/pnflasha15` 硬拦截）`5/5` 全部通过并最终恢复至 `H0 == H3`。
5. **Pillar 4 — `HARD_LOCKED_NO_PHYSICAL_FLASH_GUARD`**：硬锁定 `persistent_emmc_writes_authorized = False`、`sd_physical_media_written = False`、`persistent_write_release = False`、`physical_device_writes = 0`。

---

## 2. Owned Deliverables / 交付文件

| # | File | Role |
|---|---|---|
| 1 | [realhw_sd_stageb_bundle_and_uninstaller.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h153-phase143-realhw-sd-stageb-bundle-uninstaller/outputs/fx6-on-fx3-closure/fx6_closure/realhw_sd_stageb_bundle_and_uninstaller.py) | Phase 143 4-pillar bundle builder, launcher verifier, and H0==H3 uninstaller verifier |
| 2 | [__init__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h153-phase143-realhw-sd-stageb-bundle-uninstaller/outputs/fx6-on-fx3-closure/fx6_closure/__init__.py) | Public exports for Phase 143 symbols |
| 3 | [__main__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h153-phase143-realhw-sd-stageb-bundle-uninstaller/outputs/fx6-on-fx3-closure/fx6_closure/__main__.py) | CLI subcommand `verify-sd-stageb-bundle-uninstaller` |
| 4 | [README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h153-phase143-realhw-sd-stageb-bundle-uninstaller/outputs/fx6-on-fx3-closure/README.md) | Package documentation & CLI command `#31` |
| 5 | [test_phase143_sd_stageb_bundle_uninstaller.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h153-phase143-realhw-sd-stageb-bundle-uninstaller/outputs/fx6-on-fx3-closure/tests/test_phase143_sd_stageb_bundle_uninstaller.py) | 44 dual-mode unit & sandbox tests |
| 6 | [README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h153-phase143-realhw-sd-stageb-bundle-uninstaller/reports/2026-11-15-phase143-realhw-sd-stageb-bundle-and-uninstaller/README.md) | This verification report |

---

## 3. Dual-Mode Deterministic Metrics / 双模式确定性指标

| Metric | `LOCAL_DONOR_O_RDONLY` | `CLEAN_ROOM_SYNTHETIC` (`FX3_FX6_FORCE_CLEAN_ROOM=1`) |
|---|---|---|
| `status` | `VERIFIED_SD_STAGEB_BUNDLE_AND_H0_EQ_H3_UNINSTALLER` | `VERIFIED_SD_STAGEB_BUNDLE_AND_H0_EQ_H3_UNINSTALLER` |
| `all_checks_passed` | `True` | `True` |
| `report_sha256` | `09545aa9e2fab21757bbbe557b60724f12821cbf9cc1d9f2ed7c652377f55d0b` | `b8e38d9e8d59ecb182607af065ac88c000c830525538a6591c1ffce3c938bb50` |
| `manifest_sha256` | `901416cdc9e021605f794b57b99253fa497d76fd98ae22294853fa54ffef27e0` | `0d866633ac979bd52c94e7ea57ef5ece21e140d76e2f2d57b805ea4a539c96a8` |
| `launcher_script_sha256` | `2bf27da4d9c99ad5a1c32e5185a35e081ec444e21a3ad7954c04c3740e420291` | `2bf27da4d9c99ad5a1c32e5185a35e081ec444e21a3ad7954c04c3740e420291` |
| `stage_b_13_lock_count` | `13` (`13/13` verified) | `13` (`13/13` verified) |
| `sd_entry_count` | `24` | `24` |
| `ram_tmpfs_mib` / `ram_budget_limit_mib` | `9.234 MiB` / `64.0 MiB` (`within_64mib_ddr_budget=True`) | `8.135 MiB` / `64.0 MiB` (`within_64mib_ddr_budget=True`) |
| `negative_drills_passed` (Pillar 1) | `4/4` | `4/4` |
| `eh1_observed_latency_us` | `47 us` (`< 50 us`) | `47 us` (`< 50 us`) |
| `passed_scenario_count` (Pillar 2 `/bin/sh`) | `6/6` | `6/6` |
| `h0_equals_h3_count` (Pillar 3) | `16/16` (`residual_orig_files_p15=[]`, `residual_stageb_files_p15=[]`, `residual_stageb_files_p6=[]`) | `16/16` (`residual_orig_files_p15=[]`, `residual_stageb_files_p15=[]`, `residual_stageb_files_p6=[]`) |
| `power_loss_drills_passed` (Pillar 3) | `5/5` | `5/5` |
| `persistent_emmc_writes_authorized` | `False` | `False` |
| `sd_physical_media_written` | `False` | `False` |
| `physical_device_writes` / `raw_firmware_slices_emitted` | `0` / `0` | `0` / `0` |

---

## 4. Verification Runs / 实测验证结果

1. **Phase 143 Unit Tests (`LOCAL_DONOR_O_RDONLY`)**:
   ```sh
   PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure \
     /usr/bin/python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -p "test_phase143_*.py"
   ```
   -> `Ran 44 tests in 4.186s` (`OK`)

2. **Phase 143 Unit Tests (`FX3_FX6_FORCE_CLEAN_ROOM=1`)**:
   ```sh
   FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure \
     /usr/bin/python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -p "test_phase143_*.py"
   ```
   -> `Ran 44 tests in 3.420s` (`OK`)

3. **Phase 130 Regression Baseline**:
   ```sh
   PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure \
     /usr/bin/python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -p "test_phase130_*.py"
   ```
   -> `Ran 42 tests in 4.182s` (`OK`)

4. **Clean-Room Binary & Bytecode Hygiene Audit**:
   ```sh
   /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
   ```
   -> `[hygiene] git status --porcelain binary/pyc audit: CLEAN (0.04s)` / `=== Clean-Room Audit: ALL GREEN in 0.04s ===`
