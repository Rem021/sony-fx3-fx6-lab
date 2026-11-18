# Grand Milestone Phase 349 实机主线 6 支柱总闸门（`>=148-Gate` · `>=62-Pillar` · `>=45-Auditor` · `>=75-Stage` · `20/20 Bench Preflights (Ph186..Ph345)` · `>=45 QEMU Rounds / >=135 Runs / >=90 PNGs`）闭环报告

## 一、核心结论（结论先行）

1. **Grand Milestone Phase 349 总闸门（`schema = "realhw_milestone349_master_gate_v1"` / `python3 -B -m fx6_closure verify-milestone-349`）已完成端到端闭环并通过四态全量实测验证**：
   - 严格在指定的 **6 个归属文件**内完成交付（未修改根 `Makefile`、`.github/workflows/*` 或任何跨包文件）：[`realhw_milestone349_master_gate.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone349_master_gate.py)、[`__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py)、[`__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py)、[`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md)（第 63 节）、[`test_realhw_milestone349_master_gate.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_milestone349_master_gate.py)（`92` 项四态单元测试）及本闭环报告。
   - 将 **Waves 21–72（Phases 134–348）** 全部 6 大实机主线支柱与 **Rounds 28–72（`45/45` 轮实机内核 QEMU、`135/135` 子运行、`90/90` 脱敏 PNG 收据，`max=27,467 B`）** 收敛为带防篡改 `milestone349_sha256` 的单张主证书：
     - **`LOCAL_DONOR_O_RDONLY` 模式**：`6/6` 支柱全绿（`status=MILESTONE_349_PREBENCH_MASTER_VERIFIED`，`gate148=145/148` 离线 / `148/148` 模拟干跑、`recovery=62/62`、`cnflasha_ro=True`、`auditors=45/45`、`vm_stages=75/75`、`Ph186..Ph345` 全部 `20/20` 双态合规、`H0==H3=16/16`、`e_nd_tx=0`、`rf_pkts=0`、`slot1_writes=0`、`qemu=45/45(135/135)`、`pngs=90/90(max=27467B)`）。
     - **`CLEAN_ROOM_SYNTHETIC` 模式（`FX3_FX6_FORCE_CLEAN_ROOM=1` / `FX3_CLEAN_ROOM_TEST=1` / `work_root=None` / 无 `Mac/` 无供体 CI 环境）**：零索尼专有固件依赖，`6/6` 支柱全绿并通过 `verify_realhw_milestone349_master_gate` 防篡改校验。
2. **前向兼容（`>=` 下界 + 动态自动发现）与历史向后兼容双保证**：
   - 依据当前 HEAD 实态设定前向兼容下界（`>=148` 安全闸门、`>=62` 恢复支柱、`>=45` 固件实验室审计器、`>=75` VM HIL 阶段、`20/20` 物理台架预检 `Ph186..Ph345`、`>=45` QEMU 轮次 / `>=135` 子运行 / `>=90` PNG 收据 `< 51,200 B`），同时自动动态发现并发主线合入后的 **`150+` Gates（`H432`）**、**`63+` Recovery Pillars（`H434`）**、**`46th+` 审计器**、**`Stage 76+`（`H430`）** 与 **`Round 73+`（`H431`）**，已在单元测试中分别构造模拟前向扩展夹具实测验证通过。
   - 历史向后兼容 `make verify-milestone-324`（双模）与 `test_realhw_milestone324_master_gate.py`（`84/84 OK`）全部保持绿灯通过。
3. **严格区分实测事实与未执行物理真机边界 / 推断**：
   - **实测事实（Verified Facts）**：
     - `test_realhw_milestone349_master_gate.py` 在 `LOCAL_DONOR_O_RDONLY`（含 `work_root=None` 与无 `Mac/` 无供体测试：`92/92 OK` / `25.259s`）、`FX3_CLEAN_ROOM_TEST=1`（`92/92 OK` / `22.977s`）与 `FX3_FX6_FORCE_CLEAN_ROOM=1`（`92/92 OK` / `21.401s`）三组进程全量通过。
     - CLI `verify-milestone-349 --json` 连续两次实测在 `LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1 --force-clean-room` 均返回 `rc=0`、`status=MILESTONE_349_PREBENCH_MASTER_VERIFIED`、`6/6 PASS`、`verify_realhw_milestone349_master_gate(...).valid == True`，且 `compute_milestone349_sha256(payload) == payload["milestone349_sha256"]`。固定输入下 SHA-256 完全确定性一致；连续两次独立 CLI 进程运行后递归剥离 `elapsed_seconds` 对比，`P1`/`P2`/`P3`/`P5`/`P6` 全部字段与 `P4` 全部计数器/状态完全一致，仅上游 `fx3_vm_coemulation_suite` 在返回前将运行耗时混入自身计算的 `P4.audit_digest_sha256` 与部分 `P4.stage*_digest_sha256` 摘要导致 `milestone349_sha256` 在不同次实跑间随运行耗时波动（与 Milestone 324 实测特征一致）。
     - `make verify-milestone-324` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-324` 双模均返回 `status=OK`、`6/6 PASS`（并前向自适应当前 HEAD 的 `145/148`、`62/62`、`75/75`、`45/45`）；`test_realhw_milestone324_master_gate.py` `84/84 OK`（`24.252s`）；`make clean-audit` 返回 `ALL GREEN in 0.05s` 且无 `.pyc` / `__pycache__`。
   - **未执行物理真机边界 / 推断边界（Not Executed Physically / Boundary）**：
     - **真实物理 Sony ILME-FX3 相机上电 USB 连接、Tier-0 物理实机冷备签收及现场插卡/烧录均尚未执行（也未对真机产生任何写入）**；`--simulate-bench-dry-run` 仅代表离线台架预演，不等价于物理真机授权。全链路物理安全红线硬锁定为拒绝（`overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`cnflasha_userspace_write_blocked = True`、`persistent_emmc_writes_authorized = False`、`cross_model_flash_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`、`e_nd_actuator_tx_count = 0`、`rf_packets_transmitted = 0`、`slot1_data_sector_writes = 0`、`otp_fuse_touches = 0`、`rpmb_counter_increments = 0`、`passive_tx_bytes_emitted = 0`）。

---

## 二、六大实机支柱验收矩阵（`realhw_milestone349_master_gate_v1`）

| 支柱 ID | 支柱名称 | 验收契约与前向兼容机制 | 实测结果（Local Donor / Clean-Room） |
| :--- | :--- | :--- | :--- |
| **`P1`** | `SAFETY_148PLUS_GATE_REALHW_MASTER_PREFLIGHT` | 动态发现最高 `fx3_safety.evaluate_<N>gate_preflight`（`N >= 148`，自动发现 `150/152/...`）：离线 `== N - 3`（`145/148`，`G10..G12` fail-closed），`--simulate-bench-dry-run` `N/N`（`148/148`），逐项校验 `G63..G148+`（含 Waves 62–65 呼吸效应/`File Settings` SDHC/版权 46 字符重置勘误/NTSC-PAL/2 项节能），硬锁 `ready_attach=False`、`emmc_writes_auth=False`、`cross_model_flash_auth=False`、`usb_tx=0`、`leaked=0` | `offline=145/148` · `simulated=148/148` · `cross_model_flash=False` · `usb_tx=0` · **PASS** |
| **`P2`** | `SIXTY_TWO_PLUS_PILLAR_RECOVERY_MASTER_VAULT` | 动态发现最高 `fx3_recovery.evaluate_realhw_<M>pillar_recovery_master`（`M >= 62`，自动发现 `63/64/...`）：`M/M` 全绿（`all_passed=True`），校验 `pillar62_*` 及 `P57..P62` 零越界计数器、`cnflasha_userspace_write_blocked=True`、`otp_fuse_touches=0`、`rpmb_counter_increments=0`、`passive_tx=0`、`usb_pkts=0`、`leaked=0` | `62/62` (`cnflasha_ro=True`) · `otp=0, rpmb=0, passive_tx=0, usb_pkts=0` · **PASS** |
| **`P3`** | `FORTY_FIVE_PLUS_FIRMWARE_LAB_REALBIN_AUDITORS` | 校验全部 `45/45` 项 `fx3_firmware_lab` 实机只读审计器并动态发现 `46th+ realhw_*_auditor.py`，锁定 `raw_firmware_bytes_leaked=0`、`e_nd_actuator_tx_count=0`、`calibration_mutation_bytes=0`、`wbi_mutation_bytes=0` | `45/45` · `e_nd_tx=0` · `cal_mut=0B` · `leaked=0B` · **PASS** |
| **`P4`** | `SEVENTY_FIVE_PLUS_STAGE_VM_HIL_COEMULATION` | 运行 `fx3_vm_coemulation_suite` 启用 Stages `1..75+`（涵盖 Stages `67..75` Wave-65 全量红线及自动发现 `Stage 76+`），锁定 `vm_stages_passed >= 75`、`raw_firmware_bytes_leaked=0`、`physical_device_writes=0`、`emmc_corruptions=0`、`slot1_avf_info_mutated=False`、`wf12_00342260_hits=0` | `75/75` · `phys_writes=0` · `emmc_corruptions=0` · `leaked=0B` · **PASS** |
| **`P5`** | `ICOSUPLE_20_BENCH_READINESS_PREFLIGHTS_PH186_TO_PH345` | 校验 `Phase 136/143/154` 及全部 **`20/20` 物理台架预检器**（`Ph186..Ph321` + 新增 `Ph326/P329`、`Ph334`、`Ph338`、`Ph341`、`Ph342`、`Ph345`）：离线均为 `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT`，干跑均为 `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH`，`overall_ready_for_hardware_attach=False`、`16/16 H0==H3`、`e_nd_actuator_tx_count=0`、`rf_packets_transmitted=0`、`usb_packets_transmitted=0`、`slot1_data_sector_writes=0`、`raw_firmware_bytes_leaked=0` | `20/20` (`Ph186..Ph345`) · `H0==H3=16/16` · `rf_pkts=0` · `slot1_writes=0` · `ready_attach=False` · **PASS** |
| **`P6`** | `REAL_FX3_702_QEMU_ROUNDS_28_TO_72_PLUS_AND_PNG_RECEIPTS` | 校验 `ILME-FX3 Ver. 7.02` (`4.9.337-scel+`) ARM64 QEMU 实机内核演练 `Rounds 28..72+`（`>=45` 轮、`>=135` 子运行、`>=90` 脱敏 PNG 收据且每张 `<= 27,467 B` / `< 51,200 B`，动态发现 `Round 73+`），跨支柱强制 `16/16 H0==H3`、`emmc_write_count=0`、`nop=0`、`crashes=0`、`raw_firmware_bytes_leaked=0` | `45/45` 轮 (`135/135` runs) · `90/90` PNG (`max=27,467 B`) · `emmc=0, leaked=0` · **PASS** |

---

## 三、严格 6 文件交付清单

1. [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone349_master_gate.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone349_master_gate.py) — Grand Milestone Phase 349 6 支柱 `ProcessPoolExecutor` 并行总闸门、动态前向发现器（`>=148` Gate / `>=62` Pillar / `>=45` Auditor / `>=75` Stage / `Round 73+`）、`20/20` 台架预检验证器、防篡改 SHA-256 校验器、双语 Markdown 渲染器与 CLI 入口
2. [`outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py) — 非遮蔽导出 `P349_*` / `MILESTONE349_*` / `STATUS_MILESTONE349_*` / `RealHwMilestone349MasterGateReport` / `evaluate_realhw_milestone349_master_gate` / `verify_realhw_milestone349_master_gate` 等公共符号（完整保留历史里程碑及 `Ph186..Ph345` 导出）
3. [`outputs/fx6-on-fx3-closure/fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py) — 注册并分派 `verify-milestone-349` CLI 子命令（支持 `--repo-root`、`--fx6-lib-dir`、`--fx3-modules-dir`、`--clean-room` / `--force-clean-room`、`--simulate-bench-dry-run` / `--simulate-ready-bench`、`--json`、`--out` / `--output`、`--markdown-out`，所有 `help=` 中的百分号均安全规避/转义）
4. [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md) — 追加第 63 节 Grand Milestone Phase 349 `verify-milestone-349` 文档与测试命令
5. [`outputs/fx6-on-fx3-closure/tests/test_realhw_milestone349_master_gate.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_milestone349_master_gate.py) — 92 项四态单元测试（覆盖常量导出、`>=` 前向兼容动态发现、`20/20` 预检、Stage 76+、Round 73+、PNG `< 50 KiB`、跨支柱红线、`work_root=None` / 无 `Mac/` 无供体 CI、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1`、CLI 与防篡改验证器）
6. [`reports/2026-11-18-grand-milestone-phase349-150gate-63pillar-45auditor-76stage-20preflight-round72plus-master/README.md`](./README.md) — 本工程闭环报告

---

## 四、实测验证命令与结果记录

| 验证项目 | 命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 349 单测（Normal `LOCAL_DONOR_O_RDONLY` + `work_root=None` + 无供体 CI） | `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest -v outputs/fx6-on-fx3-closure/tests/test_realhw_milestone349_master_gate.py` | **92/92 OK**（`25.259s`） |
| Phase 349 单测（`FX3_CLEAN_ROOM_TEST=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_CLEAN_ROOM_TEST=1 /usr/bin/python3 -B -m unittest -v outputs/fx6-on-fx3-closure/tests/test_realhw_milestone349_master_gate.py` | **92/92 OK**（`22.977s`） |
| Phase 349 单测（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B -m unittest -v outputs/fx6-on-fx3-closure/tests/test_realhw_milestone349_master_gate.py` | **92/92 OK**（`21.401s`） |
| CLI 双模执行与 SHA-256 校验（Normal 连续 2 次） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" /usr/bin/python3 -B -m fx6_closure verify-milestone-349 --json` | **PASS**（`6/6`, `valid=True`, `recompute_match=True`, 145/148 · 62/62 · 45/45 · 75/75 · 20/20 · 45/45(135/135) · 90/90 PNG `max=27467B`） |
| CLI 双模执行与 SHA-256 校验（Clean-Room 连续 2 次） | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure" /usr/bin/python3 -B -m fx6_closure verify-milestone-349 --force-clean-room --json` | **PASS**（`6/6`, `valid=True`, `recompute_match=True`, 除上游 VM 计时摘要外全字段一致） |
| Phase 324 向后兼容（双模 `make` + 单测） | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-324 && PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-324` + `test_realhw_milestone324_master_gate.py` | **PASS**（双模 `6/6`，单测 **84/84 OK** `24.252s`） |
| 仓库卫生与 Clean-Room 审计 | `make clean-audit` | **ALL GREEN**（`0.05s`，零 `.pyc`） |
