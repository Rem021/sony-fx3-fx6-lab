# Phase 180（Pillar 24 `24/24` / 统一恢复总检）：Slot-1 `BODYDATA.DAT`（`>= 2.04` 底线）原厂回刷就绪度、HDMI-BRAW / `WPA3` 回退卫生与 `verify-24pillar-recovery`

## 1. 核心结论

- **交付闭环**：在 [`outputs/fx3-recovery-adapter/`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h196-phase180-pillar24-24pillar-recovery-master/outputs/fx3-recovery-adapter) 落地 Phase 180 **Pillar 24** 与 **统一 24 支柱恢复总检聚合器（`verify-24pillar-recovery` / `verify-slot1-ufu-reflash-readiness`）**，同时保留 [`realhw_22pillar_master_recovery_verifier.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h196-phase180-pillar24-24pillar-recovery-master/outputs/fx3-recovery-adapter/fx3_recovery/realhw_22pillar_master_recovery_verifier.py)（`evaluate_22pillar_recovery_master` / `verify-22pillar-recovery`）100% 完整向后兼容。
- **硬锁定安全底线**：全程强制 `persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`isp_write_authorized = False`、`otp_fuse_touches = 0`、`rpmb_counter_increments = 0`、`physical_usb_packets_emitted = 0`、`physical_device_writes = 0`、`raw_firmware_bytes_leaked = 0`。
- **事实与未执行动作边界**：本任务全部测试与 CLI 结果均基于**受控本地 `O_RDONLY` 有界只读审计**（`os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK`）与**洁净室确定性仿真**（`CLEAN_ROOM_SYNTHETIC`）；**未连接或写入任何真实物理 Sony ILME-FX3 相机、未向真实 SD 卡或机身下发 `BODYDATA.DAT` 刷写或 `WPA2/WPA3`/HDMI-BRAW/LUT 配置、未执行任何真实 USB/UART 发射或 eMMC/SPI-NOR 写入**。

## 2. 交付文件清单（严格仅 6 项归属文件）

| 类型 | 交付文件 | 说明 |
|---|---|---|
| 新增核心模块 | [`realhw_24pillar_master_recovery_verifier.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h196-phase180-pillar24-24pillar-recovery-master/outputs/fx3-recovery-adapter/fx3_recovery/realhw_24pillar_master_recovery_verifier.py) | `O_RDONLY` 有界供体审计 [`inspect_phase180_donors_readonly`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h196-phase180-pillar24-24pillar-recovery-master/outputs/fx3-recovery-adapter/fx3_recovery/realhw_24pillar_master_recovery_verifier.py#L618-L824)、Pillar 24A [`evaluate_slot1_ufu_stock_reflash_readiness`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h196-phase180-pillar24-24pillar-recovery-master/outputs/fx3-recovery-adapter/fx3_recovery/realhw_24pillar_master_recovery_verifier.py#L830-L953)、Pillar 24B [`evaluate_volatile_network_braw_lut_hygiene`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h196-phase180-pillar24-24pillar-recovery-master/outputs/fx3-recovery-adapter/fx3_recovery/realhw_24pillar_master_recovery_verifier.py#L1063-L1150) 与 24/24 聚合器 [`evaluate_24pillar_recovery_master`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h196-phase180-pillar24-24pillar-recovery-master/outputs/fx3-recovery-adapter/fx3_recovery/realhw_24pillar_master_recovery_verifier.py#L1343-L1525) |
| 更新包导出 | [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h196-phase180-pillar24-24pillar-recovery-master/outputs/fx3-recovery-adapter/fx3_recovery/__init__.py#L2279-L2375) | 无冲突导出 95 项 Phase 180 符号与模块引用，零覆盖既有安全常量与 Pillar 22/23 接口 |
| 更新 CLI | [`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h196-phase180-pillar24-24pillar-recovery-master/outputs/fx3-recovery-adapter/fx3_recovery/__main__.py#L941-L1000) | 新增 `verify-slot1-ufu-reflash-readiness` 与 `verify-24pillar-recovery`（支持 `--force-clean-room` / `--clean-room`、`--json`、`--out`） |
| 更新文档 | [`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h196-phase180-pillar24-24pillar-recovery-master/outputs/fx3-recovery-adapter/README.md#L610-L627) | 补充 Phase 180 Pillar 24 与 `24/24` 总检说明及 CLI 示例 |
| 新增单元测试 | [`test_realhw_24pillar_master_recovery_verifier.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h196-phase180-pillar24-24pillar-recovery-master/outputs/fx3-recovery-adapter/tests/test_realhw_24pillar_master_recovery_verifier.py) | 50 项双模式（`LOCAL_DONOR_O_RDONLY` + `FX3_FX6_FORCE_CLEAN_ROOM=1`）单元测试 |
| 阶段报告 | [`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h196-phase180-pillar24-24pillar-recovery-master/reports/2026-11-15-phase180-realhw-24pillar-recovery-master-verifier/README.md) | 本报告 |

## 3. 已验证事实 vs 未执行真机动作边界

### 3.1 已完成验证（`O_RDONLY` 供体审计与洁净室仿真）

1. **FX3 `7.02` 本地供体有界 `O_RDONLY` 审计（`6` 项文件，零原始固件字节泄露）**：
   - `fx3-7.02-BODYDATA.DAT`（`811,876,768 B`，有界 `4 KiB` 头 SHA-256 `fc135914e076...`，`\x89UFU\r\n\x1a\n`、`DATV`/`PROV`/`UDID` 标记校验通过）。
   - `nflasha5.img`（`209,112,512 B`，`WBI2\x00\x00\x00\x00` 前缀、`1399` 节区，头 SHA-256 `11ae397741d0...`、节表 SHA-256 `7286ddb05a73...`）。
   - `nflasha15.img`（`479,846,400 B`，有界 `4 KiB` 超级块 `ext2 0xEF53`，SHA-256 `6d05ebbd28c5...`）。
   - `partinf.conf`（`3,999 B`，30 分区含 `p12:/cert`、`p15:/usr`、`p30:/usr/data/lut`）、`mount.conf`（`1,248 B`）、`FX3-CX95900_ALLLANG-Backup.bin`（`2,229,740 B`，`BK4\x00` + `0xAAAAAAAA` + `ILME-FX3`，SHA-256 `bf3a9d851f98...`）。
2. **Pillar 24A — Slot-1 `BODYDATA.DAT`（`811,876,768 B`）卸载后回刷就绪度（`6/6`）**：
   - 验证 `H2 -> H3` 净卸载后机身固件 `>= Ver. 2.04` 底线（拦截 `<= Ver. 2.02` 以规避 `7 long + 7 short` LED 错误）、仅放行 Slot-1 ExFAT 根目录 `/BODYDATA.DAT`（拦截 Slot-2、子目录及 `BODYDATA (1).DAT`/`BODYDATA_OLD.DAT`）、`p1` 更新标志为 `0`、`p15:/usr` `.orig` 与 `p5:/wbi` `WBI2\x00\x00\x00\x00` `H0 == H3`、`NP-FZ100` `>= 3 格 / >= 7.20V`，以及 `p12:/cert/RQ_LIC.DAT` C2PA `<= 100` 上限与 `RO` 只读不变性。
3. **Pillar 24B — 挥发网络（仅 `WPA2/WPA3`）与 HDMI-BRAW / `.cube` 3D LUT 回退卫生（`6/6`）**：
   - 验证仅允许 `WPA2`/`WPA3`/`Access Authentication`（阻断 `WEP`/`WPA1`/`LEGACY_IPSEC`），并确认 Stage-B `tmpfs` Wi-Fi 凭据、`.cube` LUT 暂存与 HDMI BRAW 状态在 `EH1` 与 `H2 -> H3` 后零残留泄露至 `p2:/setting/Backup.bin` 或 `p30:/usr/data/lut`（`H0 == H3`）。
4. **统一 24/24 恢复总检聚合器（`evaluate_24pillar_recovery_master`）**：
   - 并发聚合 Pillars `1..22` + Pillar 23 + Pillar 24，在 `< 1.8s` 名义预算内产出 `24/24`（`VERIFIED_24OF24_PILLAR_RECOVERY_MASTER`）；故障注入测试验证对 Pillar 1、Pillar 23、Pillar 24 均 100% fail-closed 降级为 `23/24`（退出码 `2`）。

### 3.2 未执行物理相机台架动作（BLOCKED / NOT EXECUTED）

- **未在真实物理 ILME-FX3 相机上执行**：未插卡向真实相机执行 Slot-1 `BODYDATA.DAT` 刷写、未读取真实机身电池电压/序列号或 `p12:/cert/RQ_LIC.DAT` 实机扇区、未真机切换 `WPA2/WPA3` 或录制 HDMI BRAW 后实际验证 `p2:/setting/Backup.bin`，亦未开启任何物理设备写授权。

## 4. 实测验证命令与结果

| 验证项 | 模式 | 实测结果 |
|---|---|---|
| `verify-24pillar-recovery --json` | `LOCAL_DONOR_O_RDONLY` | `status=VERIFIED_24OF24_PILLAR_RECOVERY_MASTER`、`all_passed=True`、`pillars=24/24`、`elapsed_seconds=1.5736`（`nominal_under_1_8s=True`）、`master_24pillar_sha256=e93c663d69042e3c...` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 ... verify-24pillar-recovery --json` | `CLEAN_ROOM_SYNTHETIC` | `status=VERIFIED_24OF24_PILLAR_RECOVERY_MASTER`、`all_passed=True`、`pillars=24/24`、`elapsed_seconds=0.853842`（`nominal_under_1_8s=True`）、`master_24pillar_sha256=5512359beec4edcb...` |
| `verify-slot1-ufu-reflash-readiness` | `LOCAL_DONOR_O_RDONLY` | `status=VERIFIED_PILLAR24_SLOT1_UFU_REFLASH_AND_HYGIENE`、`pillar_24a=6/6`、`pillar_24b=6/6`、`elapsed_seconds=0.004` |
| `test_realhw_24pillar_master_recovery_verifier.py` | 默认（`LOCAL_DONOR_O_RDONLY`） | `Ran 50 tests in 11.773s — OK` |
| `test_realhw_24pillar_master_recovery_verifier.py` | `FX3_FX6_FORCE_CLEAN_ROOM=1` | `Ran 50 tests in 14.206s — OK (skipped=1)`（仅跳过依赖本地供体的 `test_06`） |
| `unittest discover -s outputs/fx3-recovery-adapter/tests -p "test_*.py"` | 默认（`LOCAL_DONOR_O_RDONLY`） | `Ran 1069 tests in 154.827s`：Phase 180 `50/50` 与 Phase 166 `50/50` 全通；仅既有 `test_recovery_master_suite_and_uart_decoder.py::test_25` 在全量并发负载下报 `1.660608 not less than 1.0`（单跑 `34/34` `0.858s` 通过） |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 ... unittest discover` | `CLEAN_ROOM_SYNTHETIC` | `Ran 1011 tests in 117.881s`（`skipped=11`）：Phase 180 与 Phase 166 均通过；同上仅既有 `test_25` 在并发负载下报 `1.943277 not less than 1.0` |
| `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | 仓库洁净度审计 | `[hygiene] git status --porcelain binary/pyc audit: CLEAN (0.06s)`，`ALL GREEN in 0.06s` |
