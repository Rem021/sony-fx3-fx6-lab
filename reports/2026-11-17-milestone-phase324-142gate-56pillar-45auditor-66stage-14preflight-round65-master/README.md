# Grand Milestone Phase 324 实机主线 6 支柱总闸门（`>=142-Gate` · `>=56-Pillar` · `>=45-Auditor` · `>=66-Stage` · `14/14 Bench Preflights (Ph186..Ph321)` · `>=38 QEMU Rounds / >=114 Runs / >=76 PNGs`）闭环报告

## 一、核心结论（结论先行）

1. **Grand Milestone Phase 324 总闸门（`schema = "realhw_milestone324_master_gate_v1"` / `make verify-milestone-324`）已完成端到端闭环并通过三态全量实测验证**：
   - 严格在 8 个受控归属文件内交付 [`realhw_milestone324_master_gate.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone324_master_gate.py)、公共符号非遮蔽导出 [`__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py)、CLI 子命令 `verify-milestone-324`（[`__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py)，支持 `--repo-root` / `--fx6-lib-dir` / `--fx3-modules-dir` / `--clean-room` / `--force-clean-room` / `--simulate-bench-dry-run` / `--simulate-ready-bench` / `--json` / `--out` / `--output` / `--markdown-out`，无未转义 `%`）、模块文档 [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md)（第 56 节）、双模单元测试 [`test_realhw_milestone324_master_gate.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_milestone324_master_gate.py)（84 项测试，全部采用 `sys.executable`、`GITHUB_ACTIONS == 'true'` 宽裕耗时预算、`assertGreaterEqual` 前向兼容下界及无 `Mac/work` 无供体 Linux CI 自动退避测试）、顶层 [`Makefile`](../../Makefile) 目标 `verify-milestone-324`（接入 `verify-fast`，完整保留历史里程碑目标）及 [`.github/workflows/clean-room-ci.yml`](../../.github/workflows/clean-room-ci.yml)（新增 `verify-142-gates`、`verify-56pillar-recovery` 与 `verify-milestone-324 --force-clean-room`）。
   - 将 **Waves 21–61+（Phases 134–323）** 全部 6 大实机主线支柱与 **Rounds 28–65（`38/38` 轮实机内核 QEMU、`114/114` 子运行、`76/76` 脱敏 PNG 收据）** 收敛为带防篡改 `milestone324_sha256` 的单张主证书：
     - **`LOCAL_DONOR_O_RDONLY` 模式**：`6/6` 支柱全绿（`gate142=139/142` 离线 / `142/142` 模拟干跑、`recovery=56/56`、`cnflasha_ro=True`、`auditors=45/45`、`vm_stages=66/66`、`Ph186..Ph321` 全部 `14/14` 双态合规、`H0==H3=16/16`、`e_nd_tx=0`、`rf_pkts=0`、`slot1_writes=0`、`qemu=38/38(114/114)`、`pngs=76/76(max=27467B)`）；
     - **`CLEAN_ROOM_SYNTHETIC` 模式（`FX3_FX6_FORCE_CLEAN_ROOM=1` / `FX3_CLEAN_ROOM_TEST=1` / 无 `Mac/work` 无供体环境）**：零索尼专有固件依赖，`6/6` 支柱全绿并通过 `verify_realhw_milestone324_master_gate` 防篡改 SHA-256 校验。
2. **前向兼容（`>=` 下界 + 动态自动发现）与历史向后兼容双保证**：
   - `P1`（动态发现 `fx3_safety` 最高 `evaluate_<N>gate_preflight`，`N >= 142`，无缝兼容并行轨道合入 `144/146...`，已通过测试验证 `144` 前向兼容及上游 `G135..G140` 链式 override）、`P2`（动态发现 `fx3_recovery` 最高 `evaluate_realhw_<M>pillar_recovery_master`，`M >= 56`，无缝兼容 `57/58...`，校验 `pillar56_a_*`/`pillar56_b_*` 子字典及前向可选子字典）、`P3`（`>= 45` 审计器 + 动态发现 `46th+`）、`P4`（`>= 66` VM HIL 阶段 + 自动发现 `Stage 67+`）、`P6`（`>= 38` 轮 / `>= 114` 运行 / `>= 76` PNG 收据 + 动态发现 `Round 66+`）。
   - 历史 `verify-milestone-311` 经实测 `6/6 PASS`（并验证其已在本地 `142` 闸门、`56` 支柱、`66` 阶段、`38` 轮 QEMU 下前向绿灯通过），`test_realhw_milestone311_master_gate.py` `78/78 OK`。
3. **严格区分实测事实与未执行物理真机边界 / 推断**：
   - **实测事实（Verified Facts）**：`test_realhw_milestone324_master_gate.py` 在 `LOCAL_DONOR_O_RDONLY`（`84/84 OK`，`20.288s`）、`FX3_CLEAN_ROOM_TEST=1`（`84/84 OK`，`19.823s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`84/84 OK`，`15.763s`）三态全量通过；`make verify-milestone-324`（双态）、`FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-324`、`make verify-milestone-311`、`verify-142-gates`（`142/142`）、`verify-56pillar-recovery`（`56/56`）、`test_realhw_milestone311_master_gate.py`（`78/78 OK`）及 `make clean-audit`（`ALL GREEN`）均经本工作树现场运行确认通过。注：P5 中上游 `p204` 干跑内部 `report_sha256` 每次运行时独立生成，但主报告自身 `to_deterministic_json()` 与 `compute_milestone324_sha256()` 在固定输入下完全确定性一致。
   - **未执行物理真机边界 / 推断边界（Not Executed Physically / Boundary）**：**真实物理 Sony ILME-FX3 相机上电 USB 连接、Tier-0 物理实机冷备签收及现场插卡/烧录均尚未执行（也未对真机产生任何写入）**；`--simulate-bench-dry-run` 仅代表离线台架预演，不等价于真机物理授权。全链路物理安全红线硬锁定为拒绝（`overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`cnflasha_userspace_write_blocked = True`、`persistent_emmc_writes_authorized = False`、`cross_model_flash_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`、`e_nd_actuator_tx_count = 0`、`rf_packets_transmitted = 0`、`slot1_data_sector_writes = 0`、`otp_fuse_touches = 0`、`rpmb_counter_increments = 0`、`passive_tx_bytes_emitted = 0`）。

---

## 二、六大实机支柱验收矩阵（`realhw_milestone324_master_gate_v1`）

| 支柱 ID | 支柱名称 | 验收契约与前向兼容机制 | 实测结果（Local Donor / Clean-Room） |
| :--- | :--- | :--- | :--- |
| **`P1`** | `SAFETY_142PLUS_GATE_REALHW_MASTER_PREFLIGHT` | 动态发现最高 `fx3_safety.evaluate_<N>gate_preflight`（`N >= 142`，兼容 `144+`）：离线 `== N - 3`（`139/142`，`G10..G12` fail-closed），`--simulate-bench-dry-run` `N/N`（`142/142`），逐项校验 `G63..G142+`（覆盖 Waves 21–61+），硬锁 `ready_attach=False`、`emmc_writes_auth=False`、`cross_model_flash_auth=False`、`usb_tx=0`、`leaked=0` | `offline=139/142` · `simulated=142/142` · `cross_model_flash=False` · `usb_tx=0` · **PASS** |
| **`P2`** | `FIFTY_SIX_PLUS_PILLAR_RECOVERY_MASTER_VAULT` | 动态发现最高 `fx3_recovery.evaluate_realhw_<M>pillar_recovery_master`（`M >= 56`，兼容 `57+`）：`M/M` 全绿（`all_passed=True`），校验 `pillar56_a_*` / `pillar56_b_*` 及 `P55..P56` 零越界计数器、`cnflasha_userspace_write_blocked=True`、`otp=0`、`rpmb=0`、`passive_tx=0`、`usb_pkts=0`、`leaked=0` | `56/56` (`cnflasha_ro=True`) · `otp=0, rpmb=0, passive_tx=0, usb_pkts=0` · **PASS** |
| **`P3`** | `FORTY_FIVE_PLUS_FIRMWARE_LAB_REALBIN_AUDITORS` | 校验全部 `45/45` 项 `fx3_firmware_lab` 实机只读审计器并动态发现 `46th+ realhw_*_auditor.py`，锁定 `raw_firmware_bytes_leaked=0`、`e_nd_actuator_tx_count=0`、`calibration_mutation_bytes=0` | `45/45` · `e_nd_tx=0` · `cal_mut=0B` · `leaked=0B` · **PASS** |
| **`P4`** | `SIXTY_SIX_PLUS_STAGE_VM_HIL_COEMULATION` | 运行 `fx3_vm_coemulation_suite` 启用 Stages `1..66+`（涵盖 Stage 63..66 `ShadingComp` / `AFIlluminator` / `SwitchVH` / `ReverseCopySlot1` / `ZeroEVF` / `DialCustomize` / `LUTEmbed` 并自动发现 `Stage 67+`），锁定 `vm_stages_passed >= 66`、`fx3_physical_dial_count == 3`、`raw_firmware_bytes_leaked=0`、`physical_device_writes=0`、`emmc_corruptions=0` | `66/66` · `phys_writes=0` · `emmc_corruptions=0` · `leaked=0B` · **PASS** |
| **`P5`** | `TETRADECUPLE_BENCH_READINESS_PREFLIGHTS_PH186_TO_PH321` | 校验 `Phase 136/143/154` 及全套 `14/14` 物理台架预检器（`Ph186`..`Ph307` + 新增 `Ph316` `bright-monitoring-shot-mark-big6-home-and-ssh-auth` & `Ph321` `rec-media-autoswitch-proxy-cloud-mymenu-and-ftpes`）：离线均为 `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT`，模拟干跑均为 `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH`，`16/16 H0==H3`，`e_nd_tx=0`，`rf_pkts=0`，`slot1_data_sector_writes=0` | `14/14` (`Ph186..Ph321`) · `H0==H3=16/16` · `rf_pkts=0` · `slot1_writes=0` · `ready_attach=False` · **PASS** |
| **`P6`** | `REAL_FX3_702_QEMU_ROUNDS_28_TO_65_PLUS_AND_PNG_RECEIPTS` | 校验 `ILME-FX3 Ver. 7.02` (`4.9.337-scel+`) ARM64 QEMU 实机内核演练 `Rounds 28..65+`（`>= 38` 轮、`>= 114` 子运行、`>= 76` 脱敏 PNG 收据且每张 `< 51,200 B`，动态发现 `Round 66+`），`16/16 H0==H3`、`emmc=0`、`nop=0`、`crashes=0`、`leaked=0` | `38/38` 轮 (`114/114` runs) · `76/76` PNG (`max=27,467 B`) · `emmc=0, leaked=0` · **PASS** |

---

## 三、严格 8 文件交付清单

1. [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone324_master_gate.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone324_master_gate.py) — Phase 324 6 支柱并行主闸门评估器、前向兼容动态发现器、防篡改 SHA-256 校验器、双语 Markdown 渲染器与 CLI 入口
2. [`outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py) — 导出 Phase 324 `P324_*` / `MILESTONE324_*` / `STATUS_MILESTONE324_*` 等非遮蔽公共符号（完整保留历史里程碑及 Ph186..Ph321 导出）
3. [`outputs/fx6-on-fx3-closure/fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py) — 注册并分派 `verify-milestone-324` CLI 子命令
4. [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md) — 补充第 56 节 Grand Milestone Phase 324 `verify-milestone-324` 模块与 CLI 说明
5. [`outputs/fx6-on-fx3-closure/tests/test_realhw_milestone324_master_gate.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_milestone324_master_gate.py) — 84 项双模单元测试（覆盖常量与动态发现、`>=` 前向兼容、14/14 预检、38+/114+/76+ QEMU 与 PNG、跨支柱红线、无供体 Linux CI、CLI 与防篡改验证器）
6. [`Makefile`](../../Makefile) — 新增双模 `verify-milestone-324` 目标并接入 `.PHONY` 与 `verify-fast`
7. [`.github/workflows/clean-room-ci.yml`](../../.github/workflows/clean-room-ci.yml) — 紧随 134-gate / 54-pillar / 311 新增 `verify-142-gates`、`verify-56pillar-recovery` 与 `verify-milestone-324 --force-clean-room` Clean-Room CI 门禁
8. [`reports/2026-11-17-milestone-phase324-142gate-56pillar-45auditor-66stage-14preflight-round65-master/README.md`](./README.md) — 本工程闭环报告

---

## 四、实测验证命令与结果记录

| 验证项目 | 命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 324 单测（`LOCAL_DONOR_O_RDONLY`） | `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_realhw_milestone324_master_gate.py -v` | **84/84 OK**（`20.288s`） |
| Phase 324 单测（`FX3_CLEAN_ROOM_TEST=1`） | `FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_realhw_milestone324_master_gate.py -v` | **84/84 OK**（`19.823s`） |
| Phase 324 单测（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_realhw_milestone324_master_gate.py -v` | **84/84 OK**（`15.763s`） |
| 双模 Master Gate（324 + 311） | `make verify-milestone-324 && FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-324 && make verify-milestone-311` | **PASS**（324 双模 `6/6`；311 双模 `6/6`） |
| 上游 CI 命令复验 | `fx3_safety verify-142-gates --force-clean-room --simulate-bench-dry-run` + `fx3_recovery verify-56pillar-recovery --clean-room` | **PASS**（`142/142` & `56/56` `0.809s`） |
| Phase 311 回归单测（Clean-Room） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_realhw_milestone311_master_gate.py` | **78/78 OK**（`14.214s`） |
| 仓库卫生与 Clean-Room 审计 | `make clean-audit` | **ALL GREEN**（`0.05s`） |
