# Phase 170 — 实体 FX3 安全护栏 `G55`（`p12:/cert/RQ_LIC.DAT` C2PA 真实性证书只读锁与跨机型签名阻断）、`G56`（`VMC-BNCM1` `EXT-LK` SMPTE-12M LTC 电平/UART 互斥、`TC-OUT` BNC 掩码与 `IMX510` 6 轴陀螺仪 `NonRealTimeMeta.xml` 守卫）及统一 56-Gate 主预检报告

> **任务 ID**: `H184` · **目标硬件**: Sony ILME-FX3（`Ver. 7.02`, Model ID `0x91030080`, AP `CXD90057` *Mira* + CP `CXD90058` *Cetus*, Sensor `IMX510`）
> **核心结论**: 在严格保持 `G01..G54` 历史模块 100% 未修改的前提下，已完成安全门 **`G55`**、**`G56`** 与统一 **56-Gate 主预检引擎（[`evaluate_56gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h184-phase170-safety-56gates-c2pa-tc-gyro-guard/outputs/fx3-safety/fx3_safety/realhw_c2pa_tc_gyro_and_56gate_guard.py#L1709-L2068) / `verify-56-gates`）** 的双模式实现与验证。离线默认模式 `53/56` 通过（`G10..G12` 实体 Tier-0 门维持 `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED`），`--dry-run-simulated-backup` 模式 `56/56` 演练通过；全部核心写入/发射/挂机红线（`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`overall_ready_for_hardware_attach = False`）均保持硬锁定。

---

## 1. 严格区分：已实测事实 vs 未执行的实体台架操作

### 1.1 本次已实测事实（`os.O_RDONLY` 固件契约审计 + 离线安全门单元测试 + CLI + 净室卫生审计）
1. **双模式只读 (`os.O_RDONLY`) Donor 审计 ([`audit_phase170_donor_contracts`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h184-phase170-safety-56gates-c2pa-tc-gyro-guard/outputs/fx3-safety/fx3_safety/realhw_c2pa_tc_gyro_and_56gate_guard.py#L555-L672))**：
   - 实测经 `os.open(..., os.O_RDONLY)` 读取并校验 FX3 `7.02` 本地供体 `libsencore.so`（`377,328 B`，含 `C_GYRO_GAIN`、`MONITOR_GET_TEST_OUT_BNC_STATUS`、`GENLOCK`）、`libmpr.so`（`3,517,008 B`，含 `InfraC2PA`、`c2pa.created`、`sony.created`、`jumdSSIG`、`sigcert.p12`、`NonRealTimeMeta`、`LtcChangeTable`、`Gyroscope`）、`im.elf`（`40,920 B`，含 `/dev/nflasha12`、`/cert`、`libIMDB.so`、`libbackup.so`、`libosal_uipc.so`）、`cpapp-b.bin`（`15,980,568 B`，含 `ILME-FX3`、`0x91030080`、`C_ImagerCtrl_IMX510`、`LTC`、`Gyro Data`、`MTG_ULOCK_START_SLAVE`、`OTP`、`sabin`）及 `FX3-CX95900_ALLLANG-Backup.bin`（`2,229,740 B`，含 `BK4\0`、`90057`、`psd.bin`、`defdet.bin`、`lensfile.bin`），5 项供体 SHA-256 与关键标记全量通过；在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或缺失供体目录时确定性回退至 `CLEAN_ROOM_SYNTHETIC`，JSON 输出零原始索尼固件字节泄露。
2. **Gate `G55` (`p12:/cert/RQ_LIC.DAT` C2PA 只读锁与跨机身/跨机型签名防火墙，[`verify_c2pa_rq_lic_and_cross_model_signing_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h184-phase170-safety-56gates-c2pa-tc-gyro-guard/outputs/fx3-safety/fx3_safety/realhw_c2pa_tc_gyro_and_56gate_guard.py#L1037-L1283))**：
   - 强制 `p12:/cert`（`/dev/nflasha12`）以 `MS_RDONLY` 挂载且 `c2pa_cert_mutation_bytes == 0`、`c2pa_cert_write_requested == False`（否则 `BLOCKED_G55_P12_CERT_NON_RO_OR_MUTATION`）。
   - 校验同机身 `p12:/cert/RQ_LIC.DAT` 在 `H0..H3` 四阶段 SHA-256 完全一致且授权许可数 `1..100`（否则 `BLOCKED_G55_RQ_LIC_SHA256_DRIFT`）。
   - 硬阻断跨机身或跨机型（如 `ILME-FX6` / `ILME-FX30`）C2PA 签名密钥复用与 `sigcert` 提取请求（`c2pa_cross_model_signing_blocked == True`，`signing_model_id == 0x91030080`，`signing_model_name == "ILME-FX3"`，否则 `BLOCKED_G55_CROSS_MODEL_SIGNING_KEY`）。
3. **Gate `G56` (`VMC-BNCM1` `EXT-LK` SMPTE-12M LTC 电平/UART 互斥、`TC-OUT` BNC 掩码与 `IMX510` 6 轴陀螺仪 `NonRealTimeMeta.xml` 守卫，[`verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h184-phase170-safety-56gates-c2pa-tc-gyro-guard/outputs/fx3-safety/fx3_safety/realhw_c2pa_tc_gyro_and_56gate_guard.py#L1286-L1542))**：
   - 强制 `VMC-BNCM1` `EXT-LK` `SMPTE-12M` LTC 交流耦合电平处于 `500..4500 mV`（`0.5V–4.5V p-p`），硬阻断 `> 5000 mV` 过压注入与 `680 kΩ ±10%` 以外错误 ID 电阻，并强制与 Multi-USB `1.8V UART` 调试口互斥（`multi_usb_uart_1v8_active == False` when attached，否则 `BLOCKED_G56_LTC_VOLTAGE_OR_UART_MUX_CLASH`）。
   - 对仅限 FX6 的独立 BNC `TC-OUT` 驱动实施 fail-closed 掩码屏蔽（`fx6_tc_out_bnc_masked == True`、`tc_out_bnc_drive_requested == False`、`tc_direction == "IN"`，否则 `BLOCKED_G56_FX6_TC_OUT_BNC_UNMASKED`）。
   - 校验录制 `MXF/MP4` 的 `NonRealTimeMeta.xml`（`v2.20`）中 `IMX510` `8.7 ms` 卷帘快门读出时间及 6 轴 IMU（`2000 Hz`）陀螺仪数据包 CRC/单调时间戳与 Catalyst Browse / DaVinci Resolve 稳像兼容性（否则 `BLOCKED_G56_IMX510_GYRO_NRTM_CORRUPT`）。
4. **全量自动化验证实测**：
   - 新增 48 项双模式单测（正常 `LOCAL_DONOR_O_RDONLY` 模式 `Ran 48 tests in 2.851s — OK`；`FX3_FX6_FORCE_CLEAN_ROOM=1` 模式 `Ran 48 tests in 2.033s — OK`）。
   - `outputs/fx3-safety/tests` 全套测试：正常模式 `Ran 1035 tests in 26.327s — OK`；`FX3_FX6_FORCE_CLEAN_ROOM=1` 模式 `Ran 1035 tests in 23.625s — OK (skipped=1)`。
   - CLI `verify-g55-c2pa-cert`、`verify-g56-tc-gyro-meta`、`verify-56-gates`（`verified=53/56`）与 `verify-56-gates --dry-run-simulated-backup`（`verified=56/56`，`el3_payload_transmit_authorized=False`、`spi_nor_write_authorized=False`、`persistent_emmc_writes_authorized=False`、`overall_ready_for_hardware_attach=False`）均实测返回退出码 `0`。
   - `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` 实测 `ALL GREEN in 0.30s`。

### 1.2 未执行的实体相机台架操作（仅离线软件门禁就绪，未接触物理机身）
- 尚未从真实物理 **ILME-FX3** 机身采集或校验实机 `p12:/cert/RQ_LIC.DAT` `H0..H3` 哈希与 C2PA 签名证书状态，实体 Tier-0 门 `G10..G12` 仍维持未签发状态，`overall_ready_for_hardware_attach` 硬锁定为 `False`。
- 尚未向真实物理机身的 Multi-Port 接入实车 `VMC-BNCM1` BNC 线缆或抓取实机录制的 `MXF/MP4` `NonRealTimeMeta.xml` 6 轴陀螺仪码流，亦未对 `p12:/cert`、SPI NOR 或 eMMC 执行任何写入/刷机操作（`el3_payload_transmit_authorized = False`、`spi_nor_write_authorized = False`、`persistent_emmc_writes_authorized = False`、`persistent_write_release = False`）；跨机型整分区刷写仍为 `BLOCKED / NO-GO`。

---

## 2. 交付清单（严格仅修改/新增 6 个所属文件）

| 序号 | 文件链接 | 变更类型 | 职责摘要 |
| :---: | :--- | :---: | :--- |
| 1 | [realhw_c2pa_tc_gyro_and_56gate_guard.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h184-phase170-safety-56gates-c2pa-tc-gyro-guard/outputs/fx3-safety/fx3_safety/realhw_c2pa_tc_gyro_and_56gate_guard.py) | 新增 | 实现 [`audit_phase170_donor_contracts`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h184-phase170-safety-56gates-c2pa-tc-gyro-guard/outputs/fx3-safety/fx3_safety/realhw_c2pa_tc_gyro_and_56gate_guard.py#L555-L672)、纯辅助校验器、[`evaluate_g55_c2pa_cert`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h184-phase170-safety-56gates-c2pa-tc-gyro-guard/outputs/fx3-safety/fx3_safety/realhw_c2pa_tc_gyro_and_56gate_guard.py#L1550-L1624)、[`evaluate_g56_tc_gyro_meta`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h184-phase170-safety-56gates-c2pa-tc-gyro-guard/outputs/fx3-safety/fx3_safety/realhw_c2pa_tc_gyro_and_56gate_guard.py#L1627-L1701) 及 [`evaluate_56gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h184-phase170-safety-56gates-c2pa-tc-gyro-guard/outputs/fx3-safety/fx3_safety/realhw_c2pa_tc_gyro_and_56gate_guard.py#L1709-L2068) |
| 2 | [__init__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h184-phase170-safety-56gates-c2pa-tc-gyro-guard/outputs/fx3-safety/fx3_safety/__init__.py) | 更新 | 导出 `G55` / `G56` 与 `evaluate_56gate_preflight` 等 Phase 170 符号（无历史符号碰撞） |
| 3 | [__main__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h184-phase170-safety-56gates-c2pa-tc-gyro-guard/outputs/fx3-safety/fx3_safety/__main__.py) | 更新 | 新增 CLI 子命令 `verify-g55-c2pa-cert`、`verify-g56-tc-gyro-meta`、`verify-56-gates` |
| 4 | [outputs/fx3-safety/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h184-phase170-safety-56gates-c2pa-tc-gyro-guard/outputs/fx3-safety/README.md) | 更新 | 补充 Section 3.3 导出项与 Section 28（Phase 170 `G55`/`G56`/`verify-56-gates` 说明） |
| 5 | [test_realhw_c2pa_tc_gyro_and_56gate_guard.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h184-phase170-safety-56gates-c2pa-tc-gyro-guard/outputs/fx3-safety/tests/test_realhw_c2pa_tc_gyro_and_56gate_guard.py) | 新增 | 48 项双模式单元测试与故障注入用例 |
| 6 | [reports/2026-11-15-phase170-safety-56gates-c2pa-tc-gyro-guard/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h184-phase170-safety-56gates-c2pa-tc-gyro-guard/reports/2026-11-15-phase170-safety-56gates-c2pa-tc-gyro-guard/README.md) | 新增 | 本 Phase 170 验证与交付报告 |
