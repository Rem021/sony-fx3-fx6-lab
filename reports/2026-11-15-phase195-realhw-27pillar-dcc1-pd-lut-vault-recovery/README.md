# Phase 195（Pillar 27 `27/27` / `verify-27pillar-recovery` 统一恢复总检）：`DC-C1`（`>=65W / 5A`）与 `NP-FZ100` 欠压互锁、双介质 `.cube` User LUT `p2:/setting` 金库隔离

## 1. 核心结论

- **交付闭环**：在 [`outputs/fx3-recovery-adapter/`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h213-phase195-pillar27-27pillar-dcc1-lut-vault-recovery/outputs/fx3-recovery-adapter) 落地 Phase 195 **Pillar 27**（`NP-FZ100` / `DC-C1` 冷备份与 UFU 欠压恢复互锁 + 双介质 `.cube` User LUT `p2:/setting` 金库隔离）及 **统一 27 支柱恢复总检聚合器（`verify-27pillar-recovery` / `verify-dcc1-pd-lut-vault`）**，同时保持 [`realhw_22pillar_master_recovery_verifier.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h213-phase195-pillar27-27pillar-dcc1-lut-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/realhw_22pillar_master_recovery_verifier.py)（`verify-22pillar-recovery`）、[`realhw_24pillar_master_recovery_verifier.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h213-phase195-pillar27-27pillar-dcc1-lut-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/realhw_24pillar_master_recovery_verifier.py)（`verify-24pillar-recovery`）与 [`realhw_26pillar_master_recovery_verifier.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h213-phase195-pillar27-27pillar-dcc1-lut-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/realhw_26pillar_master_recovery_verifier.py)（`verify-26pillar-recovery`）100% 向后兼容。
- **硬锁定安全底线**：全程强制 `persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`isp_write_authorized = False`、`persistent_write_release = False`、`live_usb_iokit_transmit_enabled = False`、`otp_fuse_touches = 0`、`rpmb_counter_increments = 0`、`physical_usb_packets_emitted = 0`、`physical_device_writes = 0`、`raw_firmware_bytes_leaked = 0`。
- **实测事实与未执行真机动作边界**：本任务全部验证均基于**受控本地 `O_RDONLY` 有界只读审计**（`os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK`）与**洁净室确定性仿真**（`CLEAN_ROOM_SYNTHETIC`）；**未连接、供电、插卡或写入任何真实物理 Sony `ILME-FX3` 相机、`DC-C1` 电源耦合器或 `NP-FZ100` 电池，未向真实机内 eMMC / SPI-NOR / USB / UART 发出任何物理数据包或写指令**。

## 2. 交付文件清单（严格仅 6 项归属文件）

| 类型 | 交付文件 | 说明 |
|---|---|---|
| 新增核心模块 | [`realhw_27pillar_dcc1_pd_lut_vault_verifier.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h213-phase195-pillar27-27pillar-dcc1-lut-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/realhw_27pillar_dcc1_pd_lut_vault_verifier.py) | `O_RDONLY` 有界供体审计 [`inspect_phase195_donors_readonly`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h213-phase195-pillar27-27pillar-dcc1-lut-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/realhw_27pillar_dcc1_pd_lut_vault_verifier.py#L681-L982)、Pillar 27A [`evaluate_dcc1_power_brownout_interlock`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h213-phase195-pillar27-27pillar-dcc1-lut-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/realhw_27pillar_dcc1_pd_lut_vault_verifier.py#L989-L1119)、Pillar 27B [`evaluate_dual_media_cube_lut_vault`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h213-phase195-pillar27-27pillar-dcc1-lut-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/realhw_27pillar_dcc1_pd_lut_vault_verifier.py#L1344-L1486) 与 `27/27` 聚合器 [`evaluate_27pillar_recovery_master`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h213-phase195-pillar27-27pillar-dcc1-lut-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/realhw_27pillar_dcc1_pd_lut_vault_verifier.py#L1781-L1944) |
| 更新包导出 | [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h213-phase195-pillar27-27pillar-dcc1-lut-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/__init__.py#L5203-L5307) | 无冲突导出 Phase 195 / Pillar 27 / `evaluate_27pillar_recovery_master` 全部公开符号，零覆盖既有 Pillar 22/24/25/26 接口 |
| 更新 CLI | [`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h213-phase195-pillar27-27pillar-dcc1-lut-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/__main__.py#L226-L233) | 新增 [`verify-dcc1-pd-lut-vault`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h213-phase195-pillar27-27pillar-dcc1-lut-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/__main__.py#L1120-L1147) 与 [`verify-27pillar-recovery`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h213-phase195-pillar27-27pillar-dcc1-lut-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/__main__.py#L1148-L1178)（支持 `--force-clean-room` / `--clean-room`、`--json`、`--out`） |
| 更新文档 | [`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h213-phase195-pillar27-27pillar-dcc1-lut-vault-recovery/outputs/fx3-recovery-adapter/README.md#L665-L685) | 补充 Phase 195 Pillar 27 与 `27/27` 恢复总检说明及 CLI 示例 |
| 新增单元测试 | [`test_realhw_27pillar_dcc1_pd_lut_vault_verifier.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h213-phase195-pillar27-27pillar-dcc1-lut-vault-recovery/outputs/fx3-recovery-adapter/tests/test_realhw_27pillar_dcc1_pd_lut_vault_verifier.py) | 50 项双模式（`LOCAL_DONOR_O_RDONLY` + `FX3_FX6_FORCE_CLEAN_ROOM=1`）快速单元测试（含 `< 6.0s` 并发防护上限与故障注入） |
| 阶段报告 | [`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h213-phase195-pillar27-27pillar-dcc1-lut-vault-recovery/reports/2026-11-15-phase195-realhw-27pillar-dcc1-pd-lut-vault-recovery/README.md) | 本报告 |

## 3. 已验证事实 vs 未执行真机动作边界

### 3.1 已完成验证（`O_RDONLY` 供体审计与洁净室仿真）

1. **FX3 `7.02` 与 `libUsbBusPower.so` 本地供体有界 `O_RDONLY` 审计（`6` 项文件，零原始固件字节泄露）**：
   - `fx3-7.02-BODYDATA.DAT`（`811,876,768 B`，有界 `4 KiB` 头 SHA-256 `fc135914e076...`，`\x89UFU\r\n\x1a\n` 与 `DATV`/`PROV`/`UDID` 标记校验通过）。
   - `nflasha8/cpapp-b.bin`（`15,980,568 B`，有界 `4 KiB` 头 SHA-256 `452c9e4e05fc...`）。
   - `nflasha15/lib/appFw.so`（`79,015,712 B`，ELF64 AArch64 `e_machine=183`，有界 `4 KiB` 头 SHA-256 `de3201c6615a...`）。
   - `FX3-CX95900_ALLLANG-Backup.bin`（`2,229,740 B`，`BK4\x00` + `0xAAAAAAAA` + `ILME-FX3`，SHA-256 `bf3a9d851f98...`）。
   - `partinf.conf`（`3,999 B`，30 分区含 `p2:/setting` 与 `p15:/usr`，SHA-256 `3d96228d4ed2...`）。
   - `libUsbBusPower.so`（`48,232 B`，ELF64 AArch64 `e_machine=183`，导出了 `_ZN11UsbBusPower11IsVbusReadyEv`、`_ZN11UsbBusPower19GetCurrentBattStateEPi` 与 `_ZN11UsbBusPower22SetPowerContractStatusEi`，SHA-256 `c606880c92ec...`）。
2. **Pillar 27A — `NP-FZ100`（`>=51%` / `>=3 格`）与 `DC-C1`（`>=65W + 5A` e-Marked 线缆）冷备份与 UFU 欠压互锁（`6/6`）**：
   - `P27A1`..`P27A6`：进入冷备份 `AdjustControl (0x40)` 与 UFU `BODYDATA.DAT` 阶段前硬校验电源准入——机身 USB-C PD 必须装载物理 `NP-FZ100`（`>= 51%`、`>= 3 格`、`>= 7.20V`），硬拒 Micro-USB 供电企图，并要求 `DC-C1` 具备 `>= 65W` USB-PD + `5A` e-Marked 线缆且无供电异常闪烁告警；
   - 证明若 Stage-B 阶段 `DC-C1` 发生中途掉电，易失性内存覆盖层被干净清零、冷重启回原厂 FX3 `7.02`，且 **`16/16` Tier-0 关键表面保持零 eMMC 损伤（`H0 == H3`）**。
3. **Pillar 27B — 双介质 `.cube` User LUT（`User1..User16`）易失覆盖层 vs 原厂 `p2:/setting` 金库保全（`6/6`）**：
   - `P27B1`..`P27B6`：校验 `SDXC`（`/Private/Sony/PRO/LUT/`）与 `CFexpress Type A`（`/Sony/PRO/LUT/`）双介质目录路径非对称规则，以及 `17pt/33pt`（`LUT_3D_SIZE 17|33`）与 `<= 63B` ASCII `.cube` 文件名边界；
   - 强制 Stage-B 期间 LUT 暂存严格受限于易失 `/tmp/fx6_lut_overlay`（`tmpfs`），`stage_b_p2_setting_writes == 0`；
   - 证明重启回原厂 FX3 `7.02` 后 `p2:/setting/Backup.bin` 保持 `BLKROSET=1` 且 `User1..User16` 共 `16` 个注册槽位及 `AE Level Offset`（`0.0..+2.0 EV`、`1/3 EV` 步进）**100% 逐比特一致（`H0 == H3`）**。
4. **统一 `27/27` 恢复总检聚合器（`evaluate_27pillar_recovery_master`）**：
   - 并发调度 `evaluate_26pillar_recovery_master`（`Pillars 1..26`）+ **Pillar 27**（`run_pillar27_standalone_suite`），实测在 `< 2.2s` 名义预算与 `< 6.0s` 单测上限内稳定产出 **`27/27`**（`VERIFIED_27OF27_PILLAR_RECOVERY_MASTER`），对 Pillar 1、25、26、27 故障注入及子套件安全计数篡改均 100% fail-closed 降级为 `26/27`。

### 3.2 未执行物理相机台架动作（BLOCKED / NOT EXECUTED）

- **未在真实物理 `ILME-FX3` 机身、`DC-C1` 电源耦合器、`NP-FZ100` 电池或真实 SDXC / CFexpress Type A 存储卡上执行**：未进行真机供电接入、未触发真实冷备份 `AdjustControl (0x40)` 或 UFU `BODYDATA.DAT` 刷写、未实际向存储卡写入 `.cube` 文件，亦未开启任何物理 eMMC / SPI-NOR / USB / UART / OTP / RPMB 写授权。

## 4. 实测验证命令与结果

| 验证项 | 模式 | 实测结果 |
|---|---|---|
| `verify-dcc1-pd-lut-vault --json` | `LOCAL_DONOR_O_RDONLY` | `status=VERIFIED_PILLAR27_DCC1_PD_AND_CUBE_LUT_VAULT`、`all_passed=True`、`elapsed_seconds=0.003672`、`suite_sha256=f82c41912dd5a11f...`、`physical_device_writes=0` |
| `verify-27pillar-recovery --json` | `LOCAL_DONOR_O_RDONLY` | `status=VERIFIED_27OF27_PILLAR_RECOVERY_MASTER`、`all_passed=True`、`pillars=27/27`、`elapsed_seconds=2.066021`（`nominal_under_2_2s=True`、`under_6s_budget=True`）、`master_27pillar_sha256=3d5c16e38776d16b...` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 ... verify-27pillar-recovery --force-clean-room --json` | `CLEAN_ROOM_SYNTHETIC` | `status=VERIFIED_27OF27_PILLAR_RECOVERY_MASTER`、`all_passed=True`、`pillars=27/27`、`elapsed_seconds=0.826876`（`nominal_under_2_2s=True`、`under_6s_budget=True`）、`master_27pillar_sha256=3c170bf65fbc3466...` |
| `verify-22pillar-recovery` / `24pillar` / `26pillar --json` | `LOCAL_DONOR_O_RDONLY` | `22/22`、`24/24`、`26/26` 均返回 `all_passed=True`（100% 向后兼容） |
| `test_realhw_27pillar_dcc1_pd_lut_vault_verifier.py` | 默认（`LOCAL_DONOR_O_RDONLY`） | `Ran 50 tests in 20.586s — OK` |
| `test_realhw_27pillar_dcc1_pd_lut_vault_verifier.py` | `FX3_FX6_FORCE_CLEAN_ROOM=1` | `Ran 50 tests in 18.127s — OK (skipped=1)`（仅按预期跳过依赖本地供体的 `test_06`） |
| `unittest discover -s outputs/fx3-recovery-adapter/tests -p "test_*.py"` | 默认（`LOCAL_DONOR_O_RDONLY`） | `Ran 1219 tests in 170.338s`（`skipped=1`；Phase 195 `50/50` 与 Phase 166/180/184/190 全通；仅既有 `test_recovery_master_suite_and_uart_decoder.py::test_25` 在全量高并发负载下报 `1.515209 not less than 1.0`，单跑 `34/34` `0.869s` 通过） |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 ... unittest discover -s outputs/fx3-recovery-adapter/tests -p "test_*.py"` | `CLEAN_ROOM_SYNTHETIC` | `Ran 1161 tests in 142.460s`（`skipped=14`；Phase 195 `49/49+1 skip` 与 Phase 166/180/184/190 全通；仅同上既有 `test_25` 在全量负载下报 `1.17853 not less than 1.0`，单跑 `34/34` `0.844s` 通过） |
| `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | 仓库洁净度审计 | `[hygiene] git status --porcelain binary/pyc audit: CLEAN (0.03s)`，`ALL GREEN in 0.03s` |
