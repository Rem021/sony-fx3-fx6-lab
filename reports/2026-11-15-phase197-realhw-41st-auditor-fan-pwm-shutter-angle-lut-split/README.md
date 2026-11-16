# Phase 197（第 41 号固件审计器 `41/41`）交付报告：`ILME-FX3` (`Ver. 7.02`) 四档风扇 PWM / `Off in Rec` 待机 `MAX PWM` 与冷备份温控护栏、独立 `[Shutter Mode]` (`Speed` vs `Angle` `5.6°..64F / 360°`) 槽位存储及 `Ver. 6.01` vs `Ver. 7.00/7.02` `p2:/setting` User LUT 二进制代际分裂防火墙

## 1. 核心结论

1. **第 41 号审计器 (`41/41`) 落地闭环**：已在 [`realhw_fan_pwm_shutter_angle_and_lut_601_702_split_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h215-phase197-41st-auditor-fan-pwm-shutter-angle-lut-split/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_fan_pwm_shutter_angle_and_lut_601_702_split_auditor.py) 完成 `PHASE_197_SCHEMA` (`197.0.0`) 实现，导出至 [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h215-phase197-41st-auditor-fan-pwm-shutter-angle-lut-split/outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py)，并在 [`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h215-phase197-41st-auditor-fan-pwm-shutter-angle-lut-split/outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py) 接入独立 CLI 子命令 `audit-realhw-fan-pwm-shutter-lut-split` 与总控 `audit-all` (`41/41`)，同步更新 [`outputs/fx3-firmware-lab/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h215-phase197-41st-auditor-fan-pwm-shutter-angle-lut-split/outputs/fx3-firmware-lab/README.md)。
2. **有界 `os.O_RDONLY` + `os.pread` 极速扫描与洁净室双模一致性**：本地真机 Donor 冷启动扫描实测耗时 **`0.117s`**（严格 `< 0.15s` 预算，进程内 `_DONOR_SCAN_CACHE` 二次命中 `< 1ms`）；无任何整镜像 `>50 MiB` 冗余扫描，`raw_firmware_bytes_leaked == 0`，JSON 输出跨进程逐字节确定性一致。
3. **全量双模回归 `100%` 通过**：新增 [`test_realhw_fan_pwm_shutter_angle_and_lut_601_702_split.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h215-phase197-41st-auditor-fan-pwm-shutter-angle-lut-split/outputs/fx3-firmware-lab/tests/test_realhw_fan_pwm_shutter_angle_and_lut_601_702_split.py) **55 项**双模单测（Donor 模式 `0.454s`、洁净室模式 `0.339s`）；`outputs/fx3-firmware-lab/tests` 全量 **1,519 项**单测在本地 Donor 模式（`50.857s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 洁净室模式（`24.318s`）均 `100%` 通过。

---

## 2. 四大实证支柱（实测二进制证据 vs 建模边界）

### Pillar 1 — `ILME-FX3` 精确四档 `[Fan Control]`、`Off in Rec` 待机 `100% MAX PWM` 排热与冷备份温控互锁
- **实测二进制事实（`O_RDONLY`）**：
  - 原厂 `FX3 Ver. 7.02` (`appFw.so` `79,015,712 B` + `string_english_f.uxc` `373,820 B`) 与 `FX6 Ver. 6.01` (`appFw.so` `50,520,424 B` + `string_english.uxc` `118,208 B`) 均精确绑定四态枚举 `FAN_CONTROL_AUTO`、`FAN_CONTROL_MINIMUM`、`FAN_CONTROL_OFF_IN_REC`、`FAN_CONTROL_ALWAYS_OFF`（菜单路径 `MENU -> Setup -> [Setup Option] -> [Fan Control]`），且非索尼演播室/松下系的 `FAN_CONTROL_AUTO1`、`FAN_CONTROL_AUTO2`、`"Auto1"`、`"Auto2"` 在两机二进制与 `.uxc` 中命中数均为 **`0`**。
  - 两机 `CPAPP-B.BIN` / `cpapp-b.bin` 有界切片均检出 `SET_FAN_EQ_ID`、`FAN_R`、`PWM`、`THERM` 等 CP RTOS 硬件温控闭环符号；`FX3 7.02` 另具 `BKID_APP_setting_fan_control`、`EVENT_REMOTE_AUTO_POWER_OFF_TEMPERATURE`、`OFF_BY_THERMAL_TIME_OUT`。
- **温控与冷备份护栏逻辑**：
  - 显式拒绝 `Auto1`/`Auto2`（归类 `MASKED_ABSENT_HW`）。
  - 精确建模 `Off in Rec`：录制中（低于 `[Auto Power OFF Temp.] = Standard (68°C) / High (78°C)` 紧急阈值）保持 `0%` PWM 静音，一旦停止录制回到待机立即拉满 **`100% MAX PWM`** 主动排热；若录制中温升突破紧急阈值，CP RTOS 强制接管 `100%` 紧急散热。
  - 在发起 `AdjustControl (0x40)` 75 MiB `p3` 长时间冷备份前，若风扇处于 `Always Off` / `Off in Rec` 且未启用互锁则直接阻断（标记 `cxd90057_cxd90058_overheat_risk = True`），启用互锁则强制切换为 `Auto` 以防 `CXD90057 / CXD90058` 过热断电。

### Pillar 2 — `Backup.bin` 独立 `[Shutter Mode]` (`Speed` vs `Angle`) 键值槽位与帧率收窄（`5.6°..64F` vs `5.6°..360°`）
- **实测二进制事实（`O_RDONLY`）**：
  - `FX3 Ver. 7.02` `appFw.so` 实测包含 `BKID_APP_setting_mode_shutter`、`VAL_setting_mode_shutter_MODE_SHUTTER_SPEED`、`VAL_setting_mode_shutter_MODE_SHUTTER_ANGLE`、`VAL_setting_shutter_angle_SHUTTER_ANGLE_5_POINT_6`、`180_POINT_0`、`360_POINT_0`、`64F` 及 `EXPOSURE_STEP_0_3_EV` / `0_5_EV`；64 字节有界读取确认 `Backup.bin` `BK4\x00` 子系统计数为 `FX3 = 819`、`FX6 = 840`。
- **槽位独立性与范围夹紧模型**：
  - 验证 `0x02cf1702` (`[Shutter Mode]`) 与 `0x02cf1704` (`[Shutter Angle]`) 同 `[Speed]` 槽位解耦，来回切换 `Speed <-> Angle` 或修改 `[Exposure step] = 0.3EV / 0.5EV` 均不会覆写对端记忆值。
  - 常规视频（`23.98p .. 59.94p`）允许完整 `5.6° .. 64F`（`23,040.0°`）；当 `[Rec Frame Rate] = 119.88p / 100p` 或进入 `S&Q` 模式时，自动夹紧（模式切换时 `SHIM_TRANSLATED -> 360.0°`）或拦截直接下发的 `2F..64F` 慢门请求，统一收窄至 `5.6° .. 360.0°`；任何 `< 5.6°` 输入均失败关闭拒绝。

### Pillar 3 — `FX6 Ver. 6.01` (`<=6.01` 旧版槽位) vs `Stock FX3 Ver. 7.00/7.02` (`7.00+` 优化版槽位) `p2:/setting` 二进制代际分裂防火墙
- **实测二进制铁证（`O_RDONLY`）**：
  - **Donor `FX6 Ver. 6.01` 独有旧版 Diadem-Pro LUT 符号**（在 `FX3 7.02` 中命中均为 `0`）：`BKID_APP_IS_EXIST_USER_LUT0..15`（全大写）、`BKID_APP_HAND_OVER_USER_LUT_EXIST_AFTER_UUD_FROM_DIADEM_PRO0..15`、`model_user_lut_files::cube file save skip!! line[%d]`。
  - **Host `Stock FX3 Ver. 7.02` 独有 `7.00+` 优化版 LUT 符号**（在 `FX6 6.01` 中命中均为 `0`）：`BKID_APP_is_exist_user_lut0..15`（全小写）、`BKID_APP_user_lut_attr_ae_level_offset0..15`（`0..+2 EV` 曝光偏移）、`BKID_APP_setting_embed_lut_file`。
- **隔离重定向证明**：
  - 洁净室模型证明若将 `FX6 6.01` 的 `<=6.01` 槽位描述符（`UL61` 48B）直接写入原厂 `p2:/setting` `User1..User16`，会导致 `Stock FX3 7.02`（期望 `UL70` 64B 含 AE Level Offset 与 CRC32）触发 `LUT_GENERATION_SPLIT_601_TO_702_DESERIALIZE_CORRUPTION`。
  - 防火墙硬阻断一切指向 `p2:/setting` 的写入，将 Stage-B `User1..User16` 强制重定向至易失性 `/tmp/fx6_lut_overlay`，确保 `H0 -> H1 -> H2 -> H3` 全生命周期 `p2:/setting` 哈希逐位恒等（`h0_equals_h3 == True`，`p2_setting_mutation_bytes == 0`，`calibration_mutation_bytes == 0`）。

### Pillar 4 — 全局零写防火墙与 12 触点四分类兼容矩阵
- 汇总 `P197-01 .. P197-12` 共 **12 个硬件/固件触点**，完整覆盖 `NATIVE_PASSTHROUGH`、`SHIM_TRANSLATED`、`MASKED_ABSENT_HW`、`HARD_WRITE_PROTECTED` 四类桥接等级。
- 硬安全不变量恒成立：`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`physical_usb_packets_emitted = 0`、`raw_firmware_bytes_leaked = 0`。
- **边界声明**：本阶段全部工作均为本地主机侧纯离线 `O_RDONLY` 二进制取证与洁净室状态机建模，**未连接任何物理相机 USB，未生成或下发任何刷机载荷或 eMMC/SPI-NOR 写入指令**。

---

## 3. 交付文件清单（严格归属范围内 7 个文件）

1. [`outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_fan_pwm_shutter_angle_and_lut_601_702_split_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h215-phase197-41st-auditor-fan-pwm-shutter-angle-lut-split/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_fan_pwm_shutter_angle_and_lut_601_702_split_auditor.py)（新增：第 41 号审计器实现）
2. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h215-phase197-41st-auditor-fan-pwm-shutter-angle-lut-split/outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py)（更新：导出 Phase 197 公共常量、数据类与入口函数）
3. [`outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h215-phase197-41st-auditor-fan-pwm-shutter-angle-lut-split/outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py)（更新：注册 `audit-realhw-fan-pwm-shutter-lut-split` 并接入 `audit-all` `41/41`）
4. [`outputs/fx3-firmware-lab/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h215-phase197-41st-auditor-fan-pwm-shutter-angle-lut-split/outputs/fx3-firmware-lab/README.md)（更新：补充第 41 号审计器说明与 CLI 命令）
5. [`outputs/fx3-firmware-lab/tests/test_realhw_fan_pwm_shutter_angle_and_lut_601_702_split.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h215-phase197-41st-auditor-fan-pwm-shutter-angle-lut-split/outputs/fx3-firmware-lab/tests/test_realhw_fan_pwm_shutter_angle_and_lut_601_702_split.py)（新增：55 项双模单测）
6. [`outputs/fx3-firmware-lab/tests/test_realhw_nouvc_dcc1_pd_lut_path_cineei.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h215-phase197-41st-auditor-fan-pwm-shutter-angle-lut-split/outputs/fx3-firmware-lab/tests/test_realhw_nouvc_dcc1_pd_lut_path_cineei.py)（更新：仅将第 40 号审计器 `audit-all` 审计键数量断言从 `assertEqual(..., 40)` 放宽为 `assertGreaterEqual(..., 40)`）
7. [`reports/2026-11-15-phase197-realhw-41st-auditor-fan-pwm-shutter-angle-lut-split/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h215-phase197-41st-auditor-fan-pwm-shutter-angle-lut-split/reports/2026-11-15-phase197-realhw-41st-auditor-fan-pwm-shutter-angle-lut-split/README.md)（新增：本交付报告）

---

## 4. 验证命令与实测结果

| 验证项 | 命令（均带 `/usr/bin/python3 -B`） | 实测结果 |
| :--- | :--- | :--- |
| 第 41 号审计器 CLI | `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-realhw-fan-pwm-shutter-lut-split --json \| head -n 30` | `all_checks_passed: true`, `auditor_index: "41/41"`, 冷扫 `0.117s` |
| 总控 `audit-all` (`41/41`) | `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-all --json \| head -n 30` | `all_checks_passed: true`（41 项审计器全绿，跨进程 JSON 100% 确定性一致） |
| Phase 197 单测（本地 Donor） | `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest outputs/fx3-firmware-lab/tests/test_realhw_fan_pwm_shutter_angle_and_lut_601_702_split.py` | `Ran 55 tests in 0.454s — OK` |
| Phase 197 单测（洁净室） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest outputs/fx3-firmware-lab/tests/test_realhw_fan_pwm_shutter_angle_and_lut_601_702_split.py` | `Ran 55 tests in 0.339s — OK` |
| 固件实验室全量单测（Donor） | `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"` | `Ran 1519 tests in 50.857s — OK` |
| 固件实验室全量单测（洁净室） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"` | `Ran 1519 tests in 24.318s — OK (skipped=6)` |
| 全局零字节码/合规门禁 | `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | `PASS`（零 `.pyc` / `__pycache__` / 专有二进制残留） |
