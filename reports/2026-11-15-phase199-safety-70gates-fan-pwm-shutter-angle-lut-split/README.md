# Phase 199（Task H218）真机安全护栏报告：`ILME-FX3`（`Ver. 7.02`）精确四态散热风扇 PWM 与冷备份防过热护栏（`G69`）、`6.01 -> 7.00/7.02` 机内 `p2:/setting` User LUT 二进制格式分裂防火墙与独立快门速度/角度边界护栏（`G70`）及 70 门总控预检（`verify-70-gates`）

## 1. 结论先行（实测闭环）

基于已合入的 **Phase 196（`verify-68-gates`）** 与 **Wave-25 全球索尼真机情报**（[Wave-25 README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h218-phase199-safety-70gates-fan-pwm-shutter-angle-lut-split/reports/2026-11-15-global-sony-wave25-fan-pwm-offinrec-shutter-angle-lut-601-vs-702-binary-split-intel/README.md)），已在 [`outputs/fx3-safety/`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h218-phase199-safety-70gates-fan-pwm-shutter-angle-lut-split/outputs/fx3-safety/README.md) 完成 **Gate `G69`**、**Gate `G70`** 与 **70 门总控安全预检（`evaluate_70gate_preflight` / `verify-70-gates`）** 的端到端实现与双模回归验证：

- **向后兼容 100% 保持**：`verify-58-gates`、`verify-60-gates`、`verify-62-gates`、`verify-64-gates`、`verify-66-gates` 与 `verify-68-gates` 全部无损通过。
- **离线与彩排双态锁定**：默认离线态 `67/70` 通过（`G10..G12` 物理 Tier-0 冷备收据门保持 `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED`，返回 `VERIFIED_67_OF_70_AWAITING_PHYSICAL_TIER0`）；`--dry-run-simulated` 彩排态 `70/70` 通过（`VERIFIED_ALL_70_GATES_DRY_RUN_SIMULATED_BACKUP`）。
- **物理红线硬锁死**：全程硬锁 `overall_ready_for_hardware_attach = False`、`agent_auto_flash_blocked = True`、`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`physical_usb_packets_emitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. 核心实现与工程模块（6 个受控文件）

1. **新增 [`realhw_fan_pwm_shutter_angle_lut_split_and_70gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h218-phase199-safety-70gates-fan-pwm-shutter-angle-lut-split/outputs/fx3-safety/fx3_safety/realhw_fan_pwm_shutter_angle_lut_split_and_70gate_guard.py)**：
   - **只读 Donor 契约审计（[`audit_phase199_donor_contracts`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h218-phase199-safety-70gates-fan-pwm-shutter-angle-lut-split/outputs/fx3-safety/fx3_safety/realhw_fan_pwm_shutter_angle_lut_split_and_70gate_guard.py#L611-L725)）**：严格以 `os.open(..., os.O_RDONLY)` 校验 FX3 `7.02` `cpapp-b.bin`（`15,980,568 B`）、`libfan.so`（`27,280 B`）、`FX3-CX95900_ALLLANG-Backup.bin`（`2,229,740 B`）及 FX6 `6.01` `CX95898_NTSC.bin`（`2,253_333 B`）的精确字节数、SHA-256 与符号标记，支持 `FX3_FX6_FORCE_CLEAN_ROOM=1` 无损脱敏回退，零原始固件字节外泄。
   - **Gate `G69` — `ILME-FX3`（`Ver. 7.02`）精确四态 `[Fan Control]` 与冷备份防过热护栏（[`evaluate_g69_fan_pwm_thermal_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h218-phase199-safety-70gates-fan-pwm-shutter-angle-lut-split/outputs/fx3-safety/fx3_safety/realhw_fan_pwm_shutter_angle_lut_split_and_70gate_guard.py#L1400-L1465)）**：
     - 严格锁定 `MENU -> Setup -> [Setup Option] -> [Fan Control]` 四态枚举 `Auto` / `Minimum` / `Off in Rec` / `Always Off`，拦截演播室机型或松下 Lumix 的非 FX3 伪枚举 `Auto1` / `Auto2`（`BLOCKED_G69_NON_FX3_FAN_ENUM_AUTO1_AUTO2`）。
     - 精确建模 [`compute_fx3_702_fan_pwm_duty_pct`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h218-phase199-safety-70gates-fan-pwm-shutter-angle-lut-split/outputs/fx3-safety/fx3_safety/realhw_fan_pwm_shutter_angle_lut_split_and_70gate_guard.py#L732-L780) 中 `Off in Rec` 物理行为：常规录制（`< 78.0°C`）停转 `0% PWM`，录制越过 `>= 78.0°C` 自动触发 `100%` 紧急热保护覆盖，待机/非录制期间强制 `100% MAX PWM` 主动全速排热（违例阻断码 `BLOCKED_G69_OFF_IN_REC_PWM_CONTRACT_VIOLATION`）。
     - 在 `AdjustControl (0x40)` `75 MiB` `p3` 冷备份或高负载双系统彩排前，若风扇处于 `Always Off` 立即 Fail-Closed 阻断（`BLOCKED_G69_ALWAYS_OFF_PREBACKUP_BLOCKED`），默认要求切回 `Auto`（`BLOCKED_G69_PREBACKUP_REQUIRES_FAN_AUTO`），并结合 `[Auto Power OFF Temp.] = Standard / High` 双温区上限守护 `CXD90057 / CXD90058`（`BLOCKED_G69_AUTO_POWER_OFF_TEMP_OR_THERMAL_OVERLIMIT`）。
   - **Gate `G70` — `FX6 Ver. 6.01` vs `Stock FX3 Ver. 7.00/7.02` `p2:/setting` User LUT 二进制格式分裂防火墙与快门速度/角度独立边界护栏（[`evaluate_g70_lut_split_shutter_angle_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h218-phase199-safety-70gates-fan-pwm-shutter-angle-lut-split/outputs/fx3-safety/fx3_safety/realhw_fan_pwm_shutter_angle_lut_split_and_70gate_guard.py#L1468-L1535)）**：
     - 区分 `<= 6.01`（`LEGACY_V601_USER_LUT_BIN`）与 `7.00+`（`OPTIMIZED_V700_PLUS_USER_LUT_BIN`）两代 `User1..User16` 编译槽位二进制格式，严禁 Stage-B `FX6 Ver. 6.01` 向宿主 `Stock FX3 Ver. 7.02` 的 `p2:/setting`（及 `/setting`、`/dev/nflasha2`）直接写入 LUT 槽位（`BLOCKED_G70_STAGEB_601_TO_702_P2_SETTING_LUT_WRITE`），强制重定向至内存态 `/tmp/fx6_lut_overlay` 并校验 `H0 == H3` `p2:/setting` SHA-256 零漂移（`BLOCKED_G70_H0_H3_P2_SETTING_HASH_DRIFT`）与旧版未重注册 LUT 拦截（`BLOCKED_G70_USER_LUT_SLOT_OR_FORMAT_INVALID`）。
     - 校验 `[Shutter Mode]` 中 `Speed`（`0x01120024`）与 `Angle`（`0x01120028`）在 `Backup.bin` 内的独立槽位存储、模式切换零互串及对 `[Exposure step]`（`0.3EV / 0.5EV`）的完全免疫（`BLOCKED_G70_SHUTTER_SPEED_ANGLE_SLOT_COLLISION`），并校验常规视频 `5.6°..64F` 与 `119.88p / 100p` 及 `S&Q` 下自动收敛至 `5.6°..360.0°`（`1F`）的精确量程（`BLOCKED_G70_SHUTTER_ANGLE_OUT_OF_BOUNDS`）。
   - **70 门总控预检（[`evaluate_70gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h218-phase199-safety-70gates-fan-pwm-shutter-angle-lut-split/outputs/fx3-safety/fx3_safety/realhw_fan_pwm_shutter_angle_lut_split_and_70gate_guard.py#L1824-L2165)）**：无损串联 `evaluate_68gate_preflight`（`G01..G68`）+ `G69` + `G70`。
2. **更新 [`outputs/fx3-safety/fx3_safety/__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h218-phase199-safety-70gates-fan-pwm-shutter-angle-lut-split/outputs/fx3-safety/fx3_safety/__init__.py)**：完整导出 `G69`、`G70`、`Master70GateReport`、`evaluate_70gate_preflight`、`run_70_gate_preflight`、`evaluate_70_master_safety_gates` 及 Phase 199 全部校验器。
3. **更新 [`outputs/fx3-safety/fx3_safety/__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h218-phase199-safety-70gates-fan-pwm-shutter-angle-lut-split/outputs/fx3-safety/fx3_safety/__main__.py)**：接入 `verify-g69-fan-pwm-thermal`、`verify-g70-lut-601-702-shutter-angle` 与 `verify-70-gates`（支持 `--force-clean-room`、`--dry-run-simulated` 与 `--json`）。
4. **更新 [`outputs/fx3-safety/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h218-phase199-safety-70gates-fan-pwm-shutter-angle-lut-split/outputs/fx3-safety/README.md)**：补充 Section 3.3 导出索引与 Section 35 Phase 199 架构与 CLI 文档。
5. **新增 [`test_phase199_fan_pwm_shutter_angle_lut_split_70gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h218-phase199-safety-70gates-fan-pwm-shutter-angle-lut-split/outputs/fx3-safety/tests/test_phase199_fan_pwm_shutter_angle_lut_split_70gate_guard.py)**：共 **56 项**双模单元测试，含 `< 6.0s` 单次调用延迟硬门禁断言。

---

## 3. 实测验证结果（全部使用 `/usr/bin/python3 -B`）

| 验证命令 | 模式 | 实测结果 |
| --- | --- | --- |
| `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-70-gates --json \| head -n 35` | Local Donor `O_RDONLY` | `67/70`（`VERIFIED_67_OF_70_AWAITING_PHYSICAL_TIER0`，红线全锁死） |
| `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-70-gates --dry-run-simulated` | Dry-Run Rehearsal | `70/70`（`VERIFIED_ALL_70_GATES_DRY_RUN_SIMULATED_BACKUP`，`overall_ready_for_hardware_attach=False`） |
| `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_phase199_fan_pwm_shutter_angle_lut_split_70gate_guard.py` | Normal Mode | **56 tests PASS**（`7.64s`，单次 70 门调用 `< 6.0s`） |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_phase199_fan_pwm_shutter_angle_lut_split_70gate_guard.py` | Clean-Room Mode | **56 tests PASS**（`5.01s < 6.0s`） |
| `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | Full `fx3-safety` Normal | **1,393 tests PASS**（`61.21s`） |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | Full `fx3-safety` Clean-Room | **1,393 tests PASS (`skipped=1`)**（`47.79s`） |
| `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | 全仓 Clean-Room 总回归 | **ALL CLEAN-ROOM SUITES PASSED**（零 `.pyc` / `__pycache__` 污染） |
