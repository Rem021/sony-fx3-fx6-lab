# Phase 142 — Real-Hardware Main Track Part 9: Gate G43 (`AdjustControl 0x40` / `libJiritsu.so` Service-Session Electrical, `/tmp/jbusy` & `p6` `25 MiB` Quota Guard), Gate G44 (`/dev/cnflasha15` SPACC Cipher-Boundary, Tier-0 Cold-Backup Receipt, SD Escape-Hatch & `p1`/`p3` Mutual-Exclusion Guard), and Unified 44-Gate Master Safety Preflight (`G01..G44`)

# 第 142 阶段 — 真机主线 Part 9：`AdjustControl 0x40` / `libJiritsu.so` 服务会话供电、`/tmp/jbusy` 与 `p6` `25 MiB` 配额护栏（`Gate G43`）、`/dev/cnflasha15` SPACC 密文边界、Tier-0 冷备份回执、SD 卡逃生门与 `p1`/`p3` 互斥预检（`Gate G44`）及 44 门禁主安全预检（`G01..G44`）

- **Date / 日期**: `2026-11-14`
- **Branch / 分支**: `codex/h152-phase142-safety-realhw-jiritsu-cnflasha-44gates`
- **Target Package / 目标包**: `outputs/fx3-safety/fx3_safety/`
- **New Module / 新增模块**: [`realhw_jiritsu_cnflasha_and_44gate_guard.py`](../../outputs/fx3-safety/fx3_safety/realhw_jiritsu_cnflasha_and_44gate_guard.py)
- **Redlines Preserved / 硬安全红线**: `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`, `overall_ready_for_hardware_attach = False` (offline & dry-run), prior gate modules (`G01..G42`) untouched.

---

## 1. Engineering Deliverables / 工程交付清单

### 1.1 Read-Only (`os.O_RDONLY`) Donor Contract Audit / 只读参考件合约审计 (`audit_phase142_donor_contracts`)
Inspects the 8 pinned FX3 `v7.02` & FX6 `v6.01` real-hardware deployment/partition/updater donor files strictly via `os.open(..., os.O_RDONLY)` with deterministic clean-room synthetic fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or local donor files are absent:

| Key | Body | Artifact | Size (B) | SHA-256 Prefix | Verified Symbols / Tokens |
| :--- | :---: | :--- | :---: | :--- | :--- |
| `fx3_lib_jiritsu` | FX3 | `libJiritsu.so` | `225,200` | `bdef58b24a3b67b4...` | `JIRITSU_SET_FILE2`, `JIRITSU_GET_FILE2`, `/tmp/jbusy`, `/tmp/jiritsu/libJit.so`, `/dev/nflasha6` |
| `fx3_ld_2_25` | FX3 | `ld-2.25.so` | `120,616` | `90b4fe734ba7faa0...` | `\x7fELF`, `GLIBC_2.17`, `dl_open` |
| `fx3_partinf_conf` | FX3 | `partinf.conf` | `3,999` | `3d96228d4ed2db3c...` | `0x00000080,0x0000BF80`, `0x00112000,0x000FA000`, `0x00346000,0x00018000` |
| `fx3_mount_conf` | FX3 | `mount.conf` | `1,248` | `ea0132091f3bb8d6...` | `/dev/nflasha1 none vfat 25100288`, `/dev/nflasha6 none vfat 26214400`, `/dev/nflasha15 /usr raw 524288000` |
| `fx3_p2_kemco_txt` | FX3 | `kemco.txt` (`p2`) | `1,736` | `555454e8b7db1461...` | `cfg.uart=1`, `wdt.mode=1` |
| `fx3_up_sh` | FX3 | `up.sh` | `6,572` | `c774320a0ab92c13...` | `UPDIR=$UPMNT/updater`, `rm -f $UPDIR/mode*`, `sync` |
| `fx3_loader_nor` | FX3 | `loader_nor.bin` | `101,888` | `4358c839cfb1f22d...` | `\\updater\\mode`, `\\mode\\cmode` |
| `fx6_p1_kemco_txt` | FX6 | `kemco.txt` (`p1`) | `933` | `e7763ad93a721f29...` | `cfg.uart=9`, `console=` |

When `include_large_binaries=True`, additionally streams FX3 `appFw.so` (`/dev/nflasha`, `OFF_BY_BATT_END`, `OFF_BY_BATT_INVALID`) and `cpapp-b.bin` (`BATT_AUTH_S`, `THERMISTOR_ADJ_START`) strictly via `os.O_RDONLY` without copying or storing raw firmware bytes.

### 1.2 Gate `G43`: `AdjustControl 0x40` / `libJiritsu.so` Service-Session Electrical, `/tmp/jbusy` & `p6` `25 MiB` Quota Guard (`verify_jiritsu_service_session_and_p6_guard`)
- **English**: Guards real-camera USB `AdjustControl 0x40` / `libJiritsu.so` service sessions against brownout, stuck `/tmp/jbusy` locks, malformed wire framing, misaligned ELF `.so` probes, and `p6` (`25 MiB` = `26,214,400 B`) partition exhaustion, failing closed on:
  1. `BLOCKED_JIRITSU_ELECTRICAL_BROWNOUT_RISK`: `NP-FZ100` SoC `< 75.0%` or load voltage `< 7.4V` without regulated USB-PD (`>= 8.55V`, `>= 27.0W`).
  2. `BLOCKED_JIRITSU_JBUSY_ACTIVE_0X10000011`: `/tmp/jbusy` exists or precheck code != `0x11` (`ENOENT`; aborts on `0x10000011`).
  3. `BLOCKED_JIRITSU_WIRE_FRAMING_OR_FORBIDDEN_OPCODE`: wire prefix != `00ff00`, `selector == 2`, or any `MODE`/`START`/`FORMAT`/`MOUNT` opcode.
  4. `BLOCKED_JIRITSU_ELF_ALIGNMENT_OR_SELFDELETE`: `PT_LOAD p_align != 0x10000` (`64 KiB`), `DT_HASH != (1,1,0,0)`, or constructor `unlinkat` self-delete disabled.
  5. `BLOCKED_P6_QUOTA_OR_RESIDUAL_EXHAUSTION`: `peak_p6_bytes > 8 MiB` (`8,388,608 B`) or `p6_residual_files > 0` (preventing `0x1000000F` and root-owned orphaned `.so` files in `p6`).
- **中文摘要**：保护物理 ILME-FX3（`7.02`）USB 服务会话在进入 `/tmp/jiritsu/` 与 `nflasha` 访问前具备安全供电与容器契约：
  1. 要求 `NP-FZ100` 电量 `>= 75%` 且带载电压 `>= 7.4V`（或稳定 `>= 8.55V / 27W` USB-PD 供电），防止读表/暂存掉电（`BLOCKED_JIRITSU_ELECTRICAL_BROWNOUT_RISK`）；
  2. 强制 `/tmp/jbusy` 预检返回 `ENOENT`（`0x11`），命中 `0x10000011` 立即阻断（`BLOCKED_JIRITSU_JBUSY_ACTIVE_0X10000011`）；
  3. 强制 `00 ff 00` 帧前缀、`selector != 2`、禁止 `MODE`/`START`/`FORMAT`/`MOUNT` 操作码，并要求 `ld-2.25.so` 加载段满足 `64 KiB`（`0x10000`）对齐 + SysV `DT_HASH (1,1,0,0)` + 构造函数 `unlinkat` 自删除；
  4. 强制 `p6`（`/dev/nflasha6`，`25 MiB` = `26,214,400 B`）峰值占用 `<= 8 MiB` 且会话后残留文件数 `== 0`，杜绝 `0x1000000F` 分区耗尽与 root 属主 `.so` 残留。

### 1.3 Gate `G44`: `/dev/cnflasha15` SPACC Cipher-Boundary, Tier-0 Cold-Backup Receipt, SD Escape-Hatch & `p1`/`p3` Mutual-Exclusion Guard (`verify_cnflasha_spacc_sd_escape_and_p1_p3_guard`)
- **English**: Enforces pre-flash Tier-0 cold-backup integrity, SPACC cipher boundary, forbidden SPI NOR / repartitioning tool bans, reversible SD escape hatch, and `p1`/`p3` single-bank isolation, failing closed on:
  1. `BLOCKED_TIER0_COLD_BACKUP_RECEIPT_INVALID`: missing or unverified two-pass SHA-256 cold-backup receipt for `Sector 0` (`"8246"`/`"2.00"`), `p1` (`dat2=91030080`/`dat3`), `p2` (`Backup.bin`/`psd.bin`/`defdet.bin`), `p6`, `p12`, `p18` (`lensfile.bin`), or SPI NOR `ddrtraining.dat` `@ 0x3e210fc`.
  2. `BLOCKED_RAW_PNFLASHA_OR_FORBIDDEN_FLASH_TOOL`: any write to raw `/dev/pnflashaN` on `type=5, flag=1` encrypted partitions (`p3`, `p7`, `p8`, `p12`, `p15`, `p23`, `p30`) instead of `/dev/nflashaN` / `/dev/cnflashaN`, or any invocation of `nor_loader_writer.sh`, `us_spi_firmup.sh` (`mew.bin`), `us_darwin_firm.sh` (`darwin` ND), or `edisx.elf` Sector-0 repartitioning.
  3. `BLOCKED_SD_ESCAPE_HATCH_MISSING_OR_SLOW`: missing/unverified SD escape hatch (`eject SD card -> 47 us bypass` to stock `/usr/bin/im.elf.orig`, `< 50 ms`).
  4. `BLOCKED_P1_P3_MUTUAL_EXCLUSION_OR_UART_TRAP`: simultaneous `p1` and `p3` modification in the same transaction, `p1` `kemco.txt` `cfg.uart != 1`, or missing line-1 `rm -f /setting/updater/mode* && sync`.
- **中文摘要**：为真机双启动与镜像/恢复链路设立四重强制门禁：
  1. 未集齐经双遍 SHA-256 核验的 **Tier-0 完整冷备份回执**（`Sector 0` `"8246"`/`"2.00"`、`p1` `dat2=91030080`/`dat3`、`p2` `Backup.bin`/`psd.bin`/`defdet.bin`、`p6`、`p12`、`p18` `lensfile.bin`、SPI NOR `ddrtraining.dat @ 0x3e210fc`）直接阻断；
  2. 对 `type=5, flag=1` 加密分区（`p3, p7, p8, p12, p15, p23, p30`）强制走 SPACC 透明加密块设备 `/dev/nflashaN` / `/dev/cnflashaN`，**硬阻断**明文写 `/dev/pnflashaN`、SPI NOR 覆写脚本 `nor_loader_writer.sh`、`us_spi_firmup.sh`（`mew.bin`）、`us_darwin_firm.sh` 与 `edisx.elf` 重分区；
  3. 强制启用 **SD 卡物理逃生门**（拔卡 `47 us` 秒退回原厂 `/usr/bin/im.elf.orig`，`< 50 ms`）；
  4. 强制 **`p1` 与 `p3` 单次事务互斥律**，并锁死 `p1` `kemco.txt` `cfg.uart=1` 与首行 `rm -f /setting/updater/mode* && sync`。

### 1.4 Unified 44-Gate Master Safety Preflight (`evaluate_44gate_preflight` / `verify-44-gates`)
- Composes `evaluate_42gate_preflight` (`G01..G42`) with `G43` and `G44`:
  - **Offline default mode / 离线默认模式**: `41/44` gates pass (`offline_41_gates_verified = True`, `G10..G12` remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED`, `overall_ready_for_hardware_attach = False`).
  - **`--dry-run-simulated-backup` rehearsal mode / 仿真备份演练模式**: `44/44` simulation gates pass (`all_44_gates_verified = True`, `dry_run_rehearsal_only = True`), while `overall_ready_for_hardware_attach = False`, `persistent_emmc_writes_authorized = False`, and `persistent_write_release = False` remain hard-locked.

---

## 2. Verification Receipts / 实测验证回执

| Command / 命令 | Mode / 模式 | Result / 结果 | Duration / 耗时 |
| :--- | :--- | :--- | :---: |
| `PYTHONPATH=outputs/fx3-safety PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_realhw_jiritsu_cnflasha_and_44gate_guard.py -v` | Local Donor (`os.O_RDONLY`) | `44/44` passed (`OK`) | `2.176s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-safety PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_realhw_jiritsu_cnflasha_and_44gate_guard.py -v` | Clean-Room (`FX3_FX6_FORCE_CLEAN_ROOM=1`) | `44/44` passed (`OK`) | `2.080s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | Full Suite (Local Donor) | `751/751` passed (`OK`) | `11.738s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | Full Suite (Clean-Room) | `751` run, `750` passed, `1` skipped (`OK`) | `10.907s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure /usr/bin/python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -p "test_phase130_*.py"` | Phase 130 Cross-Check | `42/42` passed (`OK`) | `4.225s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-g43-jiritsu-service` | CLI Gate G43 (`LOCAL_DONOR_O_RDONLY`) | `status=VERIFIED_ADJUSTCONTROL_JIRITSU_ELECTRICAL_JBUSY_AND_P6_QUOTA_SAFE`, `valid=True`, `soc=85.0%`, `jbusy=0x11`, `p6_peak=10032B`, `persistent_emmc_writes_authorized=False` | `<0.3s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-g44-cnflasha-dualboot` | CLI Gate G44 (`LOCAL_DONOR_O_RDONLY`) | `status=VERIFIED_CNFLASHA_SPACC_TIER0_SD_ESCAPE_AND_P1_P3_MUTEX_SAFE`, `valid=True`, `dev=/dev/cnflasha15`, `sd_escape_us=47.0`, `p1_uart=1`, `persistent_emmc_writes_authorized=False` | `<0.3s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-44-gates` | CLI Offline Default (`LOCAL_DONOR_O_RDONLY`) | `status=VERIFIED_41_OF_44_AWAITING_PHYSICAL_TIER0`, `verified=41/44`, `g43_to_g44_all_passed=True`, `overall_ready_for_hardware_attach=False`, `persistent_emmc_writes_authorized=False` | `<0.3s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-44-gates --clean-room --dry-run-simulated-backup` | CLI Clean-Room Dry-Run Simulated Backup | `status=VERIFIED_ALL_44_GATES_DRY_RUN_SIMULATED_BACKUP`, `verified=44/44`, `g43_to_g44_all_passed=True`, `all_44_gates_verified=True`, `dry_run_rehearsal_only=True`, `overall_ready_for_hardware_attach=False`, `persistent_emmc_writes_authorized=False` | `<0.3s` |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-42-gates` & `verify-40-gates` | Backward-Compat CLI Check | `verified=39/42` & `verified=37/40`, `persistent_emmc_writes_authorized=False` | `<0.4s` |
| `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | Repo Clean-Room Hygiene Audit | `ALL GREEN` (`CLEAN`) | `1.30s` |

---

## 3. Owned Files Touched / 本阶段专有文件清单 (6 Files)

1. `outputs/fx3-safety/fx3_safety/realhw_jiritsu_cnflasha_and_44gate_guard.py`
2. `outputs/fx3-safety/fx3_safety/__init__.py`
3. `outputs/fx3-safety/fx3_safety/__main__.py`
4. `outputs/fx3-safety/README.md`
5. `outputs/fx3-safety/tests/test_realhw_jiritsu_cnflasha_and_44gate_guard.py`
6. `reports/2026-11-14-phase142-safety-realhw-jiritsu-cnflasha-44gates/README.md`
