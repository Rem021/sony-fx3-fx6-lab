# Phase 176（Pillar 23 / 实机主线）：`p5:/wbi`（`WBI2` / `hibdrv.ko`）跨模式污染防火墙、突发断电恢复与 100 周期 `H0 -> H1 -> H2 -> H3` 不变性校验器

## 1. 核心结论

- **交付闭环**：在 [`outputs/fx3-recovery-adapter/`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h191-phase176-pillar23-wbi-powerloss-100cycle-recovery/outputs/fx3-recovery-adapter) 落地 Phase 176 Pillar 23，围绕 **Sony ILME-FX3（`Ver. 7.02`、`Linux 4.9.337-scel+`、`CXD90057` Mira）** 与可逆 SD 卡门控 `FX6_STAGEB` 双系统切换，交付 **Pillar 23A（`p5:/wbi` `WBI2` / `hibdrv.ko` 跨模式污染防火墙，8 场景）**、**Pillar 23B（突发 `NP-FZ100` 拔电池 / `6.3V` 欠压恢复与 100 周期 `H0 -> H1 -> H2 -> H3` 状态机仿真，8 场景 + 100 周期校验）** 及 CLI 子命令 **`verify-wbi-powerloss-recovery`**。
- **硬锁定安全底线**：全程强制 `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`ISP_WRITE_AUTHORIZED = False`、`OTP_FUSE_TOUCHES = 0`、`RPMB_COUNTER_INCREMENTS = 0`、`PHYSICAL_USB_PACKETS_EMITTED = 0`、`PHYSICAL_DEVICE_WRITES = 0`、`WBI_PERSISTENT_WRITES = 0`、`RAW_FIRMWARE_BYTES_LEAKED = 0`；未修改 [`realhw_22pillar_master_recovery_verifier.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h191-phase176-pillar23-wbi-powerloss-100cycle-recovery/outputs/fx3-recovery-adapter/fx3_recovery/realhw_22pillar_master_recovery_verifier.py)。
- **事实与未执行动作边界**：本任务全部测试与 CLI 输出均为**受控本地 `O_RDONLY` 只读检查**（`os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK`）与**洁净室确定性仿真**（`CLEAN_ROOM_SYNTHETIC`），**未对任何真实物理 ILME-FX3 相机执行拔电池、SD 插拔、USB/UART 发包、eMMC/NOR 写入或固件刷写**。

## 2. 交付文件清单（严格仅 6 项归属文件）

| 类型 | 交付文件 | 说明 |
|---|---|---|
| 新增核心模块 | [`realhw_wbi_powerloss_and_100cycle_transition_verifier.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h191-phase176-pillar23-wbi-powerloss-100cycle-recovery/outputs/fx3-recovery-adapter/fx3_recovery/realhw_wbi_powerloss_and_100cycle_transition_verifier.py) | `O_RDONLY` 供体审计 [`inspect_phase176_wbi_donors_readonly`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h191-phase176-pillar23-wbi-powerloss-100cycle-recovery/outputs/fx3-recovery-adapter/fx3_recovery/realhw_wbi_powerloss_and_100cycle_transition_verifier.py#L600-L999)、Pillar 23A [`run_pillar23a_wbi_contamination_firewall_suite`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h191-phase176-pillar23-wbi-powerloss-100cycle-recovery/outputs/fx3-recovery-adapter/fx3_recovery/realhw_wbi_powerloss_and_100cycle_transition_verifier.py#L1240-L1451)、Pillar 23B 100 周期状态机 [`run_pillar23b_powerloss_and_100cycle_suite`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h191-phase176-pillar23-wbi-powerloss-100cycle-recovery/outputs/fx3-recovery-adapter/fx3_recovery/realhw_wbi_powerloss_and_100cycle_transition_verifier.py#L1653-L1797) 与总入口 [`run_wbi_powerloss_and_100cycle_suite`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h191-phase176-pillar23-wbi-powerloss-100cycle-recovery/outputs/fx3-recovery-adapter/fx3_recovery/realhw_wbi_powerloss_and_100cycle_transition_verifier.py#L1805-L1879) |
| 更新包导出 | [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h191-phase176-pillar23-wbi-powerloss-100cycle-recovery/outputs/fx3-recovery-adapter/fx3_recovery/__init__.py#L2165-L2277) | 末尾导出 108 项无冲突 Phase 176 Pillar 23 符号与 `__all__` 条目（零覆盖既有安全符号） |
| 更新 CLI | [`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h191-phase176-pillar23-wbi-powerloss-100cycle-recovery/outputs/fx3-recovery-adapter/fx3_recovery/__main__.py#L897-L928) | 新增 `verify-wbi-powerloss-recovery`（支持 `--json`、`--force-clean-room` / `--clean-room`、`--out`） |
| 更新文档 | [`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h191-phase176-pillar23-wbi-powerloss-100cycle-recovery/outputs/fx3-recovery-adapter/README.md#L595-L610) | 补充 Phase 176 Pillar 23 架构说明与 CLI 用法 |
| 新增单元测试 | [`test_realhw_wbi_powerloss_and_100cycle_transition.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h191-phase176-pillar23-wbi-powerloss-100cycle-recovery/outputs/fx3-recovery-adapter/tests/test_realhw_wbi_powerloss_and_100cycle_transition.py) | 52 项双模式（`LOCAL_DONOR_O_RDONLY` + `FX3_FX6_FORCE_CLEAN_ROOM=1`）单元测试 |
| 阶段报告 | [`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h191-phase176-pillar23-wbi-powerloss-100cycle-recovery/reports/2026-11-15-phase176-realhw-pillar23-wbi-powerloss-100cycle-recovery/README.md) | 本报告 |

## 3. 已验证事实与未执行物理动作严格区分

### 3.1 已完成验证：`O_RDONLY` 本地供体审计与洁净室仿真

1. **FX3 `7.02` 实机解包供体 `O_RDONLY` 只读审计（`0.010s`，零原始固件字节泄露）**：
   - `fx3_nflasha5_wbi2`（`nflasha5.img`，`209,112,512 B`）：有界读取 `512 B` 头部（SHA-256 `11ae397741d0...`）与 `1,399` 个 `WBI2` 节表项（SHA-256 `7286ddb05a73...`），确认为 `WBI2` 魔数、`512 B` 扇区几何。
   - `partinf.conf`（`3,999 B`，SHA-256 `3d96228d4ed2...`）：实证 30 分区布局含 `p5:/wbi`（`0x00041800, 0x00096000, 0x00000006`）。
   - `mount.conf`（`1,248 B`，SHA-256 `ea0132091f3b...`）：实证 `/dev/nflasha5 /wbi wbi 314572800 0` 及 `/setting`、`/cert`、`/usr`、`/lens` 挂载关系。
   - `kemco.txt`（`1,736 B`，SHA-256 `555454e8b7db...`）、`sbin/init`（`735 B`，`c83de1abeeb7...`）、`sbin/init2`（`1,658 B`，`45d3b907e6ef...`）、`sbin/initrc/setup_nflash`（`375 B`，`055cb3db7a40...`）：实证 `WBI_MEMCLR`、`WBIMEM` 4 区域、`PM_RESUME`、`WDT_500` 与 `nflasha`/`pnflasha` 符号链。
   - `vmlinux.bin`（`6,610,952 B`，SHA-256 `da4a66fa29f6...`）：实证 `Linux 4.9.337-scel+` 与 `WBI2`/`pm_suspend` 符号标记。
   - `fx3-7.02-BODYDATA.DAT`（`811,876,768 B`，前 4K 头 SHA-256 `fc135914e076...`）：有界 `4 KiB` 头校验通过 `\x89UFU` 魔数。
   - `FX3_FX6_FORCE_CLEAN_ROOM=1` 下确定性回退 `CLEAN_ROOM_SYNTHETIC` / `SYNTHETIC_METADATA_ONLY`（`donor_files_inspected = 0`，耗时 `9 us`）。

2. **Pillar 23A — `p5:/wbi`（`WBI2` / `hibdrv.ko`）跨模式污染防火墙（`8/8` 通过）**：
   - `WBI_S1_STAGEB_COLDBOOT_FORCED_BYPASS`：SD 卡接入进入 Stage-A 强制 `WBI_RESUME_BYPASS=1` + 冷启动初始化（`wbi_resume_attempted=False`、`cold_boot_enforced=True`）。
   - `WBI_S2_NFLASHA5_PNFLASHA5_BLKROSET_LOCK`：`/dev/nflasha5` 与 `/dev/pnflasha5` 双双锁定 `BLKROSET=1`，任何 `hibdrv.ko` 写入尝试均 fail-closed 返回 `-EROFS`（`errno=30`，`wbi_persistent_writes=0`）。
   - `WBI_S3_EH1_SD_EJECT_STOCK_WBI_INTACT`：拔卡 `EH1`（`< 50 us`，仿真 `47 us`）回到原厂 FX3 `7.02`，`p5:/wbi` SHA-256 与 `H0` 完全一致。
   - `WBI_S4_STALE_WBI_MAGIC_MISMATCH_FALLBACK`：损坏/陈旧 `WBI2` 头（`invl` / `wbi2` / `WBI3` / CRC 异常）优雅回落冷启动，零内核 panic。
   - `WBI_S5_UFU_BODYDATA_COLDBOOT_COEXISTENCE`：存在 `/mnt/sd/BODYDATA.DAT`（`\x89UFU`）时 `< 100 us`（`42 us`）同时旁路 Stage-B 与陈旧 `WBI2` 恢复。
   - `WBI_S6_TMPFS_VOLATILE_SUSPEND_BLOCK`：Stage-B 拦截 `/sys/power/state` `disk`（`PM_SUSPEND_DISK`）屏蔽为空操作，`hibdrv_triggered=False`。
   - `WBI_S7_FACTORY_CAL_AND_CERT_RO_COINVARIANCE`：`p2:/setting`（`psd.bin`、`defdet.bin`、`Backup.bin`）、`p5:/wbi`、`p12:/cert`（`RQ_LIC.DAT`）、`p18:/lens`（`LENSFILE.BIN`）协同只读零写入（`persistent_writes=0`）。
   - `WBI_S8_TIER0_RECEIPT_PREREQUISITE`：缺少或漂移 `p5:/wbi` 基线哈希的双介质 `FX3RCPT1` 收据 fail-closed 拒绝 Stage-B 激活。

3. **Pillar 23B — 突发断电与 100 周期 `H0 -> H1 -> H2 -> H3` 状态机校验（`8/8` 场景、`100/100` 周期、`16/16` 关键面零漂移）**：
   - 确定性覆盖 100 周期事件分布：`BOOT_STOCK_H0`（8）、`STAGE_A_TO_STAGE_B_H1_H2`（39）、`NP_FZ100_BATTERY_PULL_BIG6_MENU`（8，`tmpfs` 挥发零 eMMC 日志污染）、`NP_FZ100_6V3_BROWNOUT_ENCWFISTOP_RSV`（8，`.RSV` 隔离至可移除 ExFAT 卡，eMMC 零写入）、`EH1_SD_EJECT_47US_STOCK`（8，`47 us`）、`EH2_DISP_MENU_SHUTTER_SAFEBOOT`（7）、`EH3_LIBJIT_1BYTE_CRC32_TAMPER`（7，`420 us` `< 1 ms` fail-closed 回退）、`UFU_BODYDATA_DAT_COLDBOOT`（7，`42 us`）、`CLEAN_UNINSTALL_H2_TO_H3`（8）。
   - 100 周期全部执行完毕后，`emmc_bit_drift_count = 0`、`wbi_persistent_writes = 0`、`16/16` 关键表面精确满足 `H0 == H3`（`522ea31fa5e505a019c56787d66f2b255441194d1951877206031df4a93777c0`）；负向 1-bit eMMC 漂移注入确认被 `BLOCKED_EMMC_PARTITION_BIT_DRIFT_DETECTED` 拒绝。

### 3.2 未执行动作：真实物理 ILME-FX3 相机台架动作（BLOCKED / NOT EXECUTED）

- **未在真实相机上执行**：未插拔真实 `NP-FZ100` 电池制造 `6.3V` 欠压或菜单中段断电，未在实机拔插 SD 卡验证 `47 us` 硬件复位时序，未运行真实内核 `hibdrv.ko` / `BLKROSET` ioctl 或加载 `BODYDATA.DAT` 刷写，亦未连接物理 USB / UART 触发设备端任何持久化写操作。

## 4. 实测验证命令与结果

| 验证项 | 模式 | 实测结果 |
|---|---|---|
| `verify-wbi-powerloss-recovery --json` | `LOCAL_DONOR_O_RDONLY` | `all_passed=True`、`pillar_23a=8/8`、`pillar_23b=8/8`、`cycles=100/100`、`emmc_bit_drift_count=0`、`h0_equals_h3=True`、`elapsed_seconds=0.014`（`< 1.0s`）、`suite_sha256=d4b6819a2dc3c17c...` |
| `verify-wbi-powerloss-recovery --json` | `CLEAN_ROOM_SYNTHETIC` | `all_passed=True`、`pillar_23a=8/8`、`pillar_23b=8/8`、`cycles=100/100`、`emmc_bit_drift_count=0`、`h0_equals_h3=True`、`elapsed_seconds=0.003`（`< 1.0s`）、`suite_sha256=befb76e292ff7e6c...` |
| `test_realhw_wbi_powerloss_and_100cycle_transition.py` | 默认（`LOCAL_DONOR_O_RDONLY`） | `Ran 52 tests in 2.974s — OK` |
| `test_realhw_wbi_powerloss_and_100cycle_transition.py` | `FX3_FX6_FORCE_CLEAN_ROOM=1` | `Ran 52 tests in 1.924s — OK` |
| `PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests -p "test_*.py"` | 默认（`LOCAL_DONOR_O_RDONLY`） | `Ran 1019 tests in 131.699s`（`1018` 通过、`1` skipped；仅既有用例 `test_recovery_master_suite_and_uart_decoder.py::test_25` 在多路并发宿主 CPU 负载下偶发 `1.143s >= 1.0s`，同文件单跑 `34/34` `0.679s` 通过；Phase 176 全部 `52/52` 通过） |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests -p "test_*.py"` | `CLEAN_ROOM_SYNTHETIC` | `Ran 961 tests in 101.631s`（`950` 通过、`10` skipped；同上仅既有 `test_25` 在并发负载下报 `1.966s >= 1.0s`，Phase 176 全部 `52/52` 通过） |
| `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | 仓库洁净度审计 | `ALL GREEN in 0.05s`（零 `.pyc` / 零未跟踪二进制污染） |
