# Phase 149（第 30 号审计器）：真机 ILME-FX3 机身按键 / T/W 变焦杆 / 3 颗 Tally 灯 / 主动散热风扇 PWM 与 NP-FZ100 / USB-PD 供电桥接审计报告

- **任务编号**：`H160 / Phase 149`
- **目标架构**：Hybrid Userland Stage-B（`FX6 v6.01 appFw.so` + `LD_PRELOAD libgrm-fbinit9.so` 运行于 Stock FX3 `v7.02` `4.9.337-scel+` 内核与原厂 `cpapp-b.bin` RTOS 之上）
- **核心原则**：100% `os.O_RDONLY` + `mmap.ACCESS_READ` 只读静态审计 + 确定性 Clean-Room 回退；严禁写入 `p2:/Backup.bin`、`cpapp-b.bin` 或 `/dev/mmcblk0*`，状态叠加严格限制在 `/tmp/` / `ram://` 易失内存区（`emmc_mutation_bytes = 0`、`calibration_mutation_bytes = 0`）。

## 1. 本次修改文件清单（严格限定 6 个 Owned Files）

| 序号 | 文件 | 职责 |
| :--- | :--- | :--- |
| 1 | [realhw_physical_controls_tally_fan_and_power_auditor.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h160-phase149-realhw-controls-tally-fan-power/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_physical_controls_tally_fan_and_power_auditor.py) | 第 30 号统一审计器实现（4 大支柱 + 12 触点 4 分类兼容矩阵 + 持久化写保护卫士） |
| 2 | [__init__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h160-phase149-realhw-controls-tally-fan-power/outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py) | 导出 Phase 149 常量、数据类、评估函数与 `__all__` 符号 |
| 3 | [__main__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h160-phase149-realhw-controls-tally-fan-power/outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py) | 新增 CLI 子命令 `audit-realhw-controls-fan-power` 并接入 `audit-all`（汇总 `30/30`） |
| 4 | [README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h160-phase149-realhw-controls-tally-fan-power/outputs/fx3-firmware-lab/README.md) | 更新第 30 号审计器说明与 CLI 用法示例 |
| 5 | [test_realhw_physical_controls_tally_fan_and_power.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h160-phase149-realhw-controls-tally-fan-power/outputs/fx3-firmware-lab/tests/test_realhw_physical_controls_tally_fan_and_power.py) | 46 项双模式（Local Donor / Clean-Room）单元测试 |
| 6 | [README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h160-phase149-realhw-controls-tally-fan-power/reports/2026-11-15-phase149-realhw-controls-tally-fan-fz100-power-bridge/README.md) | 本期 Phase 149 结项报告 |

## 2. 实测事实与未执行边界（严格区分）

### 2.1 `O_RDONLY` 本地 Donor 实测事实（FX3 v7.02 vs FX6 v6.01）

通过 [`analyze_realhw_physical_controls_tally_fan_and_power`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h160-phase149-realhw-controls-tally-fan-power/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_physical_controls_tally_fan_and_power_auditor.py#L1408) 对本地 12 份 BYOF 镜像执行 `os.O_RDONLY` + `mmap.ACCESS_READ` 实测（单次全量耗时 `< 0.6 s`，SHA-256 `9451ce5afac3d74fa45ad90efec08332470c4cdc2f9651ec04ab22590f3f4e52`）：

- **被测 Donor 字节规模**：
  - `appFw.so`：FX3 `79,015,712 B` vs FX6 `50,520,424 B`
  - `libsencore.so`：FX3 `377,328 B` vs FX6 `401,952 B`（双方导出/导入符号数完全一致：**`355` exports / `130` imports**，共享 `FAN_SET_SPEED`、`CXS_WRITE_PWM`、`GET_TEMPERATURE`、`C_IMAGER_TEMP_CHK`、`TALLY_LED`、`USB_BUSPOWER_SUPPLY_CONTROL`、`CTRL_POWER`、`OUTSIDE_EVF_KEY_POSITION`）
  - `libmpr.so`：FX3 `3,517,008 B` vs FX6 `28,921,824 B`（均包含 `mpr::Codec::EncWfiStop` 与 `mpr::Codec::EncWfiStopReserve`）
  - `im.elf`：FX3 与 FX6 均为 **`40,920 B`**（导出/导入与动态库依赖完全一致：**`11` exports / `85` imports / `15` `DT_NEEDED`**，含 `libIMDB.so`、`libbackup.so`、`libosal_uipc.so`）
  - `cpapp-b.bin`：FX3 `15,980,568 B` vs FX6 `17,952,816 B`
  - `Backup.bin`（`BK4\x00` 双记录）：FX3 `2,229,740 B`（`819` 子系统）vs FX6 `2,253,333 B`（`840` 子系统），双记录 32-bit 校验和均通过
- **Pillar 1 — 实体机身按键映射与人体工学单手闭环**：
  - `appFw.so` 只读扫描命中 FX3 `15/15`、FX6 `16/16` 按键/变焦符号（含 `WidgetBase::onKeyEvent`、`EVENT_INPUT_KEY_TACT_*`、`UIBIZ_KEY_TACT_*`、`UIBIZ_SLIKEY_ZOOM`、`UIBIZ_KEY_SLIKEY_ZOOM_SPINAL`）。
  - [`evaluate_physical_keymap_bridge`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h160-phase149-realhw-controls-tally-fan-power/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_physical_controls_tally_fan_and_power_auditor.py#L971) 证实：FX3 `Custom 1..6` + `MODE` + `DELETE/DISP` + 前后拨轮/转盘 + 5 向摇杆 + `T/W` 变焦杆 + 顶/前双 `REC` + `AF-ON` / `AEL` / 镜头 `FH` 可单手直达 FX6 全部 6 项核心操作（`BIG6_HOME`、`FULL_MENU_128P`、`STATUS_CHECK_TABS`、`DIRECT_TOUCH_JOYSTICK`、`SERVO_ZOOM_8STEP`、`REC_START_STOP`），同时将 FX6 独有物理开关（`SLOT SEL`、`FULL AUTO`、`ND` 转轮）软映射/屏蔽，且 **强制保留 `MENU + SHUTTER + POWER` 物理逃生通道（`escape_hatch_preserved == True`）**。
- **Pillar 2 — 主动散热风扇 PWM 与热保护紧急接管**：
  - `appFw.so` 命中 FX3 `8/8`、FX6 `9/9` 风扇控制标记；`cpapp-b.bin` 命中共享标记 `SET_FAN_EQ_ID`（1/1）、`PROC_MSG_SET_FAN_EQ_ID:`（1/1）、`FAN_R`（1/1）、`PWM`（12/12）、`THERM`（FX3 `10` vs FX6 `11`）。
  - [`evaluate_cooling_fan_thermal_bridge`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h160-phase149-realhw-controls-tally-fan-power/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_physical_controls_tally_fan_and_power_auditor.py#L1035) 证明：`OFF_IN_REC` 仅在 `< 58°C` 静音（`0% PWM`），到达 `58°C` 预升温至 `45%`、`>= 65°C` 由 Stock FX3 `cpapp-b.bin` 强制拉满 `100% PWM`、`>= 72°C` 或风扇故障过热时触发 `EncWfiStop` 优雅封包落盘；录制中严禁 `ALWAYS_OFF`，且禁止屏蔽 Stock-CP 温控覆盖（`thermal_emergency_override_intact == True`）。
- **Pillar 3 — 机身 3 颗物理红 Tally 灯同步**：
  - `appFw.so` 命中 FX3 `4/4`、FX6 `9/9` Tally 控制标记（`REC_LAMP_ALL_LIGHTS_UP` / `REC_LAMP_ONLY_FRONT_OFF` / `REC_LAMP_LIGHT_UP_ONLY_ONE` / `REC_LAMP_ALL_LIGHTS_OUT`），`cpapp-b.bin` 共享 `MSG_ID_INFRABB_SYS_SET_CA_TALLY`（1/1）。
  - [`evaluate_tally_lamps_bridge`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h160-phase149-realhw-controls-tally-fan-power/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_physical_controls_tally_fan_and_power_auditor.py#L1125) 验证 FX3 前/顶 REC/后 3 颗物理红灯 1:1 同步录制与亮灭配置，并将 FX6 独有的 `Green (PVW)` / `Yellow` 广播 Tally 严格隔离在 GPE0 OSD 边框层，禁止写入红色 GPIO（`gpio_mismatch_count == 0`）。
- **Pillar 4 — `NP-FZ100` (`7.2V`) + `USB-PD` (`9V/3A`) 供电遥测与防误报警**：
  - `appFw.so` 命中 FX3 `7/7`、FX6 `10/10` 电源遥测标记，`cpapp-b.bin` 命中 `9/9` 电池认证与状态帧（`ACV_BATT_Snd`、`BATT_AUTH_Snd`、`BATT_STATE1..3_Snd` 等），`libmpr.so` 命中 `2/2` `EncWfiStop` 接口。
  - [`evaluate_power_telemetry_bridge`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h160-phase149-realhw-controls-tally-fan-power/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_physical_controls_tally_fan_and_power_auditor.py#L1197) 验证 `NP-FZ100` (`6000..8400 mV`, `16.4 Wh`) + `USB-PD 9V/3A (27W)` / `5V/3A (15W)` 在 FX6 HUD 干净显示 `0..100% + USB-PD` 并屏蔽 FX6 `18.0V / 19.5V DC-IN Low Voltage` 误报警（`false_dcin_alarm_eliminated == True`）；无外接 PD 时在 `<= 5%` / `6350 mV` 触发 `NEAR_END` 提示，在 `<= 2%` / `6100 mV` 触发 `EncWfiStop` 防止产生 `.RSV` 损坏文件。

### 2.2 尚未在真实物理 ILME-FX3 机身上执行的实机测试（明确未测项）

以下项目属于真机运行时验证范畴，**本次仅完成静态/Clean-Room 符号与状态机合同验证，尚未在物理 ILME-FX3 机身实机上电执行**：
1. 真实物理 ILME-FX3 机身运行 Stage-B `LD_PRELOAD libgrm-fbinit9.so` 时，`Custom 1..6` / `T/W` 变焦杆 / 前后拨轮的实际 `KeyEvent` 延迟与手感联调。
2. 真实 4K60P 长时间录制下，选择 `Off in Rec` 并人为加热至 `>= 65°C` / `>= 72°C` 时的物理风扇转速阶跃与 `EncWfiStop` 实机波形抓取。
3. 物理机身在 `NP-FZ100` 耗尽关机临界点（`<= 2%`）及插拔 `9V/3A USB-PD` 瞬态下的实机 HUD 刷新与热拔插录影连续性测试。

## 3. 定向验证结果

| 验证命令 | 模式 | 结果 |
| :--- | :--- | :--- |
| `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest outputs/fx3-firmware-lab/tests/test_realhw_physical_controls_tally_fan_and_power.py` | Local Donor | **46/46 PASS**（`2.918s`） |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest outputs/fx3-firmware-lab/tests/test_realhw_physical_controls_tally_fan_and_power.py` | Clean-Room | **45 PASS / 1 SKIP**（`0.449s`，仅跳过本地 donor 专属断言） |
| `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"` | Local Donor 全量 | **972/972 PASS**（`31.782s`） |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"` | Clean-Room 全量 | **971 PASS / 1 SKIP**（`16.250s`） |
| `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | Hygiene / Clean-Room | **ALL GREEN**（`1.89s`） |
| `audit-all --clean-room --json` & `audit-realhw-controls-fan-power --json` | 30/30 Unified CLI | `all_checks_passed: true`（`30` 个审计模块全部通过） |
