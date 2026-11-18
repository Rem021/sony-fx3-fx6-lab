# Grand Milestone Phase 311 实机主线 6 支柱总闸门（`>=134-Gate` · `>=54-Pillar` · `45/45 Auditor` · `>=62-Stage` · `12/12 Bench Preflights (Ph186..Ph307)` · `>=35 QEMU Rounds / >=105 Runs / >=70 PNGs`）闭环报告

## 一、核心结论（结论先行）

1. **Grand Milestone Phase 311 总闸门（`schema = "realhw_milestone311_master_gate_v1"` / `make verify-milestone-311`）已完成端到端闭环并通过三态全量实测验证**：
   - 严格在 8 个受控归属文件内交付 [`realhw_milestone311_master_gate.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone311_master_gate.py)、公共符号非遮蔽导出 [`__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py)、CLI 子命令 `verify-milestone-311`（[`__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py)，支持 `--repo-root` / `--clean-room` / `--force-clean-room` / `--simulate-bench-dry-run` / `--simulate-ready-bench` / `--json` / `--out` / `--output` / `--markdown-out`）、模块文档 [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md)（第 53 节）、双模单元测试 [`test_realhw_milestone311_master_gate.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_milestone311_master_gate.py)（78 项测试，全部采用 `sys.executable`、Python 3.14 `%%` 转义安全、`GITHUB_ACTIONS == 'true'` `+15.0s` 宽裕耗时预算与 `assertGreaterEqual` 前向兼容断言）、顶层 [`Makefile`](../../Makefile) 目标 `verify-milestone-311`（接入 `verify-fast`，完整保留 `verify-milestone-295/264/254`）及 [`.github/workflows/clean-room-ci.yml`](../../.github/workflows/clean-room-ci.yml)（新增 `verify-134-gates`、`verify-54pillar-recovery` 与 `verify-milestone-311`）。
   - 将 **Waves 21–57+（Phases 134–310）** 全部 6 大实机主线支柱与 **Rounds 28–62（`35/35` 轮实机内核 QEMU、`105/105` 子运行、`70/70` 脱敏 PNG 收据）** 收敛为带防篡改 `milestone311_sha256` 的单张确定性主证书：
     - **`LOCAL_DONOR_O_RDONLY` 模式**：`6/6` 支柱全绿（`gate134=131/134` 离线 / `134/134` 模拟干跑、`recovery=54/54`、`cnflasha_ro=True`、`auditors=45/45`、`vm_stages=62/62`、`Ph186..Ph307` 全部 `12/12` 双态合规、`H0==H3=16/16`、`e_nd_tx=0`、`rf_pkts=0`、`qemu=35/35(105/105)`、`pngs=70/70(max=27467B)`、`milestone311_sha256=2c8aa3a5a714d9a4...`）；
     - **`CLEAN_ROOM_SYNTHETIC` 模式（`FX3_FX6_FORCE_CLEAN_ROOM=1`）**：零索尼专有固件依赖，`6/6` 支柱全绿并通过确定性 SHA-256 校验（`milestone311_sha256=d44a391037643957...`）。
2. **前向兼容（`>=` 下界 + 动态自动发现）与历史向后兼容双保证**：
   - `P1`（动态发现 `fx3_safety` 最高 `evaluate_<N>gate_preflight`，`N >= 134`，兼容 `136, 138...`，且修复了 `G133+` 无下划线门号与 dataclass `g<K>_result` 属性递归提取）、`P2`（动态发现 `fx3_recovery` 最高 `evaluate_realhw_<M>pillar_recovery_master`，`M >= 54`，兼容 `55, 56...`，单测对 `pillar54_a_*` / `pillar54_b_*` 均采用 `rec.setdefault(sub_key, {})["passed"] = False`）、`P3`（`>= 45` 审计器 + 动态发现 `46th+`）、`P4`（`>= 62` VM HIL 阶段 + 动态发现 `Stage 63+`）、`P6`（`>= 35` 轮 / `>= 105` 运行 / `>= 70` PNG 收据 + 动态发现 `Round 63+`）。
   - 历史 `verify-milestone-295/264/254/233/221/209/193/175/147/130/110/90` 100% 完整无回归；`outputs/fx6-on-fx3-closure/tests` 全量 2,095 项测试在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下全部通过（`2,095 tests in 257.650s — OK, skipped=51`）。
3. **严格区分实测事实与未执行物理实机边界（Facts vs Physical Bench Boundary）**：
   - **已闭环实测事实**：78 项三态 Phase 311 单元测试在 `LOCAL_DONOR_O_RDONLY`（`19.782s`）、`FX3_CLEAN_ROOM_TEST=1`（`19.365s`）、`FX3_FX6_FORCE_CLEAN_ROOM=1`（`13.979s`）三态全部 `78/78 OK`；`make verify-milestone-311`、`make verify-milestone-295`、`fx3_safety verify-134-gates`（`134/134`）、`fx3_recovery verify-54pillar-recovery`（`54/54`）、`scripts/run_all_lab_tests.py --clean-only` 与 `make clean-audit` 全部通过。
   - **未执行物理实机边界**：**真实物理 Sony ILME-FX3 相机上电 USB 连接、Tier-0 实机冷备签收与现场插卡/烧录尚未执行**；全链路物理安全红线硬锁定为拒绝（`overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`cnflasha_userspace_write_blocked = True`、`persistent_emmc_writes_authorized = False`、`cross_model_flash_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`、`otp_fuse_touches = 0`、`rpmb_counter_increments = 0`、`passive_tx_bytes_emitted = 0`）。

---

## 二、六大实机支柱验收矩阵（`realhw_milestone311_master_gate_v1`）

| 支柱 ID | 支柱名称 | 验收契约与前向兼容机制 | 实测结果（Local Donor / Clean-Room） |
| :--- | :--- | :--- | :--- |
| **`P1`** | `SAFETY_134PLUS_GATE_REALHW_MASTER_PREFLIGHT` | 动态发现最高 `fx3_safety.evaluate_<N>gate_preflight`（`N >= 134`，兼容 `136+`）：离线 `== N - 3`（`131/134`，`G10..G12` fail-closed），`--simulate-bench-dry-run` `N/N`（`134/134`），逐项校验 `G63..G134+`（覆盖 Waves 42–57+），硬锁 `ready_attach=False`、`emmc_writes_auth=False`、`cross_model_flash_auth=False`、`usb_tx=0`、`leaked=0` | `offline=131/134` · `simulated=134/134` · `cross_model_flash=False` · `usb_tx=0` · **PASS** |
| **`P2`** | `FIFTY_FOUR_PLUS_PILLAR_RECOVERY_MASTER_VAULT` | 动态发现最高 `fx3_recovery.evaluate_realhw_<M>pillar_recovery_master`（`M >= 54`，兼容 `55+`）：`M/M` 全绿（`all_passed=True`），`cnflasha_userspace_write_blocked=True`、`otp=0`、`rpmb=0`、`passive_tx=0`、`usb_pkts=0`、`leaked=0` | `54/54` (`cnflasha_ro=True`) · `otp=0, rpmb=0, passive_tx=0, usb_pkts=0` · **PASS** |
| **`P3`** | `FORTY_FIVE_PLUS_FIRMWARE_LAB_REALBIN_AUDITORS` | 校验全部 `45/45` 项 `fx3_firmware_lab` 实机只读审计器并动态发现 `46th+ realhw_*_auditor.py`，锁定 `raw_firmware_bytes_leaked=0`、`e_nd_actuator_tx_count=0`、`calibration_mutation_bytes=0` | `45/45` · `e_nd_tx=0` · `cal_mut=0B` · `leaked=0B` · **PASS** |
| **`P4`** | `SIXTY_TWO_PLUS_STAGE_VM_HIL_COEMULATION` | 运行 `fx3_vm_coemulation_suite` 启用 Stages `1..62+`（涵盖 Stage 59..62 Wave-52 并自动发现 `Stage 63+`），锁定 `vm_stages_passed >= 62`、`raw_firmware_bytes_leaked=0`、`physical_device_writes=0`、`emmc_corruptions=0` | `62/62` · `phys_writes=0` · `emmc_corruptions=0` · `leaked=0B` · **PASS** |
| **`P5`** | `DODECUPLE_BENCH_READINESS_PREFLIGHTS_PH186_TO_PH307` | 校验 `Phase 136/143/154` 及全套 `12/12` 物理台架预检器（`Ph186`、`Ph204`、`Ph216`、`Ph227`、`Ph248`、`Ph261`、`Ph275`、`Ph279`、`Ph284`、`Ph291`、`Ph302`、`Ph307`）：离线均为 `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT`，模拟干跑均为 `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH`，`16/16 H0==H3`，`e_nd_tx=0`，`p307_wireless_rf_packets_emitted=0`，`p307_slot1_data_sector_writes=0` | `12/12` (`Ph186..Ph307`) · `H0==H3=16/16` · `rf_pkts=0` · `ready_attach=False` · **PASS** |
| **`P6`** | `REAL_FX3_702_QEMU_ROUNDS_28_TO_62_PLUS_AND_PNG_RECEIPTS` | 校验 `ILME-FX3 Ver. 7.02` (`4.9.337-scel+`) ARM64 QEMU 实机内核演练 `Rounds 28..62+`（`>= 35` 轮、`>= 105` 子运行、`>= 70` 脱敏 PNG 收据且每张 `< 51,200 B`，动态发现 `Round 63+`），`16/16 H0==H3`、`emmc=0`、`nop=0`、`crashes=0`、`leaked=0` | `35/35` 轮 (`105/105` runs) · `70/70` PNG (`max=27,467 B`) · `emmc=0, leaked=0` · **PASS** |

---

## 三、严格 8 文件交付清单

1. [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone311_master_gate.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone311_master_gate.py) — Phase 311 6 支柱并行主闸门评估器、前向兼容动态发现器、防篡改 SHA-256 校验器、双语 Markdown 渲染器与 CLI 入口
2. [`outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py) — 导出 Phase 311 `P311_*` / `MILESTONE311_*` / `STATUS_MILESTONE311_*` 等非遮蔽公共符号（完整保留 Ph186..Ph307 导出）
3. [`outputs/fx6-on-fx3-closure/fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py) — 注册并分派 `verify-milestone-311` CLI 子命令（支持 `--simulate-bench-dry-run` 等全套选项）
4. [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md) — 补充第 53 节 Grand Milestone Phase 311 `verify-milestone-311` 模块与 CLI 说明
5. [`outputs/fx6-on-fx3-closure/tests/test_realhw_milestone311_master_gate.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_milestone311_master_gate.py) — 78 项三态单元测试（`sys.executable`、`GITHUB_ACTIONS` +15s 耗时预算、`rec.setdefault(...)` 安全子键注入、`assertGreaterEqual` 前向兼容阈值）
6. [`Makefile`](../../Makefile) — 新增双模 `verify-milestone-311` 目标并接入 `.PHONY` 与 `verify-fast`
7. [`.github/workflows/clean-room-ci.yml`](../../.github/workflows/clean-room-ci.yml) — 紧随 124-gate / 50-pillar / 295 新增 `verify-134-gates`、`verify-54pillar-recovery` 与 `verify-milestone-311` Clean-Room CI 门禁
8. [`reports/2026-11-17-milestone-phase311-134gate-54pillar-45auditor-62stage-12preflight-round62-master/README.md`](./README.md) — 本工程闭环报告

---

## 四、实测验证命令与结果记录

| 验证项目 | 命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 311 单测（`LOCAL_DONOR_O_RDONLY`） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure:outputs/fx6-on-fx3-closure/tests" /usr/bin/python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_realhw_milestone311_master_gate.py` | **78/78 OK**（`19.782s`） |
| Phase 311 单测（`FX3_CLEAN_ROOM_TEST=1`） | `FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=... /usr/bin/python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_realhw_milestone311_master_gate.py` | **78/78 OK**（`19.365s`） |
| Phase 311 单测（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=... /usr/bin/python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_realhw_milestone311_master_gate.py` | **78/78 OK**（`13.979s`） |
| 双模 Master Gate（311 + 295） | `make verify-milestone-311 && make verify-milestone-295` | **PASS**（311 双模 `6/6`；295 双模 `6/6`） |
| 上游 CI 命令复验 | `fx3_safety verify-134-gates --force-clean-room --simulate-bench-dry-run` + `fx3_recovery verify-54pillar-recovery --clean-room` | **PASS**（`134/134` & `54/54`） |
| Closure 全量发现（Clean-Room） | `FX3_FX6_FORCE_CLEAN_ROOM=1 ... unittest discover -s outputs/fx6-on-fx3-closure/tests` | **2,095 tests OK**（`skipped=51`，`257.650s`） |
| Closure 全量发现（Local Donor） | `... unittest discover -s outputs/fx6-on-fx3-closure/tests` + `test_phase110_milestone_master_gate.py` | **2,094/2,095**（仅 Ph110 `<2.5s` 耗时抖动 `2.818s`，复跑 Ph110 `40/40 OK` `4.411s`） |
| 仓库卫生与 Clean-Room 审计 | `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only && make clean-audit` | **ALL GREEN**（`0.05s` & `0.04s`） |
