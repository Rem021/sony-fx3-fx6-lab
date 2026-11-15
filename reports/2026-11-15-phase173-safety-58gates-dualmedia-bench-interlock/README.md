# Phase 173 — 实体 FX3 安全护栏 `G57`（双介质独立 Tier-0 冷备份设备 ID 隔离、`16/16` SHA-256 校验与 `GF(256)` `0x11d` 比特翻转清洗恢复）、`G58`（两步人工台架授权、`NP-FZ100 >= 80% / >= 7400 mV` 与零自动刷机互锁）及统一 58-Gate 主预检报告

> **任务 ID**: `H188` · **目标硬件**: Sony ILME-FX3（`Ver. 7.02`, Model ID `0x91030080`, AP `CXD90057` *Mira* + CP `CXD90058` *Cetus*）
> **核心结论**: 在严格保持 `G01..G56` 历史模块 100% 未修改的前提下，已完成安全门 **`G57`**、**`G58`** 与统一 **58-Gate 主预检引擎（[`evaluate_58gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h188-phase173-safety-58gates-dualmedia-bench-interlock/outputs/fx3-safety/fx3_safety/realhw_dualmedia_bench_interlock_and_58gate_guard.py#L1804-L2175) / `verify-58-gates`）** 的双模式实现与验证。离线默认模式 `55/58` 通过（`G10..G12` 实体 Tier-0 门维持 `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED`），`--dry-run-simulated-backup` 模式 `58/58` 演练通过；全部核心写入/发射/自动刷机/挂机红线（`EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`、`SPI_NOR_WRITE_AUTHORIZED = False`、`PERSISTENT_EMMC_WRITES_AUTHORIZED = False`、`PERSISTENT_WRITE_RELEASE = False`、`PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED = False`、`overall_ready_for_hardware_attach = False`）均保持硬锁定。

---

## 1. 严格区分：已实测事实 vs 未执行的实体台架操作

### 1.1 本次已实测事实（`os.O_RDONLY` 固件契约审计 + 离线安全门单元测试 + CLI + 净室卫生审计）
1. **双模式只读 (`os.O_RDONLY`) Donor 审计 ([`audit_phase173_donor_contracts`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h188-phase173-safety-58gates-dualmedia-bench-interlock/outputs/fx3-safety/fx3_safety/realhw_dualmedia_bench_interlock_and_58gate_guard.py#L666-L783))**：
   - 实测经 `os.open(..., os.O_RDONLY)` 读取并校验 FX3 `7.02` 本地供体 `libsencore.so`（`377,328 B`，含 `C_GYRO_GAIN`、`MONITOR_GET_TEST_OUT_BNC_STATUS`、`GENLOCK`、`DSP`、`AVC`）、`libmpr.so`（`3,517,008 B`，含 `InfraC2PA`、`c2pa.created`、`sony.created`、`jumdSSIG`、`sigcert.p12`、`NonRealTimeMeta`、`LtcChangeTable`、`Gyroscope`）、`im.elf`（`40,920 B`，含 `/dev/nflasha12`、`/cert`、`libIMDB.so`、`libbackup.so`、`libosal_uipc.so`）、`cpapp-b.bin`（`15,980,568 B`，含 `ILME-FX3`、`0x91030080`、`C_ImagerCtrl_IMX510`、`LTC`、`Gyro Data`、`MTG_ULOCK_START_SLAVE`、`OTP`、`sabin`）及 `FX3-CX95900_ALLLANG-Backup.bin`（`2,229,740 B`，含 `BK4\0`、`90057`、`psd.bin`、`defdet.bin`、`lensfile.bin`），5 项供体 SHA-256 与关键标记全量通过；在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或缺失供体目录时确定性回退至 `CLEAN_ROOM_SYNTHETIC`，JSON 输出零原始索尼固件字节泄露。
2. **Gate `G57`（双介质独立 Tier-0 冷备份设备 ID 隔离、`16/16` SHA-256 校验与 `GF(256)` 比特翻转清洗恢复，[`verify_dual_media_vault_and_gf256_scrub_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h188-phase173-safety-58gates-dualmedia-bench-interlock/outputs/fx3-safety/fx3_safety/realhw_dualmedia_bench_interlock_and_58gate_guard.py#L1194-L1344)）**：
   - 强制双备份仓库位于物理分离设备（`media_a_st_dev != media_b_st_dev`，且挂载点/卷 ID 互不重叠），硬阻断同盘伪备份（否则 `BLOCKED_G57_SINGLE_MEDIA_OR_SAME_ST_DEV`）。
   - 校验双介质间 `16/16` 规范 Tier-0 存储面（`sector0`、`emmc_boot0`、`emmc_boot1`、`p1_updater`..`p18_lens`、`spi_nor_ro`）SHA-256 完全一致（`parity_matched_count == 16`，否则 `BLOCKED_G57_16_SURFACE_SHA256_MISMATCH`）。
   - 纯 Python 实现 `GF(2^8)`（本原多项式 `0x11D`）RAID-6 P+Q 校验生成、比特翻转（bit-rot）巡检清洗与 `<= 2` 分片丢失/损毁恢复验证（`unrecoverable_chunk_count == 0`，`>= 3` 分片同时丢失或未修复损坏时 fail-closed 返回 `BLOCKED_G57_GF256_SCRUB_OR_QUORUM_LOSS`）。
3. **Gate `G58`（两步显式人工台架授权、`NP-FZ100 >= 80%` / `>= 7400 mV` 与零自动刷机互锁，[`verify_two_step_bench_interlock_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h188-phase173-safety-58gates-dualmedia-bench-interlock/outputs/fx3-safety/fx3_safety/realhw_dualmedia_bench_interlock_and_58gate_guard.py#L1347-L1638)）**：
   - 硬锁定零自动刷机互锁：严禁任何自动化脚本或 AI Agent 自授权物理刷写（`agent_auto_flash_blocked == True`、`auto_flash_requested == False`、`ai_agent_self_authorize_attempted == False`，仓库常量硬锁 `False`，否则 `BLOCKED_G58_AUTO_FLASH_INTERLOCK_VIOLATION`）。
   - 校验刷写前 `NP-FZ100` 电池满足 `>= 80%` SOC 且 `>= 7400 mV` 端电压（默认 `85% / 7800 mV`，否则 `BLOCKED_G58_BATTERY_BELOW_PREFLASH_THRESHOLD`）。
   - 校验 `op=0xFF` RAM 金丝雀 `FX3S0OK`（`528 B`）回执及 `MSC 054C:0DA1` 无残留返回、双介质 `FX3RCPT1`（`528 B`）冷备回执哈希一致性（否则 `BLOCKED_G58_CANARY_OR_FX3RCPT1_UNVERIFIED`），并在任何台架实操请求时强制要求 Step-1 人工确认 + Step-2 确认短语 `CONFIRM-ILME-FX3-0x91030080-BENCH`（否则 `BLOCKED_G58_TWO_STEP_HUMAN_AUTH_MISSING`）。
4. **全量自动化验证实测**：
   - 新增 48 项双模式单测（正常 `LOCAL_DONOR_O_RDONLY` 模式 `Ran 48 tests in 3.071s — OK`；`FX3_FX6_FORCE_CLEAN_ROOM=1` 模式 `Ran 48 tests in 1.948s — OK`）。
   - `outputs/fx3-safety/tests` 全套测试：正常模式 `Ran 1083 tests in 29.972s — OK`；`FX3_FX6_FORCE_CLEAN_ROOM=1` 模式 `Ran 1083 tests in 26.208s — OK (skipped=1)`。
   - CLI `verify-g57-dualmedia-vault`、`verify-g58-bench-interlock`、`verify-58-gates`（`verified=55/58`）、`verify-58-gates --dry-run-simulated-backup`（`verified=58/58`）与 `--clean-room --dry-run-simulated-backup`（`verified=58/58`, `mode=CLEAN_ROOM_SYNTHETIC`）均实测返回退出码 `0`，且所有授权红线保持 `False`、`agent_auto_flash_blocked=True`。
   - `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` 实测 `Clean-Room Audit: ALL GREEN in 1.44s`。

### 1.2 未执行的实体相机台架操作（仅离线软件门禁就绪，未接触物理机身）
- 尚未将真实物理 **ILME-FX3** 机身接入台架或实际向两台独立物理介质（如 SDXC 冷备卡与 Mac 宿主冷备库）落盘写入实体机 `16` 个 Tier-0 分区镜像与 `FX3RCPT1` 回执；实体 Tier-0 门 `G10..G12` 仍维持未签发状态，`overall_ready_for_hardware_attach` 硬锁定为 `False`。
- 尚未对真实物理相机发起 `op=0xFF` RAM 金丝雀探测、两步人工台架授权确认，亦未对 SPI NOR 或 eMMC 执行任何持久写入/刷机操作（`el3_payload_transmit_authorized = False`、`spi_nor_write_authorized = False`、`persistent_emmc_writes_authorized = False`、`persistent_write_release = False`、`physical_flash_auto_exec_authorized = False`）；跨机型整分区刷写仍为 `BLOCKED / NO-GO`。

---

## 2. 交付清单（严格仅修改/新增 6 个所属文件）

| 序号 | 文件链接 | 变更类型 | 职责摘要 |
| :---: | :--- | :---: | :--- |
| 1 | [realhw_dualmedia_bench_interlock_and_58gate_guard.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h188-phase173-safety-58gates-dualmedia-bench-interlock/outputs/fx3-safety/fx3_safety/realhw_dualmedia_bench_interlock_and_58gate_guard.py) | 新增 | 实现 [`audit_phase173_donor_contracts`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h188-phase173-safety-58gates-dualmedia-bench-interlock/outputs/fx3-safety/fx3_safety/realhw_dualmedia_bench_interlock_and_58gate_guard.py#L666-L783)、`GF(256)` P+Q 编码与恢复、[`evaluate_g57_dualmedia_vault`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h188-phase173-safety-58gates-dualmedia-bench-interlock/outputs/fx3-safety/fx3_safety/realhw_dualmedia_bench_interlock_and_58gate_guard.py#L1646-L1719)、[`evaluate_g58_bench_interlock`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h188-phase173-safety-58gates-dualmedia-bench-interlock/outputs/fx3-safety/fx3_safety/realhw_dualmedia_bench_interlock_and_58gate_guard.py#L1722-L1796) 及 [`evaluate_58gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h188-phase173-safety-58gates-dualmedia-bench-interlock/outputs/fx3-safety/fx3_safety/realhw_dualmedia_bench_interlock_and_58gate_guard.py#L1804-L2175) |
| 2 | [__init__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h188-phase173-safety-58gates-dualmedia-bench-interlock/outputs/fx3-safety/fx3_safety/__init__.py) | 更新 | 导出 `G57` / `G58` 与 `evaluate_58gate_preflight` 等 Phase 173 符号（无历史符号碰撞） |
| 3 | [__main__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h188-phase173-safety-58gates-dualmedia-bench-interlock/outputs/fx3-safety/fx3_safety/__main__.py) | 更新 | 新增 CLI 子命令 `verify-g57-dualmedia-vault`、`verify-g58-bench-interlock`、`verify-58-gates` |
| 4 | [outputs/fx3-safety/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h188-phase173-safety-58gates-dualmedia-bench-interlock/outputs/fx3-safety/README.md#L755-L781) | 更新 | 补充 Section 3.3 导出项与 Section 29（Phase 173 `G57`/`G58`/`verify-58-gates` 说明） |
| 5 | [test_realhw_dualmedia_bench_interlock_and_58gate_guard.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h188-phase173-safety-58gates-dualmedia-bench-interlock/outputs/fx3-safety/tests/test_realhw_dualmedia_bench_interlock_and_58gate_guard.py) | 新增 | 48 项双模式单元测试与故障注入用例 |
| 6 | [reports/2026-11-15-phase173-safety-58gates-dualmedia-bench-interlock/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h188-phase173-safety-58gates-dualmedia-bench-interlock/reports/2026-11-15-phase173-safety-58gates-dualmedia-bench-interlock/README.md) | 新增 | 本 Phase 173 验证与交付报告 |
