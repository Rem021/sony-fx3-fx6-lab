# Phase 158 — 实体 FX3 硬件安全护栏 `G49`（`1.8V ttyAMA0` 只读被动监听 & `VMC-BNCM1` 互斥 / `1.8V eMMC ISP`）、`G50`（`IMX510` `psd.bin & defdet.bin` NVS 锁 & `.cube` 防双烤）与统一 50-Gate 主预检报告

> **任务 ID**: `H170` · **目标硬件**: Sony ILME-FX3 (`Ver. 7.02`, Model ID `0x91030080`, SoC `CXD90057`)
> **核心结论**: 在严格保持 `G01..G48` 历史模块 100% 未修改的前提下，已完成安全门 **`G49`**、**`G50`** 与统一 **50-Gate 主预检引擎 (`evaluate_50gate_preflight` / `verify-50-gates`)** 的双模式实现与验证。离线默认模式 `47/50` 通过（`G10..G12` 实体 Tier-0 门维持 `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED`），`--dry-run-simulated-backup` 模式 `50/50` 演练通过；全部核心写入红线 (`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`overall_ready_for_hardware_attach = False`) 均保持硬锁定。

---

## 1. 严格区分：已实测事实 vs 未执行的实体台架操作

### 1.1 本次已实测事实（`os.O_RDONLY` 固件契约审计 + 离线安全门单元测试 + CLI）
1. **双模式只读 (`os.O_RDONLY`) Donor 审计 (`audit_phase158_donor_contracts`)**：
   - 实测读取并校验 FX3 `7.02` 与 FX6 `6.01` 共 10 份本地引用镜像（`libsencore.so`、`libmpr.so`、`im.elf`、`cpapp-b.bin` 及 `FX3-CX95900_ALLLANG-Backup.bin` / `CX95898_NTSC.bin`），全程仅使用 `os.open(..., os.O_RDONLY)`，单次校验全部通过；在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或缺失 donor 目录时确定性回退至 `CLEAN_ROOM_SYNTHETIC`，JSON 输出零原始索尼固件字节泄露。
   - 实测关键契约标记：FX3/FX6 `libsencore.so` 含 `AdjustControlFunc`、`SenserIfStart`、`SenserPacket`、`UART`、`USB_BUSPOWER_SUPPLY_CONTROL`；`cpapp-b.bin` 含 `/setting/defdet.bin`、`IMX510`、`ddl_VfxSetMlutUser3D`、`S-Log3/S-Gamut3.Cine`、`MLUT_L1D_A_ON`；`Backup.bin` 含 `BK4\0`、`psd.bin`、`defdet.bin`、`lensfile.bin`。
2. **Gate `G49` (`1.8V CMOS ttyAMA0 460800 8N1` 被动 RX 监听、`VMC-BNCM1` 互斥防火墙与 `1.8V 8-bit` eMMC ISP 护栏)**：
   - 强制 `ttyAMA0` 严格 `1.8V` CMOS 逻辑电平 (`1620..1950 mV`)、高阻被动 `RX + GND` 监听 (`tx_line_connected == False`、`backpower_leakage_ua <= 5.0 uA`)、禁止 `3.3V/5.0V` FTDI/CP2102 电平过驱 (`BLOCKED_G49_UART_1V8_OVERVOLTAGE_OR_TX_ACTIVE`)。
   - 强制 Multi-USB UART 监听与 `VMC-BNCM1` BNC 时间码适配器互斥 (`BLOCKED_G49_VMC_BNCM1_MULTIPORT_CONTENTION`)。
   - 强制板外/离板 `8-bit` eMMC ISP 仅允许 `1.8V` VCCQ (`1650..1950 mV`)、`isp_clk_mhz <= 26.0 MHz`、激活读时 `emmc_rst_n_held_low == True`、并硬阻断 `CMD24/CMD25` 写命令 (`BLOCKED_G49_EMMC_ISP_1V8_OR_WRITE_CMD_HAZARD`)。
3. **Gate `G50` (`IMX510` `p2:/setting/psd.bin & defdet.bin` 校准 NVS 锁定、Dual-Base ISO `800/12800` 与 `.cube` 3D MLUT 防双烤护栏)**：
   - 强制 `p2:/setting/psd.bin`、`p2:/setting/defdet.bin` 与 E-Mount `p18:/lens/LENSFILE.BIN` 只读不可变 (`sensor_cal_mutation_bytes == 0`、`same_body_sensor_cal_sha256_match == True`)，硬阻断跨机身或 FX6 donor 校准导入 (`BLOCKED_G50_SENSOR_CAL_NVS_MUTATION_OR_CROSS_BODY`)。
   - 强制 `IMX510` 双原生 ISO (`800` LCG `[-6.0, 22.0] dB` / `160..10000`；`12800` HCG `[0.0, 30.2] dB` / `12800..409600`) 模拟增益边界 (`BLOCKED_G50_IMX510_DUAL_BASE_ISO_GAIN_OUT_OF_BOUNDS`)。
   - 支持 `17^3` 与 `33^3` `.cube` 3D LUT 解析校验（拒绝 `NaN`/`Inf`/越界值），并在 `mlut_burn_in_authorized == False` 时硬阻断将监看 MLUT 双烤写入 `S-Log3 / S-Gamut3.Cine` XAVC 母带 (`BLOCKED_G50_CUBE_3DLUT_INVALID_OR_DOUBLE_BAKE`)。
4. **全量自动化验证实测**：
   - 新增 48 项双模式单测（正常模式与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 模式均 `48/48` 通过）。
   - `outputs/fx3-safety/tests` 全套测试：正常模式 `Ran 891 tests in 19.095s — OK`；`FX3_FX6_FORCE_CLEAN_ROOM=1` 模式 `Ran 891 tests in 18.303s — OK (skipped=1)`。
   - CLI `verify-g49-uart1v8-isp`、`verify-g50-imx510-sensor-cal`、`verify-50-gates`（`verified=47/50`）及 `verify-50-gates --dry-run-simulated-backup`（`verified=50/50`，四项写/挂载锁均为 `False`）均实测返回退出码 `0`。

### 1.2 未执行的实体相机台架操作（仅台架就绪，未接触物理机身）
- 尚未将实体 **ILME-FX3** 机身接入物理 `1.8V` USB-UART（`ttyAMA0`）、`VMC-BNCM1` BNC 时间码或离板 `1.8V 8-bit` eMMC ISP 探针；实体 Tier-0 门 `G10..G12` 仍未签发，`overall_ready_for_hardware_attach` 硬锁定为 `False`。
- 尚未对任何实体相机执行 `eMMC`、`SPI NOR` 或 `p2`/`p18` 写入；跨机型整分区刷写仍为 `BLOCKED / NO-GO`。

---

## 2. 交付清单（严格仅修改/新增 6 个所属文件）

| 序号 | 文件链接 | 变更类型 | 职责摘要 |
| :---: | :--- | :---: | :--- |
| 1 | [realhw_uart1v8_imx510_cal_and_50gate_guard.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/codex-h170-phase158-safety-50gates-uart-imx510-guard/outputs/fx3-safety/fx3_safety/realhw_uart1v8_imx510_cal_and_50gate_guard.py) | 新增 | 实现 `audit_phase158_donor_contracts`、纯辅助校验器、`G49`、`G50` 及 [`evaluate_50gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/codex-h170-phase158-safety-50gates-uart-imx510-guard/outputs/fx3-safety/fx3_safety/realhw_uart1v8_imx510_cal_and_50gate_guard.py#L2042-L2385) |
| 2 | [__init__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/codex-h170-phase158-safety-50gates-uart-imx510-guard/outputs/fx3-safety/fx3_safety/__init__.py) | 更新 | 导出 `G49` / `G50` 与 `50-Gate` 符号（无历史符号碰撞） |
| 3 | [__main__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/codex-h170-phase158-safety-50gates-uart-imx510-guard/outputs/fx3-safety/fx3_safety/__main__.py) | 更新 | 新增 CLI 子命令 `verify-g49-uart1v8-isp`、`verify-g50-imx510-sensor-cal`、`verify-50-gates` |
| 4 | [outputs/fx3-safety/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/codex-h170-phase158-safety-50gates-uart-imx510-guard/outputs/fx3-safety/README.md) | 更新 | 补充 Section 3.3 导出项与 Section 25（Phase 158 `G49`/`G50`/`verify-50-gates` 说明） |
| 5 | [test_realhw_uart1v8_imx510_cal_and_50gate_guard.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/codex-h170-phase158-safety-50gates-uart-imx510-guard/outputs/fx3-safety/tests/test_realhw_uart1v8_imx510_cal_and_50gate_guard.py) | 新增 | 48 项双模式单元测试与故障注入用例 |
| 6 | [reports/2026-11-15-phase158-safety-50gates-uart-imx510-guard/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/codex-h170-phase158-safety-50gates-uart-imx510-guard/reports/2026-11-15-phase158-safety-50gates-uart-imx510-guard/README.md) | 新增 | 本 Phase 158 验证与交付报告 |
