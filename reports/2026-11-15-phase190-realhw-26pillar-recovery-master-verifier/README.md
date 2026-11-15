# Phase 190（Pillar 26 `26/26` / `verify-26pillar-recovery` 统一恢复总检）：`ILME-FX3` vs `ILME-FX3A` 跨分支恢复防火墙、`CAMSET` 设置隔离与 `XLR-H1` MI 热靴音频卫生护栏

## 1. 核心结论

- **交付闭环**：在 [`outputs/fx3-recovery-adapter/`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h207-phase190-pillar26-26pillar-recovery-master/outputs/fx3-recovery-adapter) 落地 Phase 190 **Pillar 26**（`ILME-FX3` vs `ILME-FX3A` 跨分支恢复/`CAMSET` 防火墙与 `XLR-H1` MI 热靴 4ch/24bit 音频卫生）及 **统一 26 支柱恢复总检聚合器（`verify-26pillar-recovery` / `verify-fx3a-branch-recovery-firewall`）**，同时保持 [`realhw_22pillar_master_recovery_verifier.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h207-phase190-pillar26-26pillar-recovery-master/outputs/fx3-recovery-adapter/fx3_recovery/realhw_22pillar_master_recovery_verifier.py)（`evaluate_22pillar_recovery_master` / `verify-22pillar-recovery`）与 [`realhw_24pillar_master_recovery_verifier.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h207-phase190-pillar26-26pillar-recovery-master/outputs/fx3-recovery-adapter/fx3_recovery/realhw_24pillar_master_recovery_verifier.py)（`evaluate_24pillar_recovery_master` / `verify-24pillar-recovery`）100% 完整向后兼容。
- **硬锁定安全底线**：全程强制 `persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`isp_write_authorized = False`、`otp_fuse_touches = 0`、`rpmb_counter_increments = 0`、`physical_usb_packets_emitted = 0`、`physical_device_writes = 0`、`raw_firmware_bytes_leaked = 0`。
- **实测事实与未执行真机动作边界**：本任务全部测试与 CLI 结果均基于**受控本地 `O_RDONLY` 有界只读审计**（`os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK`）与**洁净室确定性仿真**（`CLEAN_ROOM_SYNTHETIC`）；**未连接或写入任何真实物理 Sony `ILME-FX3` / `ILME-FX3A` 相机或 `XLR-H1` 手柄，未向真实机身或 SD 卡刷写 `BODYDATA.DAT`、`CAMSET01..10.DAT` 或 `Backup.bin`，未执行任何真实 USB/UART 发射或 eMMC/SPI-NOR 写入**。

## 2. 交付文件清单（严格仅 6 项归属文件）

| 类型 | 交付文件 | 说明 |
|---|---|---|
| 新增核心模块 | [`realhw_26pillar_master_recovery_verifier.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h207-phase190-pillar26-26pillar-recovery-master/outputs/fx3-recovery-adapter/fx3_recovery/realhw_26pillar_master_recovery_verifier.py) | `O_RDONLY` 有界供体审计 [`inspect_phase190_donors_readonly`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h207-phase190-pillar26-26pillar-recovery-master/outputs/fx3-recovery-adapter/fx3_recovery/realhw_26pillar_master_recovery_verifier.py#L602-L905)、Pillar 26A [`evaluate_fx3a_branch_recovery_firewall`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h207-phase190-pillar26-26pillar-recovery-master/outputs/fx3-recovery-adapter/fx3_recovery/realhw_26pillar_master_recovery_verifier.py#L909-L1062)、Pillar 26B [`evaluate_xlrh1_mishoe_audio_hygiene`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h207-phase190-pillar26-26pillar-recovery-master/outputs/fx3-recovery-adapter/fx3_recovery/realhw_26pillar_master_recovery_verifier.py#L1281-L1414) 与 `26/26` 聚合器 [`evaluate_26pillar_recovery_master`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h207-phase190-pillar26-26pillar-recovery-master/outputs/fx3-recovery-adapter/fx3_recovery/realhw_26pillar_master_recovery_verifier.py#L1673-L1889) |
| 更新包导出 | [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h207-phase190-pillar26-26pillar-recovery-master/outputs/fx3-recovery-adapter/fx3_recovery/__init__.py#L5001-L5050) | 无冲突导出 Phase 190 / Pillar 26 / `evaluate_26pillar_recovery_master` 全部公开符号，零覆盖既有 Pillar 22/24/25 接口 |
| 更新 CLI | [`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h207-phase190-pillar26-26pillar-recovery-master/outputs/fx3-recovery-adapter/fx3_recovery/__main__.py#L214-L221) | 新增 `verify-fx3a-branch-recovery-firewall` 与 `verify-26pillar-recovery`（支持 `--force-clean-room` / `--clean-room`、`--json`、`--out`） |
| 更新文档 | [`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h207-phase190-pillar26-26pillar-recovery-master/outputs/fx3-recovery-adapter/README.md#L646-L660) | 补充 Phase 190 Pillar 26 与 `26/26` 恢复总检说明及 CLI 示例 |
| 新增单元测试 | [`test_realhw_26pillar_master_recovery_verifier.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h207-phase190-pillar26-26pillar-recovery-master/outputs/fx3-recovery-adapter/tests/test_realhw_26pillar_master_recovery_verifier.py) | 50 项双模式（`LOCAL_DONOR_O_RDONLY` + `FX3_FX6_FORCE_CLEAN_ROOM=1`）单元测试（含 `< 6.0s` 并发防护上限与故障注入） |
| 阶段报告 | [`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h207-phase190-pillar26-26pillar-recovery-master/reports/2026-11-15-phase190-realhw-26pillar-recovery-master-verifier/README.md) | 本报告 |

## 3. 已验证事实 vs 未执行真机动作边界

### 3.1 已完成验证（`O_RDONLY` 供体审计与洁净室仿真）

1. **FX3 `7.02` 与 `XLR-H1` 相关本地供体有界 `O_RDONLY` 审计（`6` 项文件，零原始固件字节泄露）**：
   - `fx3-7.02-BODYDATA.DAT`（`811,876,768 B`，有界 `4 KiB` 头 SHA-256 `fc135914e076...`，`\x89UFU\r\n\x1a\n` 与 `DATV`/`PROV`/`UDID` 标记校验通过）。
   - `nflasha8/cpapp-b.bin`（`15,980,568 B`，有界 `4 KiB` 头 SHA-256 `452c9e4e05fc...`）。
   - `nflasha15/lib/appFw.so`（`79,015,712 B`，ELF64 AArch64 `e_machine=183`，有界 `4 KiB` 头 SHA-256 `de3201c6615a...`）。
   - `FX3-CX95900_ALLLANG-Backup.bin`（`2,229,740 B`，`BK4\x00` + `0xAAAAAAAA` + `ILME-FX3`，SHA-256 `bf3a9d851f98...`）。
   - `partinf.conf`（`3,999 B`，30 分区含 `p2:/setting` 与 `p15:/usr`，SHA-256 `3d96228d4ed2...`）。
   - `libInfraHotshoe.so`（`47,808 B`，ELF64 AArch64 `e_machine=183`，SHA-256 `0bf55367c034...`）。
2. **Pillar 26A — `ILME-FX3`（`Ver. 7.02`，`1.44M` LCD + NFC + IR）vs `ILME-FX3A`（`Ver. 2.02`，`2.36M` XGA LCD，无 NFC/IR）恢复与 `CAMSET` 防火墙（`6/6`）**：
   - 校验 `< 50 us` 预检机制：仅放行 `ILME-FX3`（`0x91030080`，`1,440,000`-dot LCD + NFC + IR，`Ver. 7.02`）与同源 FX3 恢复包及 `p2:/setting/Backup.bin`（`H0 == H3`、`BLKROSET=1`）；
   - 双向拦截 `FX3A`（`Ver. 1.xx/2.xx` / `2,359,296`-dot XGA LCD / 无 NFC/IR）、`FX30`（`0x91030084`）与 `FX6`（`0x91020080`）的 `BODYDATA.DAT` 恢复包与显示垫片混用；
   - 双向拦截 `FX3` 与 `FX3A` 之间的 `CAMSET01.DAT`..`CAMSET10.DAT` SD 卡设置导入，防止跨支线 LCD/NFC/IR 标定与配置污染。
3. **Pillar 26B — `XLR-H1` MI 热靴 `48kHz/24bit 4ch` 恢复后与 UFU 升级后音频卫生护栏（`6/6`）**：
   - 验证 `XLR-H1` `48kHz/24bit 4ch`（`IN1/IN2 -> CH1/CH2`、`IN3 -> CH3/CH4`）、`24bit 2ch` 与 `16bit 2ch` 路由矩阵及 `CH1_2` / `CH3_4` / `CH1+3_CH2+4` 耳机监听模式；
   - 强制零独立手柄固件写入（`P190_XLRH1_STANDALONE_FW_SHIPPED = False`），拦截伪造 `XLR-H1` 固件写入企图；
   - 校验冷启动恢复期机身 `3.5mm` 麦克风插孔物理抢占安全（触发 `[MI Shoe Audio Set.]` 物理屏蔽时保持静默安全，若期待 MI 热靴激活则阻断进入）、`S&Q` 静音一致性及 Stage-A -> Stage-B `+48V` 幻象供电零毛刺；
   - 审计 `BODYDATA.DAT` UFU 升级后自动重置为 `48kHz/16bit 2ch` 的默认行为，且 Stage-B 全程零污染 `p2:/setting/Backup.bin`（`stage_b_backup_bin_writes == 0`、`H0 == H3`）。
4. **统一 `26/26` 恢复总检聚合器（`evaluate_26pillar_recovery_master`）**：
   - 并发调度 [`evaluate_24pillar_recovery_master`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h207-phase190-pillar26-26pillar-recovery-master/outputs/fx3-recovery-adapter/fx3_recovery/realhw_24pillar_master_recovery_verifier.py)（`Pillars 1..24`）+ **Pillar 25**（[`run_airgap_sd_bundle_manifest_suite`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h207-phase190-pillar26-26pillar-recovery-master/outputs/fx3-recovery-adapter/fx3_recovery/realhw_airgap_sd_bundle_manifest_verifier.py)）+ **Pillar 26**（[`run_pillar26_standalone_suite`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h207-phase190-pillar26-26pillar-recovery-master/outputs/fx3-recovery-adapter/fx3_recovery/realhw_26pillar_master_recovery_verifier.py#L1581-L1653)），在 `< 2.0s` 名义预算与 `< 6.0s` 并发单测上限内稳定产出 **`26/26`**（`VERIFIED_26OF26_PILLAR_RECOVERY_MASTER`）；对 Pillar 1、Pillar 25、Pillar 26 故障注入均 100% fail-closed 降级为 `25/26`。

### 3.2 未执行物理相机台架动作（BLOCKED / NOT EXECUTED）

- **未在真实物理 `ILME-FX3` / `ILME-FX3A` / `XLR-H1` 硬件上执行**：未插卡刷写任何真实 `BODYDATA.DAT`、未导入真实 SD 卡 `CAMSET01..10.DAT`、未插拔真实 `XLR-H1` 或 `3.5mm` 麦克风采集硬件音频或 `+48V` 电压，亦未开启任何物理 eMMC / SPI-NOR / USB / UART / OTP / RPMB 写授权。

## 4. 实测验证命令与结果

| 验证项 | 模式 | 实测结果 |
|---|---|---|
| `verify-fx3a-branch-recovery-firewall --json` | `LOCAL_DONOR_O_RDONLY` | `status=VERIFIED_PILLAR26_FX3A_BRANCH_FIREWALL_AND_XLRH1_HYGIENE`、`all_passed=True`、`elapsed_seconds=0.002949`、`suite_sha256=7d0b852f340f4dbe...` |
| `verify-26pillar-recovery --json` | `LOCAL_DONOR_O_RDONLY` | `status=VERIFIED_26OF26_PILLAR_RECOVERY_MASTER`、`all_passed=True`、`pillars=26/26`、`elapsed_seconds=1.096665`（`nominal_under_2s=True`、`under_6s_budget=True`）、`master_26pillar_sha256=591cea714ef620f6...` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 ... verify-26pillar-recovery --force-clean-room --json` | `CLEAN_ROOM_SYNTHETIC` | `status=VERIFIED_26OF26_PILLAR_RECOVERY_MASTER`、`all_passed=True`、`pillars=26/26`、`elapsed_seconds=1.193123`（`nominal_under_2s=True`、`under_6s_budget=True`）、`master_26pillar_sha256=6280472e062d0348...` |
| `test_realhw_26pillar_master_recovery_verifier.py` | 默认（`LOCAL_DONOR_O_RDONLY`） | `Ran 50 tests in 14.001s — OK` |
| `test_realhw_26pillar_master_recovery_verifier.py` | `FX3_FX6_FORCE_CLEAN_ROOM=1` | `Ran 50 tests in 14.225s — OK (skipped=1)`（仅按预期跳过依赖本地供体的 `test_06`） |
| `unittest discover -s outputs/fx3-recovery-adapter/tests -p "test_*.py"` | 默认（`LOCAL_DONOR_O_RDONLY`） | `Ran 1169 tests in 151.314s`：Phase 190 `50/50` 与 Phase 166/180/184 全通；仅既有 `test_recovery_master_suite_and_uart_decoder.py::test_25` 在全量并发负载下报 `1.173267 not less than 1.0`（单跑 `34/34` `0.922s` 通过） |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 ... unittest discover -s outputs/fx3-recovery-adapter/tests -p "test_*.py"` | `CLEAN_ROOM_SYNTHETIC` | `Ran 1111 tests in 120.031s — OK (skipped=13)` |
| `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | 仓库洁净度审计 | `[hygiene] git status --porcelain binary/pyc audit: CLEAN (0.05s)`，`ALL GREEN in 0.05s` |
