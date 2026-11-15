# Phase 172 — VM Stage 30（`30/30` 里程碑）真机 `p12:/cert/RQ_LIC.DAT` C2PA 锁、`VMC-BNCM1`（`EXT-LK`）SMPTE 时间码、`IMX510` 6 轴陀螺仪 `NonRealTimeMeta.xml` 与完整 10 步 Pre-Bench Go/No-Go HIL 协同仿真报告

> **任务 ID**: `H187` · **目标硬件基线**: Sony ILME-FX3（`Ver. 7.02`, Model ID `0x91030080`, AP `CXD90057` *Mira* + CP `CXD90058` *Cetus*, Sensor `IMX510`）
> **核心结论**: 已在 [`outputs/fx3-vm/`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h187-phase172-vm-stage30-c2pa-tc-gyro-prebench-hil/outputs/fx3-vm/) 完成 **Phase 172 / Stage 30（`30/30` 里程碑阶段）** 实现并接入 [`fx3_vm_coemulation_suite.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h187-phase172-vm-stage30-c2pa-tc-gyro-prebench-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py)。双模只读供体审计、四大 HIL 协同仿真支柱（Pillar A–D）、`30/30` 全板协同仿真（本地 CLI `2.566s < 2.7s` / 洁净室 CLI `0.847s < 1.3s`）、新增 46 项单测与全量 `1,084` 项 `fx3-vm` 单测及洁净室卫生门禁均实测 `100%` 通过；全部红线保持硬锁定（`persistent_emmc_writes_authorized = False`、`emmc_nflasha_write_count = 0`、`c2pa_cert_mutation_bytes = 0`、`p2_mutation_bytes = 0`、`p18_mutation_bytes = 0`、`cp_mutation_bytes = 0`）。

---

## 1. 严格区分：已实测事实 vs 未执行的实体相机台架操作

### 1.1 本次已实测事实（`os.O_RDONLY` 供体审计 + HIL 协同仿真 + 单元测试 + 洁净室审计）

1. **双模只读 (`os.O_RDONLY`) 供体审计 ([`inspect_phase172_donors`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h187-phase172-vm-stage30-c2pa-tc-gyro-prebench-hil/outputs/fx3-vm/realhw_c2pa_tc_gyro_and_prebench_gonogo_coemulator.py#L981-L1106))**：
   - 本地模式严格使用 `os.open(..., os.O_RDONLY)` + 缓冲 `os.read` 校验 FX3 `7.02` 与 FX6 `6.01` 的 **10 份核心供体**：
     - `cpapp-b.bin`（`15,980,568 B` vs `17,952,816 B`）：均含 ARM32 LE 入口字与 `0x00108000` 加载基址及 `IMX510` / `C_ImagerCtrl_IMX510` / `LTC` / `Gyro Data` / `OTP` 标记；`ILME-FX3` 与 `MTG_ULOCK_START_SLAVE` 在 FX3 存在且在 FX6 中为 `0` 命中。
     - `libmpr.so`（`3,517,008 B` / `3,541` 导出 vs `28,921,824 B` / `4,271` 导出）：均含 `NonRealTimeMeta` / `LtcChangeTable` / `Gyroscope` / `SetMovieRecParam`；FX3 v7.02 独有 C2PA 标记 `InfraC2PA` / `c2pa.created` / `sony.created` / `jumdSSIG` / `sigcert.p12` 在 FX6 v6.01 中 `0` 命中。
     - `libsencore.so`（`377,328 B` vs `401,952 B`）：同为 `355` 导出 / `130` 导入，均含 `C_GYRO_GAIN` / `MONITOR_GET_TEST_OUT_BNC_STATUS` / `GENLOCK` / `MPR_CMD_` / `SenserIfStart`。
     - `im.elf`（`40,920 B`）：零差异 ELF64 ABI（`11` 导出 / `85` 导入），均含 `/dev/nflasha12`、`/cert`、`/dev/nflasha2`、`/dev/nflasha15`、`libIMDB.so`、`libbackup.so`、`libosal_uipc.so`。
     - `Backup.bin`（`2,229,740 B` / `819` 子系统 vs `2,253,333 B` / `840` 子系统）：`BK4\x00` 魔数与 `90057` / `psd.bin` / `defdet.bin` / `lensfile.bin` / `tomco` 标记完备。
   - 在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺失时自动切换至确定性 `CLEAN_ROOM_SYNTHETIC` 合成本基线，JSON 报告零原始索尼固件字节泄漏。
2. **Pillar A — `p12:/cert/RQ_LIC.DAT` 单机 C2PA 许可证 `MS_RDONLY` 锁与防伪防火墙 ([`evaluate_pillar_a_c2pa_lock_and_firewall`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h187-phase172-vm-stage30-c2pa-tc-gyro-prebench-hil/outputs/fx3-vm/realhw_c2pa_tc_gyro_and_prebench_gonogo_coemulator.py#L1270-L1304))**：
   - 协同仿真 Stage-B 启动、电影录制与干净卸载全周期，验证 `p12:/cert` 强制 `MS_RDONLY`、`c2pa_cert_mutation_bytes == 0`、`H0 == H1 == H2 == H3` SHA-256 一致，并 fail-closed 阻断跨机身克隆及跨型号（`ILME-FX6` / `ILME-FX30` / `ILCE-7SM3`）签名与 `sigcert.p12` 导出请求。
3. **Pillar B — `VMC-BNCM1`（`AD_JACK_IN` Pin 10 -> `EXT-LK`）SMPTE-12M LTC-IN & Multi-USB UART 争用互锁 ([`evaluate_pillar_b_vmc_bncm1_ltc_interlock`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h187-phase172-vm-stage30-c2pa-tc-gyro-prebench-hil/outputs/fx3-vm/realhw_c2pa_tc_gyro_and_prebench_gonogo_coemulator.py#L1459-L1490))**：
   - 验证 `23.98 / 24 / 25 / 29.97 / 59.94` fps 下 `0.5V–4.5V p-p` 外置 LTC 锁相、SMPTE-12M `0x3FFD` 同步与 User-Bits 透传；对 `> 5.0V p-p` 过压、错误 ID 电阻、Multi-USB `1.8V UART` 引脚争用及 FX6 BNC `TC-OUT` 驱动请求实施 fail-closed 阻断与掩码屏蔽（`tc_direction == "IN"`、`uart_contention_damage_events == 0`、`over_voltage_damage_events == 0`）。
4. **Pillar C — `IMX510`（`8.7 ms` 读出）+ 6 轴 IMU 陀螺仪 + `p18:/lens` `NonRealTimeMeta.xml` 管线 ([`evaluate_pillar_c_imx510_gyro_nrtm`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h187-phase172-vm-stage30-c2pa-tc-gyro-prebench-hil/outputs/fx3-vm/realhw_c2pa_tc_gyro_and_prebench_gonogo_coemulator.py#L1688-L1718))**：
   - 模拟录制 `XAVC S-I`（MP4）与 `XAVC-I`（MXF）片段，生成并 XML 往返校验 Sony `NonRealTimeMeta.xml`（`ver.2.20`），在不触碰 `p2` 与 `p18`（`p2_mutation_bytes == 0`、`p18_mutation_bytes == 0`）的前提下证明 100% Catalyst Browse 与 DaVinci Resolve 增稳 Schema 合规，并 fail-closed 拦截陀螺仪 CRC 异常、时间戳回退或读出延迟漂移。
5. **Pillar D — 完整 10 步 Pre-Bench Go/No-Go 干跑生命周期 ([`evaluate_pillar_d_10step_prebench_lifecycle`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h187-phase172-vm-stage30-c2pa-tc-gyro-prebench-hil/outputs/fx3-vm/realhw_c2pa_tc_gyro_and_prebench_gonogo_coemulator.py#L1853-L1885))**：
   - 完整协同仿真 10 步实操预演闭环（被动 USB -> `054C:0DA1 -> 054C:0336` `op=0xFF` 金丝雀 -> 双介质 16 存储面 Tier-0 备份 -> `p12`/`p18` `MS_RDONLY` -> `/dev/cnflasha15` `.orig` 暂存 -> 双启动 + `EXT-LK` -> Big-6 录制 + `NonRealTimeMeta.xml` -> `.RSV` + C2PA 核查 -> 干净卸载 -> `16/16 H0 == H3` 出厂零残留封签），并验证任何备份缺失、哈希漂移、残余 `.orig`/分片或未授权写请求立即触发 `NO_GO`。
6. **全量自动化验证实测结果（全部使用 `/usr/bin/python3 -B`）**：
   - Stage 30 独立自检（`--self-test --summary`）：
     - 本地 `LOCAL_DONOR_RDONLY`：`[PASS]`（`c2pa_mut=0 | p18_mut=0 | steps=10/10 | h0_eq_h3=16/16 | go=GO_DRYRUN_HIL | emmc_wr=0 | digest=5a58ff6adc7d`）
     - 洁净室 `CLEAN_ROOM_SYNTHETIC`：`[PASS]`（`c2pa_mut=0 | p18_mut=0 | steps=10/10 | h0_eq_h3=16/16 | go=GO_DRYRUN_HIL | emmc_wr=0 | digest=6019fbc5b5a3`）
   - 全板 `30/30` 阶段协同仿真（[`fx3_vm_coemulation_suite.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h187-phase172-vm-stage30-c2pa-tc-gyro-prebench-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py) `--summary`）：
     - 本地只读供体子进程耗时 `2.566s`（`< 2.7s`），`[PASS] ... digest=ac22f0be42e3`
     - 洁净室模式子进程耗时 `0.847s`（`< 1.3s`），`[PASS] ... digest=d9b86a645c07`
   - Phase 172 新增 46 项双模单测（[`test_realhw_c2pa_tc_gyro_and_prebench_gonogo_coemulator.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h187-phase172-vm-stage30-c2pa-tc-gyro-prebench-hil/outputs/fx3-vm/tests/test_realhw_c2pa_tc_gyro_and_prebench_gonogo_coemulator.py)）：
     - 本地模式：`Ran 46 tests in 6.730s — OK`
     - `FX3_FX6_FORCE_CLEAN_ROOM=1`：`Ran 46 tests in 4.851s — OK`
   - 全量 `outputs/fx3-vm/tests` `unittest discover`：
     - 本地模式：`Ran 1084 tests in 82.531s — OK`
     - `FX3_FX6_FORCE_CLEAN_ROOM=1`：`Ran 1084 tests in 77.756s — OK (skipped=3)`
   - `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only`：`ALL GREEN in 0.04s`（二进制 / `.pyc` 卫生审计全清）。

### 1.2 未执行的实体相机台架操作（仅软件仿真就绪，未接触物理机身）

- 尚未连接真实物理 **ILME-FX3** 机身，未执行实体 USB `054C:0DA1 -> 054C:0336` `op=0xFF` 探测或实机 16 存储面 Tier-0 备份采集。
- 尚未向实体 FX3 Multi-Port 接入真实 `VMC-BNCM1` BNC 线缆，亦未在实体相机上实拍输出包含 `NonRealTimeMeta.xml` 陀螺仪码流的真机 MXF/MP4 素材。
- 尚未对任何实体相机执行 eMMC / SPI NOR / `p12:/cert` / `p18:/lens` / CP `p8` / OTP / RPMB 写入（`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`）；跨机型整分区刷写与物理机刷机仍保持 `BLOCKED / NO-GO`。

---

## 2. 交付文件清单（严格限定所属范围）

| 序号 | 文件链接 | 变更类型 | 职责摘要 |
| :---: | :--- | :---: | :--- |
| 1 | [realhw_c2pa_tc_gyro_and_prebench_gonogo_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h187-phase172-vm-stage30-c2pa-tc-gyro-prebench-hil/outputs/fx3-vm/realhw_c2pa_tc_gyro_and_prebench_gonogo_coemulator.py) | 新增 | Stage 30（`30/30`）双模供体审计、Pillar A–D HIL 协同仿真引擎与 CLI |
| 2 | [fx3_vm_coemulation_suite.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h187-phase172-vm-stage30-c2pa-tc-gyro-prebench-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py) | 更新 | 接入 [`run_stage30_realhw_c2pa_tc_gyro_prebench_hil`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h187-phase172-vm-stage30-c2pa-tc-gyro-prebench-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py#L1760-L1819) 与 `--skip-phase172`，达成 `30/30` 阶段 |
| 3 | [outputs/fx3-vm/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h187-phase172-vm-stage30-c2pa-tc-gyro-prebench-hil/outputs/fx3-vm/README.md) | 更新 | 新增 Phase 172 / Stage 30（`30/30`）文档与 CLI/单测命令 |
| 4 | [test_realhw_c2pa_tc_gyro_and_prebench_gonogo_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h187-phase172-vm-stage30-c2pa-tc-gyro-prebench-hil/outputs/fx3-vm/tests/test_realhw_c2pa_tc_gyro_and_prebench_gonogo_coemulator.py) | 新增 | 46 项双模单元测试（供体、Pillar A–D、XML 往返、`30/30` 套件、耗时与卫生门禁） |
| 5 | [test_realhw_cxd90058_sabin_codec_and_seal_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h187-phase172-vm-stage30-c2pa-tc-gyro-prebench-hil/outputs/fx3-vm/tests/test_realhw_cxd90058_sabin_codec_and_seal_coemulator.py) | 更新 | 将 Stage 29 硬编码总阶段数 `== 29` 放宽为 `>= 29`，兼容 `30/30` 套件 |
| 6 | [reports/2026-11-15-phase172-vm-stage30-c2pa-tc-gyro-prebench-hil/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h187-phase172-vm-stage30-c2pa-tc-gyro-prebench-hil/reports/2026-11-15-phase172-vm-stage30-c2pa-tc-gyro-prebench-hil/README.md) | 新增 | 本 Phase 172（Stage 30 `30/30` 里程碑）交付与验证报告 |
