# Grand Milestone Phase 364 实机主线 6 支柱总闸门（`>=156-Gate` · `>=65-Pillar` · `45/45 Auditors` · `>=80-Stage VM HIL` · `22/22 Bench Preflights (Ph186..Ph358)` · `>=48 QEMU Rounds / >=144 Runs / >=96 PNGs`）闭环报告

## 一、核心结论（结论先行）

1. **Grand Milestone Phase 364 总闸门（`schema = "realhw_milestone364_master_gate_v1"` / `python3 -B -m fx6_closure verify-milestone-364`）已完成端到端闭环并通过四态全量实测验证**：
   - 严格在指定的 **6 个归属路径**内完成交付（未修改根 `Makefile`、`.github/workflows/*` 或任何跨包模块）：[`realhw_milestone364_master_gate.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone364_master_gate.py)、[`__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py)、[`__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py)、[`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md)（第 66 节）、[`test_realhw_milestone364_master_gate.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_milestone364_master_gate.py)（`96` 项全覆盖单元测试）及本闭环报告。
   - 将 **Waves 21–75（Phases 134–363）** 全部 6 大实机主线支柱与 **Rounds 28–75（`48/48` 轮实机内核 ARM64 QEMU、`144/144` 子运行、`96/96` 脱敏 PNG 收据，`max = 27,467 B`）** 收敛为带防篡改 `milestone364_sha256` 的单张主证书：
     - **`LOCAL_DONOR_O_RDONLY` 模式**：`6/6` 支柱全绿（`status = MILESTONE_364_PREBENCH_MASTER_VERIFIED`，`gate156 = 153/156` 离线 NO-GO / `156/156` 模拟干跑、`recovery = 65/65`、`cnflasha_ro = True`、`otp = 0`、`rpmb = 0`、`passive_tx = 0`、`auditors = 45/45`、`vm_stages = 80/80`、`Ph186..Ph358` 全部 `22/22` 双态合规、`H0==H3 = 16/16`、`e_nd_tx = 0`、`rf_pkts = 0`、`slot1_writes = 0`、`qemu = 48/48 (144/144)`、`pngs = 96/96 (max=27467B)`）。
     - **`CLEAN_ROOM_SYNTHETIC` 模式（`FX3_FX6_FORCE_CLEAN_ROOM=1` / `FX3_CLEAN_ROOM_TEST=1` / `work_root=None` / 无 `Mac/` 无供体 CI 环境）**：零索尼专有固件依赖，`6/6` 支柱全绿并通过 `verify_realhw_milestone364_master_gate` 防篡改校验。
2. **前向兼容（`>=` 下界 + 动态自动发现）与历史向后兼容双保证**：
   - 依据当前 HEAD 实态设定前向兼容下界（`>=156` 安全闸门、`>=65` 恢复支柱、`45/45` 固件实验室审计器、`>=80` VM HIL 阶段、`22/22` 物理台架预检 `Ph186..Ph358`、`>=48` QEMU 轮次 / `>=144` 子运行 / `>=96` PNG 收据 `<= 27,467 B` 且 `< 51,200 B`），自动发现未来更高 `verify-*gates`（`158+`）、`*pillar*`（`66+`）、`Stage 81+` 与 `Round 76+`。
   - 保留 `f141c0e17` 负向布尔审计规则（`bk.startswith(("fx3_", "fx6_")) and (bk.endswith(("_present", "_only", "_exposed", "_supported")) or "_has_" in bk)` 期望 `False`）并强制 `broken_audit` fail-closed 拦截。
   - 双模向后兼容：`verify-milestone-349`（Normal 与 `FX3_FX6_FORCE_CLEAN_ROOM=1`）及 `test_realhw_milestone349_master_gate.py`（`92/92 OK`）全部保持绿灯通过。
3. **严格区分实测事实与未执行物理真机边界 / 推断**：
   - **实测事实（Verified Facts）**：
     - `test_realhw_milestone364_master_gate.py` 在 **Normal `LOCAL_DONOR_O_RDONLY`（含 `work_root=None` 与无 `Mac/` 无供体 CI 模拟夹具）**：`96/96 OK`（`36.383s`）；**`FX3_CLEAN_ROOM_TEST=1`**：`96/96 OK`（`35.071s`）；**`FX3_FX6_FORCE_CLEAN_ROOM=1`**：`96/96 OK`（`32.449s`）。
     - `test_realhw_milestone349_master_gate.py` 向后兼容实测：`92/92 OK`（`30.780s`）。
     - CLI `verify-milestone-364 --json` 在 `LOCAL_DONOR_O_RDONLY`、`--force-clean-room`（`FX3_FX6_FORCE_CLEAN_ROOM=1`）及 `--simulate-bench-dry-run` 均返回 `rc=0`、`status=MILESTONE_364_PREBENCH_MASTER_VERIFIED`、`6/6`、`verify_realhw_milestone364_master_gate(payload).valid == True` 与 `compute_milestone364_sha256(payload) == payload["milestone364_sha256"]`。同输入对象序列化 (`to_deterministic_json`) 与摘要重算 100% 确定性一致；两次独立实时评测运行间仅上游 `fx3_vm_coemulation_suite` 混入运行时耗时的 `P4.audit_digest_sha256` / `P4.stage46..66_digest_sha256` 与 `P5.p204_sim_report_sha256` 会随实时耗时变化（与 Milestone 349 实测特征一致）。
     - CLI `verify-milestone-349 --json` 双模（`LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1`）均返回 `status=MILESTONE_349_PREBENCH_MASTER_VERIFIED`、`6/6`、`pref=20`。
     - `PYTHONDONTWRITEBYTECODE=1 make clean-audit` 全绿且零 `.pyc` / 未跟踪文件污染。
   - **未执行物理真机边界（Not Executed Physically / Hard-Locked Redlines）**：
     - **真实物理 Sony ILME-FX3 相机上电 USB 连接、Tier-0 物理实机冷备签收及现场插卡/烧录均尚未执行（也未对真机产生任何写入）**；`--simulate-bench-dry-run` 仅代表离线台架预演，不等价于物理真机授权。全链路物理安全红线硬锁定为拒绝（`overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`persistent_emmc_writes_authorized = False`、`emmc_writes_authorized = False`、`cross_model_flash_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`cnflasha_userspace_write_blocked = True`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`、`e_nd_actuator_tx_count = 0`、`rf_packets_transmitted = 0`、`slot1_data_sector_writes = 0`、`otp_fuse_touches = 0`、`rpmb_counter_increments = 0`、`passive_tx_bytes_emitted = 0`）。

---

## 二、六大实机支柱验收矩阵（`realhw_milestone364_master_gate_v1`）

| 支柱 ID | 支柱名称 | 验收契约与前向兼容机制 | 实测结果（Local Donor / Clean-Room） |
| :--- | :--- | :--- | :--- |
| **`P1`** | `SAFETY_156PLUS_GATE_REALHW_MASTER_PREFLIGHT` | 动态发现最高 `fx3_safety.verify-*gates`（`N >= 156`，自动兼容 `158+`）：离线 `== N - 3`（`153/156`，`G10..G12` fail-closed），`--simulate-bench-dry-run` `N/N`（`156/156`），逐项校验 `G63..G156+` 与 `P1` 硬锁红线 | `offline=153/156` · `simulated=156/156` · `cross_model_flash=False` · `usb_tx=0` · **PASS** |
| **`P2`** | `SIXTY_FIVE_PLUS_PILLAR_RECOVERY_MASTER_VAULT` | 动态发现最高 `fx3_recovery.*pillar*`（`M >= 65`，自动兼容 `66+`）：`M/M` 全绿（`65/65` `verify-65pillar-recovery`），校验 `cnflasha_userspace_write_blocked=True`、`otp_fuse_touches=0`、`rpmb_counter_increments=0`、`passive_tx_bytes_emitted=0`、`slot1_data_sector_writes=0` | `65/65` (`cnflasha_ro=True`) · `otp=0, rpmb=0, passive_tx=0, slot1=0` · **PASS** |
| **`P3`** | `FORTY_FIVE_PLUS_FIRMWARE_LAB_REALBIN_AUDITORS` | 校验 `fx3_firmware_lab` `45/45` 实机只读审计器并支持发现更高审计器，锁定 `raw_firmware_bytes_leaked=0`、`e_nd_actuator_tx_count=0`、`calibration_mutation_bytes=0`、`wbi_mutation_bytes=0` | `45/45` · `e_nd_tx=0` · `cal_mut=0B` · `leaked=0B` · **PASS** |
| **`P4`** | `EIGHTY_PLUS_STAGE_VM_HIL_COEMULATION` | 运行 `fx3_vm_coemulation_suite` 覆盖 Stages `1..80+`（前向兼容 `81+`），锁定 `vm_stages_passed >= 80`、`raw_firmware_bytes_leaked=0`、`physical_device_writes=0`、`emmc_corruptions=0`、`slot1_avf_info_mutated=False`、`wf12_00342260_hits=0` | `80/80` · `phys_writes=0` · `emmc_corruptions=0` · `leaked=0B` · **PASS** |
| **`P5`** | `DOUOSUPLE_22_BENCH_READINESS_PREFLIGHTS_PH186_TO_PH358` | 校验 `Ph186..Ph345`（20 项）+ Phase 354 第 21 项（`realhw_lockop_shocklesswb_focusmag_afspeed_zebra_custom_and_saveload_camset_verifier`）+ Phase 358 第 22 项（`realhw_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_verifier`）：离线均为 `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT`，干跑均为 `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH`，`16/16 H0==H3`、`e_nd_tx=0`、`rf_pkts=0`、`slot1_writes=0` | `22/22` (`Ph186..Ph358`) · `H0==H3=16/16` · `rf_pkts=0` · `slot1_writes=0` · `ready_attach=False` · **PASS** |
| **`P6`** | `REAL_FX3_702_QEMU_ROUNDS_28_TO_75_PLUS_AND_PNG_RECEIPTS` | 动态扫描 `reports/*-round*-*/summary.json`（`>=48` 轮 `R28..R75+`、`>=144` 次运行、`>=96` 张 PNG `<= 27,467 B` 且 `< 51,200 B`），保留 `f141c0e17` 负向布尔审计校验与 `broken_audit` fail-closed 拦截，跨支柱强制 `16/16 H0==H3`、`emmc_write_count=0`、`raw_firmware_bytes_leaked=0` | `48/48` 轮 (`144/144` runs) · `96/96` PNG (`max=27,467 B`) · `emmc=0, leaked=0` · **PASS** |

---

## 三、严格 6 文件交付清单

1. [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone364_master_gate.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone364_master_gate.py) — Grand Milestone Phase 364 6 支柱并行总闸门、动态前向发现器（`>=156` Gate / `>=65` Pillar / `45/45` Auditor / `>=80` Stage / `Round 76+`）、`22/22` 台架预检验证器（含 `Ph354`、`Ph358`）、`f141c0e17` 负向布尔审计器、防篡改 SHA-256 校验器、双语 Markdown 渲染器与 CLI 入口
2. [`outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py) — 非遮蔽导出 `P364_*` / `MILESTONE364_*` / `STATUS_MILESTONE364_*` / `RealHwMilestone364MasterGateReport` / `evaluate_realhw_milestone364_master_gate` / `verify_realhw_milestone364_master_gate` 等公共符号（完整保留历史里程碑及 `Ph186..Ph358` 导出）
3. [`outputs/fx6-on-fx3-closure/fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py) — 注册并分派 `verify-milestone-364` CLI 子命令（argparse `help=` 无未转义 `%`）
4. [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md) — 追加第 66 节 Grand Milestone Phase 364 `verify-milestone-364` 文档与测试命令
5. [`outputs/fx6-on-fx3-closure/tests/test_realhw_milestone364_master_gate.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_milestone364_master_gate.py) — 96 项四态单元测试（覆盖常量导出、`>=` 前向兼容动态发现、`22/22` 预检、Stage 81+、Round 76+、`f141c0e17` 负向布尔与 `broken_audit`、跨支柱红线、`work_root=None` / 无 `Mac/` 无供体 CI、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1`、双模 CLI 与防篡改验证器）
6. [`reports/2026-11-18-phase364-grand-milestone-364-master-gate/README.md`](./README.md) — 本闭环报告

---

## 四、实测验证命令与结果记录

| 验证项目 | 命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 364 单测（Normal `LOCAL_DONOR_O_RDONLY` + `work_root=None` + 无供体 CI） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm" /usr/bin/python3 -B -m unittest -v outputs/fx6-on-fx3-closure/tests/test_realhw_milestone364_master_gate.py` | **96/96 OK**（`36.383s`） |
| Phase 364 单测（`FX3_CLEAN_ROOM_TEST=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_CLEAN_ROOM_TEST=1 PYTHONPATH="outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm" /usr/bin/python3 -B -m unittest -q outputs/fx6-on-fx3-closure/tests/test_realhw_milestone364_master_gate.py` | **96/96 OK**（`35.071s`） |
| Phase 364 单测（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH="outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm" /usr/bin/python3 -B -m unittest -q outputs/fx6-on-fx3-closure/tests/test_realhw_milestone364_master_gate.py` | **96/96 OK**（`32.449s`） |
| Phase 349 向后兼容单测 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm" /usr/bin/python3 -B -m unittest -q outputs/fx6-on-fx3-closure/tests/test_realhw_milestone349_master_gate.py` | **92/92 OK**（`30.780s`） |
| CLI 双模执行与防篡改校验（`verify-milestone-364`：`default` / `--force-clean-room` / `--simulate-bench-dry-run`） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm" /usr/bin/python3 -B -m fx6_closure verify-milestone-364 [--force-clean-room \| --simulate-bench-dry-run] --json` | **PASS**（`6/6`, `valid=True`, `recompute_match=True`, `153/156` offline / `156/156` sim · `65/65` · `45/45` · `80/80` · `22/22` · `48/48(144/144)` · `96/96 PNG max=27467B`） |
| CLI 双模执行（`verify-milestone-349`：`default` 与 `--force-clean-room`） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm" /usr/bin/python3 -B -m fx6_closure verify-milestone-349 [--force-clean-room] --json` | **PASS**（双模 `6/6`, `pref=20`, `status=MILESTONE_349_PREBENCH_MASTER_VERIFIED`） |
| 仓库卫生与 Clean-Room 审计 | `PYTHONDONTWRITEBYTECODE=1 make clean-audit` | **ALL GREEN**（零 `.pyc` / 未跟踪污染） |
