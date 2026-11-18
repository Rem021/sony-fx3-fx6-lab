# Grand Milestone Phase 295 实机主线 6 支柱总闸门（`124+-Gate` · `50+-Pillar` · `45+ Auditor` · `58+ Stage` · `10/10 Bench Preflights (Ph186..Ph291)` · `Rounds 28–58+`）闭环报告

## 一、核心结论（结论先行）

1. **Grand Milestone Phase 295 总闸门（`schema = "realhw_milestone295_master_gate_v1"` / `make verify-milestone-295`）已完成端到端闭环并通过双模/三态全量验证**：
   - 交付 [`realhw_milestone295_master_gate.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone295_master_gate.py)、公共符号导出 [`__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py)（`P295_*` / `MILESTONE295_*` 非遮蔽导出）、CLI 子命令 `verify-milestone-295`（[`__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py)，支持 `--repo-root` / `--clean-room` / `--force-clean-room` / `--json` / `--out` / `--output` / `--markdown-out`）、模块文档 [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md)、顶层 [`Makefile`](../../Makefile) 目标 `verify-milestone-295`（接入 `verify-fast`）与 [`.github/workflows/clean-room-ci.yml`](../../.github/workflows/clean-room-ci.yml)（并行保留原有 `108-gates` / `45pillar` / `264` 校验并新增 `verify-124-gates`、`verify-50pillar-recovery`、`verify-milestone-295`）。
   - 将 **Waves 21–52+（Phases 134–294）** 全部 6 大实机支柱与 **Rounds 28–58（`31/31` 轮实机内核 QEMU、`93/93` 子运行、`62/62` 脱敏 PNG 收据）** 收敛为带防篡改 `milestone295_sha256` 的单张确定性主证书：
     - **`LOCAL_DONOR_O_RDONLY` 模式**：`6/6` 支柱全绿（`pillars=6/6`、`gate124=121/124` 离线 / `124/124` 模拟干跑、`recovery=50/50`、`cnflasha_ro=True`、`auditors=45/45`、`vm_stages=58/58`、`Ph186/204/216/227/248/261/275/279/284/291` 全部 `10/10` 双态合规、`H0==H3=16/16`、`e_nd_tx=0`、`qemu=31/31(93/93)`、`pngs=62/62(max=27467B)`、`milestone295_sha256=fb239ebf5bcea61f...`）；
     - **`CLEAN_ROOM_SYNTHETIC` 模式（`FX3_FX6_FORCE_CLEAN_ROOM=1`）**：零索尼专有固件依赖，`6/6` 支柱全绿并通过确定性 SHA-256 校验（`milestone295_sha256=ec0da60e2a356bab...`）。
2. **前向兼容（`>=` 下界 + 动态发现）与历史向后兼容双保证**：
   - `P1`（动态发现 `fx3_safety` 最高 `evaluate_<N>gate_preflight`，`N >= 124`，兼容 `126+`）、`P2`（动态发现 `fx3_recovery` 最高 `evaluate_realhw_<M>pillar_recovery_master`，`M >= 50`，兼容 `51+`）、`P3`（`>= 45` 审计器 + 动态发现 `46th+ realhw_*_auditor.py`）、`P4`（`>= 58` VM HIL 阶段 + 动态发现 `Stage 59+`）、`P6`（`>= 31` 轮 / `>= 93` 运行 / `>= 62` PNG 收据 + 动态发现 `Round 59+`）统一采用 `>=` 契约，避免后续 Phase 合并破坏 `verify-milestone-295`。
   - 历史 `verify-milestone-90..264`、`verify-108-gates`、`verify-45pillar-recovery` 保持 100% 完整无回归；`outputs/fx6-on-fx3-closure/tests` 在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 模式下全量 `1,847` 项单元测试通过（`OK, skipped=51`，耗时 `204.524s`）。
3. **严格区分实测事实与未执行物理实机边界（Facts vs Physical Bench Boundary）**：
   - **已闭环实测事实**：`76` 项双模 Phase 295 单元测试（[`test_realhw_milestone295_master_gate.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_milestone295_master_gate.py)）在 `LOCAL_DONOR_O_RDONLY`（`10.142s`）、`FX3_CLEAN_ROOM_TEST=1`（`10.251s`）、`FX3_FX6_FORCE_CLEAN_ROOM=1`（`6.199s`）三态全部 `76/76 OK`；`make verify-milestone-295`、`make verify-milestone-264`、CI `verify-124-gates`（`124/124`）、`verify-50pillar-recovery`（`50/50`）、`scripts/run_all_lab_tests.py --clean-only` 及 `make clean-audit` 全部通过。
   - **未执行物理实机边界**：**真实物理 Sony ILME-FX3 相机上电 USB 连接、Tier-0 实机冷备签收与现场插卡/烧录尚未执行**；全链路物理安全红线硬锁定为拒绝（`overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`cnflasha_userspace_write_blocked = True`、`persistent_emmc_writes_authorized = False`、`cross_model_flash_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`、`otp_fuse_touches = 0`、`rpmb_counter_increments = 0`、`passive_tx_bytes_emitted = 0`）。

---

## 二、六大实机支柱验收矩阵（`realhw_milestone295_master_gate_v1`）

| 支柱 ID | 支柱名称 | 验收契约与前向兼容机制 | 实测结果（Local Donor / Clean-Room） |
| :--- | :--- | :--- | :--- |
| **`P1`** | `SAFETY_124PLUS_GATE_REALHW_MASTER_PREFLIGHT` | 动态发现最高 `fx3_safety.evaluate_<N>gate_preflight`（`N >= 124`，兼容 `126+`）：离线 `>= N - 3`（`121/124`，`G10..G12` fail-closed），`--simulate-bench-dry-run` `N/N`（`124/124`），逐项校验 `G63..G124+`（覆盖 Waves 42–52+），硬锁 `overall_ready_for_hardware_attach=False`、`persistent_emmc_writes_authorized=False`、`cross_model_flash_authorized=False`、`usb_packets_transmitted=0`、`raw_firmware_bytes_leaked=0` | `offline=121/124` · `simulated=124/124` · `cross_model_flash=False` · `usb_tx=0` · **PASS** |
| **`P2`** | `FIFTY_PLUS_PILLAR_RECOVERY_MASTER_VAULT` | 动态发现最高 `fx3_recovery.evaluate_realhw_<M>pillar_recovery_master`（`M >= 50`，兼容 `51+`）：`M/M` 全绿（`all_passed=True`），`cnflasha_userspace_write_blocked=True`、`otp_fuse_touches=0`、`rpmb_counter_increments=0`、`passive_tx_bytes_emitted=0`、`physical_usb_packets_emitted=0`、`raw_firmware_bytes_leaked=0` | `50/50` (`cnflasha_ro=True`) · `otp=0, rpmb=0, passive_tx=0, usb_pkts=0` · **PASS** |
| **`P3`** | `FORTY_FIVE_PLUS_FIRMWARE_LAB_REALBIN_AUDITORS` | 校验全部 `>= 45` 项 `fx3_firmware_lab` 实机只读审计器并动态发现 `46th+ realhw_*_auditor.py`，锁定 `raw_firmware_bytes_leaked=0`、`e_nd_actuator_tx_count=0`、`calibration_mutation_bytes=0` | `45/45` · `e_nd_tx=0` · `cal_mut=0B` · `leaked=0B` · **PASS** |
| **`P4`** | `FIFTY_EIGHT_PLUS_STAGE_VM_HIL_COEMULATION` | 运行 `fx3_vm_coemulation_suite` 启用 Stages `1..58+`（涵盖至 Stage 58 Wave-48 并自动发现 `Stage 59+`），锁定 `vm_stages_passed >= 58`、`raw_firmware_bytes_leaked=0`、`physical_device_writes=0`、`emmc_corruptions=0` | `58/58` · `phys_writes=0` · `emmc_corruptions=0` · `leaked=0B` · **PASS** |
| **`P5`** | `DECUPLE_BENCH_READINESS_PREFLIGHTS_PH186_TO_PH291` | 校验 `Phase 136/143/154` 及全套 `10/10` 物理台架预检器（`Ph186`、`Ph204`、`Ph216`、`Ph227`、`Ph248`、`Ph261`、`Ph275`、`Ph279`、`Ph284`、`Ph291`）：离线均为 `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT`，模拟干跑均为 `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH`，`16/16 H0==H3`，`overall_ready_for_hardware_attach=False`，`raw_firmware_bytes_leaked=0` | `10/10` (`Ph186..Ph291`) · `H0==H3=16/16` · `ready_attach=False` · **PASS** |
| **`P6`** | `REAL_FX3_702_QEMU_ROUNDS_28_TO_58_PLUS_AND_PNG_RECEIPTS` | 校验 `ILME-FX3 Ver. 7.02` (`4.9.337-scel+`) ARM64 QEMU 实机内核演练 `Rounds 28..58+`（`>= 31` 轮、`>= 93` 子运行、`>= 62` 脱敏 PNG 收据且每张 `< 51,200 B`，动态发现 `Round 59+`），`16/16 H0==H3`、`emmc_write_count=0`、`raw_firmware_bytes_leaked=0` | `31/31` 轮 (`93/93` runs) · `62/62` PNG (`max=27,467 B`) · `emmc=0, leaked=0` · **PASS** |

---

## 三、严格 8 文件交付清单

1. [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone295_master_gate.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone295_master_gate.py) — Phase 295 6 支柱并行主闸门评估器、动态前向发现器、防篡改 SHA-256 校验器、双语 Markdown 渲染器与 CLI 辅助入口
2. [`outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py) — 导出 Phase 295 `P295_*` / `MILESTONE295_*` / `STATUS_MILESTONE295_*` / `CROSS_MODEL_FLASH_AUTHORIZED` 等非遮蔽公共符号
3. [`outputs/fx6-on-fx3-closure/fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py) — 注册并分派 `verify-milestone-295` CLI 子命令
4. [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md) — 补充第 50 节 Grand Milestone Phase 295 `verify-milestone-295` 模块与 CLI 说明
5. [`outputs/fx6-on-fx3-closure/tests/test_realhw_milestone295_master_gate.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_milestone295_master_gate.py) — 76 项双模/三态单元测试（全数采用 `sys.executable`、`< 15.0s` 宽裕耗时预算、`assertGreaterEqual` 前向兼容阈值）
6. [`Makefile`](../../Makefile) — 新增 `verify-milestone-295` 双模目标并接入 `.PHONY` 与 `verify-fast`
7. [`.github/workflows/clean-room-ci.yml`](../../.github/workflows/clean-room-ci.yml) — 保留原有 `108-gates` / `45pillar` / `264` 校验并新增 `verify-124-gates`、`verify-50pillar-recovery` 与 `verify-milestone-295` Clean-Room CI 门禁
8. [`reports/2026-11-17-phase295-grand-milestone-124gate-50pillar-45auditor-58stage-10preflight-round58-master-gate/README.md`](./README.md) — 本工程闭环报告

---

## 四、实测验证命令与结果记录

| 验证项目 | 命令 | 实测结果 |
| :--- | :--- | :--- |
| 双模 Master Gate（295 + 264） | `make verify-milestone-295 && make verify-milestone-264` | **PASS**（295 双模 `6/6`；264 双模 `6/6`） |
| Phase 295 单测（本地） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure:outputs/fx6-on-fx3-closure/tests" /usr/bin/python3 -B -m unittest outputs/fx6-on-fx3-closure/tests/test_realhw_milestone295_master_gate.py -v` | **76/76 OK**（`10.142s`） |
| Phase 295 单测（`FX3_CLEAN_ROOM_TEST=1`） | `FX3_CLEAN_ROOM_TEST=1 ... unittest ...test_realhw_milestone295_master_gate.py -v` | **76/76 OK**（`10.251s`） |
| Phase 295 单测（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `FX3_FX6_FORCE_CLEAN_ROOM=1 ... unittest ...test_realhw_milestone295_master_gate.py -v` | **76/76 OK**（`6.199s`） |
| Closure 全量测试发现（Clean-Room） | `FX3_FX6_FORCE_CLEAN_ROOM=1 ... unittest discover -s outputs/fx6-on-fx3-closure/tests` | **1,847 tests OK**（`skipped=51`，`204.524s`） |
| 上游 CI 命令复验 | `fx3_safety verify-124-gates --force-clean-room --simulate-bench-dry-run` + `fx3_recovery verify-50pillar-recovery --clean-room` | **PASS**（`124/124` & `50/50`，`0.808s`） |
| 仓库卫生与 Clean-Room 审计 | `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only && make clean-audit` | **ALL GREEN**（`3.05s`） |
