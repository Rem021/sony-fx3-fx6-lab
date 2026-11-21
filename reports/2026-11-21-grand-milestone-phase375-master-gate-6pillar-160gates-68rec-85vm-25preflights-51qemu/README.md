# Grand Milestone Phase 375 实机主线 6 支柱总闸门（`>=160-Gate` · `>=68-Pillar` · `>=45/45 Auditors` · `>=85-Stage VM HIL` · `25/25 Bench Preflights (Ph186..Ph374)` · `>=51 QEMU Rounds / >=153 Runs / >=102 PNGs`）闭环报告

## 一、核心结论（结论先行）

1. **Grand Milestone Phase 375 总闸门（`schema = "realhw_milestone375_master_gate_v1"` / `make verify-milestone-375` / `python3 -B -m fx6_closure verify-milestone-375`）已完成端到端交付并通过四态全量实测验收**：
   - 严格限定在指定的 **7 个归属文件**内交付（未越界修改任何其他文件）：
     1. [realhw_milestone375_master_gate.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h481-grand-milestone-phase375-master-gate-6pillar/outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone375_master_gate.py)
     2. [__init__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h481-grand-milestone-phase375-master-gate-6pillar/outputs/fx6-on-fx3-closure/fx6_closure/__init__.py)
     3. [__main__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h481-grand-milestone-phase375-master-gate-6pillar/outputs/fx6-on-fx3-closure/fx6_closure/__main__.py)
     4. [README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h481-grand-milestone-phase375-master-gate-6pillar/outputs/fx6-on-fx3-closure/README.md)（第 70 节）
     5. [test_realhw_milestone375_master_gate.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h481-grand-milestone-phase375-master-gate-6pillar/outputs/fx6-on-fx3-closure/tests/test_realhw_milestone375_master_gate.py)（`98` 项 4 模式单元测试）
     6. [Makefile](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h481-grand-milestone-phase375-master-gate-6pillar/Makefile)（新增 `.PHONY`、`verify-milestone-375` 目标及 `verify-fast` 串联）
     7. [README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h481-grand-milestone-phase375-master-gate-6pillar/reports/2026-11-21-grand-milestone-phase375-master-gate-6pillar-160gates-68rec-85vm-25preflights-51qemu/README.md)（本闭环报告）
   - 将 **Waves 21–83** 全部 6 大实机主线支柱（`160/160` 安全闸门、`68/68` 恢复支柱、`45/45` 固件审计器、`86/86` VM HIL 阶段 [满足 `>=85/85` 并前向自动发现 Stage 86]、全部 `25/25` 物理台架预检 `Ph186..Ph374` [集成第 23 项 `Ph368`、第 24 项 `Ph371`、第 25 项 `Ph374`]、`51/51` 轮实机内核 ARM64 QEMU `R28..R78` / `153/153` 子运行 / `102/102` 张 `<50 KiB` PNG 收据 `max = 27,467 B`）统一收敛为带防篡改 `milestone375_sha256` 的主控证书。
2. **前向兼容（`>=` 下界 + 动态自动发现）与历史向后兼容双保证**：
   - `P1` 动态发现最高 `evaluate_<N>gate_preflight`（`N >= 160`，实测命中 `160/160` 且单测覆盖 `162+`）；`P2` 动态发现最高 `evaluate_realhw_<M>pillar_recovery_master`（`M >= 68`，实测命中 `68/68` 且单测覆盖 `69+`）；`P3` 校验 `>= 45/45` 审计器；`P4` 显式校验 Stages `1..85` 并前向发现 `Stage 86+`（在当前 HEAD 上实测自动发现并验证 `Stage 86`，返回 `86/86`）；`P5` 校验全部 `25/25` 台架预检；`P6` 显式校验 `R28..R78`（`51/51` 轮、`153/153` 运行、`102/102` PNG）并前向发现 `Round 79+` 且保留 `f141c0e17` 负向布尔审计规则。
   - 历史向后兼容实测：`make verify-milestone-364` 在 `LOCAL_DONOR_O_RDONLY` 与 `CLEAN_ROOM_SYNTHETIC` 双模下保持 `status=OK pillars=6/6 preflights=22/22 leaked=0`。
3. **严格区分实测事实（Verified Facts）与推断 / 未执行物理真机边界（Inferences & Hardware Redlines）**：
   - **实测事实（Verified Facts）**：
     - [test_realhw_milestone375_master_gate.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h481-grand-milestone-phase375-master-gate-6pillar/outputs/fx6-on-fx3-closure/tests/test_realhw_milestone375_master_gate.py) 四态全通过：
       - **Normal（`LOCAL_DONOR_O_RDONLY` + 内置 `work_root=None` 及无 `Mac/` 无供体 CI 夹具）**：`98/98 OK`（`34.426s`）
       - **`FX3_CLEAN_ROOM_TEST=1`**：`98/98 OK`（`31.608s`）
       - **`FX3_FX6_FORCE_CLEAN_ROOM=1`**：`98/98 OK`（`29.694s`）
     - `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-375`：双命令均返回 `rc=0`、`status=OK`、`pillars=6/6`、`gate160=157/160`、`recovery=68/68`、`cnflasha_ro=True`、`otp=0`、`rpmb=0`、`passive_tx=0`、`auditors=45/45`、`vm_stages=86/86`、`preflights=25/25(p368=DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH,p371=DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH,p374=DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH)`、`h0_eq_h3=16/16`、`e_nd_tx=0`、`rf_pkts=0`、`slot1_writes=0`、`qemu=51/51(153/153)`、`pngs=102/102(max=27467B)`、`ready_attach=False`、`live_attach_auth=False`、`emmc_writes_auth=False`、`cross_model_flash_auth=False`、`spi_nor_auth=False`、`el3_tx_auth=False`、`usb_tx=0`、`leaked=0`。
     - `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 make verify-milestone-375`：双命令均返回 `rc=0`、`status=OK`、`mode=CLEAN_ROOM_SYNTHETIC`、`pillars=6/6`、`preflights=25/25`、`leaked=0`。
     - `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-364`：双命令均返回 `rc=0`、`status=OK`、`pillars=6/6`、`preflights=22/22`、`leaked=0`。
     - `PYTHONDONTWRITEBYTECODE=1 make clean-audit`：`Clean-Room Audit: ALL GREEN in 0.08s`（零专有固件、零 `.pyc` / `__pycache__` 污染）。
   - **推断与未执行物理真机边界（Inferences / Not Executed Physically）**：
     - **推断**：由于 `P1`（`>=160`）、`P2`（`>=68`）、`P3`（`>=45`）、`P4`（`>=85` + `Stage 86+` 动态发现）、`P6`（`>=51` + `Round 79+` 动态发现）全部采用前向兼容动态下界与单测夹具验证，后续合并 `Gate 162+`、`Pillar 69+`、`Stage 87+`、`Round 79+` 预计不会破坏 Phase 375 总闸门（仍需在对应合入分支实际回归确认）。
     - **未执行物理真机边界（Hard-Locked NO-GO）**：本任务**未连接、未枚举、未写入任何真实物理 Sony ILME-FX3 相机或物理 SD/CFexpress/eMMC 介质**。所有硬件写入与跨机型刷写授权均硬锁定为拒绝（`ready_attach=False`、`live_attach_auth=False`、`emmc_writes_auth=False`、`cross_model_flash_auth=False`、`spi_nor_auth=False`、`el3_tx_auth=False`、`usb_tx=0`、`leaked=0`）；`DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` 仅代表离线模拟干跑通过，不构成物理连接或刷写授权。

---

## 二、六大实机支柱验收矩阵（`realhw_milestone375_master_gate_v1`）

| 支柱 ID | 支柱名称 | 验收契约与前向兼容机制 | 实测结果（Local Donor / Clean-Room） |
| :--- | :--- | :--- | :--- |
| **`P1`** | `SAFETY_160PLUS_GATE_REALHW_MASTER_PREFLIGHT` | 动态发现最高 `evaluate_<N>gate_preflight`（`N >= 160`，前向兼容 `162+`）：离线严格 `(N-3)/N`（`157/160`，Tier-0 `G10..G12` fail-closed），干跑 `N/N`（`160/160`），逐项校验 `G63..G160+` 及 `cross_model_flash_authorized=False` | `offline=157/160` · `simulated=160/160` · `cross_model_flash=False` · `usb_tx=0` · **PASS** |
| **`P2`** | `SIXTY_EIGHT_PLUS_PILLAR_RECOVERY_MASTER_VAULT` | 动态发现最高 `evaluate_realhw_<M>pillar_recovery_master`（`M >= 68`，前向兼容 `69+`）：`M/M` 全绿（`68/68`），校验 Pillars `66..68` 零违规计数与 FX3/FX6 硬件边界，锁定 `cnflasha_ro=True`、`otp=0`、`rpmb=0`、`passive_tx=0`、`usb_tx=0`、`slot1_writes=0` | `68/68` (`cnflasha_ro=True`) · `otp=0, rpmb=0, passive_tx=0, slot1=0` · **PASS** |
| **`P3`** | `FORTY_FIVE_PLUS_FIRMWARE_LAB_REALBIN_AUDITORS` | 校验 `fx3_firmware_lab` `>= 45/45` 实机只读审计器并支持前向发现 `46+`，锁定 `raw_firmware_bytes_leaked=0`、`e_nd_actuator_tx_count=0`、`calibration_mutation_bytes=0`、`wbi_mutation_bytes=0` | `45/45` · `e_nd_tx=0` · `cal_mut=0B` · `leaked=0B` · **PASS** |
| **`P4`** | `EIGHTY_FIVE_PLUS_STAGE_VM_HIL_COEMULATION` | 运行 `fx3_vm_coemulation_suite` 覆盖 Stages `1..85`（显式校验 `Stage 81..85` 里程碑、摘要与违规计数）并自动发现 `Stage 86+`（实测发现 HEAD 上的 `Stage 86`），锁定 `vm_stages_passed >= 85`、`phys_writes=0`、`emmc_corruptions=0`、`wf12=0`、`leaked=0` | `86/86` (`>=85` PASS) · `phys_writes=0` · `emmc_corruptions=0` · `leaked=0B` · **PASS** |
| **`P5`** | `QUINVIGINTUPLE_25_BENCH_READINESS_PREFLIGHTS_PH186_TO_PH374` | 并行执行全部 `25/25` 物理台架预检：`Ph136/143/154` + `Ph186..Ph358`（22 项）+ 第 23 项 `Ph368`（[realhw_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_verifier.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h481-grand-milestone-phase375-master-gate-6pillar/outputs/fx6-on-fx3-closure/fx6_closure/realhw_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_verifier.py)）+ 第 24 项 `Ph371`（[realhw_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_verifier.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h481-grand-milestone-phase375-master-gate-6pillar/outputs/fx6-on-fx3-closure/fx6_closure/realhw_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_verifier.py)）+ 第 25 项 `Ph374`（[realhw_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_verifier.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h481-grand-milestone-phase375-master-gate-6pillar/outputs/fx6-on-fx3-closure/fx6_closure/realhw_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_verifier.py)），验证离线 `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT`、干跑 `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH`、`16/16 H0==H3`、`e_nd_tx=0`、`rf_pkts=0`、`slot1_writes=0`、`overall_ready_for_hardware_attach=False` | `25/25` (`Ph186..Ph374`) · `H0==H3=16/16` · `e_nd_tx=0` · `rf_pkts=0` · `slot1_writes=0` · `ready_attach=False` · **PASS** |
| **`P6`** | `REAL_FX3_702_QEMU_ROUNDS_28_TO_78_PLUS_AND_PNG_RECEIPTS` | 校验 `R28..R78`（`>=51/51` 轮、`>=153/153` 子运行、`>=102/102` 张 `<50 KiB` PNG 收据，实测基线最大 `27,467 B`），动态发现 `Round 79+` 并保留 `f141c0e17` 负向布尔规则，跨支柱锁死 `16/16 H0==H3`、`nop=0`、`crashes=0`、`emmc=0`、`leaked=0 B` | `51/51` 轮 (`153/153` runs) · `102/102` PNG (`max=27,467 B`) · `nop=0, crashes=0, emmc=0, leaked=0B` · **PASS** |

---

## 三、严格 7 文件交付清单

1. [realhw_milestone375_master_gate.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h481-grand-milestone-phase375-master-gate-6pillar/outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone375_master_gate.py) — Grand Milestone Phase 375 6 支柱并行总闸门、动态前向发现器（`>=160` Gate / `>=68` Pillar / `>=45` Auditor / `>=85` Stage [发现 `86+`] / `Round 79+`）、`25/25` 台架预检验证器（含 `Ph368`、`Ph371`、`Ph374`）、`f141c0e17` 负向布尔审计器、防篡改 SHA-256 校验器、双语 Markdown 渲染器与 CLI 入口
2. [__init__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h481-grand-milestone-phase375-master-gate-6pillar/outputs/fx6-on-fx3-closure/fx6_closure/__init__.py) — 非遮蔽导出 `P375_*` / `MILESTONE375_*` / `STATUS_MILESTONE375_*` / `RECOVERY_68_PILLAR_IDS` / `VM_COEMULATION_85_STAGE_KEYS` / `ROUND28_TO_78_*` / `RealHwMilestone375MasterGateReport` / `evaluate_realhw_milestone375_master_gate` / `verify_realhw_milestone375_master_gate` 等公共符号
3. [__main__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h481-grand-milestone-phase375-master-gate-6pillar/outputs/fx6-on-fx3-closure/fx6_closure/__main__.py) — 注册并分派 `verify-milestone-375` CLI 子命令（`argparse` `help=` 无未转义 `%`）
4. [README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h481-grand-milestone-phase375-master-gate-6pillar/outputs/fx6-on-fx3-closure/README.md) — 追加第 70 节 Grand Milestone Phase 375 `verify-milestone-375` 文档与运行命令
5. [test_realhw_milestone375_master_gate.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h481-grand-milestone-phase375-master-gate-6pillar/outputs/fx6-on-fx3-closure/tests/test_realhw_milestone375_master_gate.py) — 98 项四态前向兼容单元测试（覆盖常量导出、`>=` 动态发现、`25/25` 预检、Stage 81..86+、Round 76..79+、`f141c0e17` 负向布尔、递归耗时剥离确定性校验、`work_root=None` / 无 `Mac/` 无供体 CI、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1`、Makefile 接线、CLI 与向后兼容 `verify-milestone-364`）
6. [Makefile](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h481-grand-milestone-phase375-master-gate-6pillar/Makefile) — 新增 `.PHONY`、`verify-milestone-375` 目标（串联正常模式与 `--force-clean-room`）并将 `verify-milestone-375` 追加至 `verify-fast`
7. [README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h481-grand-milestone-phase375-master-gate-6pillar/reports/2026-11-21-grand-milestone-phase375-master-gate-6pillar-160gates-68rec-85vm-25preflights-51qemu/README.md) — 本闭环报告

---

## 四、实测验证命令与结果记录

| 验证项目 | 命令 | 实测结果 |
| :--- | :--- | :--- |
| Phase 375 单测（Normal `LOCAL_DONOR_O_RDONLY` + `work_root=None` + 无供体 CI） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm" /usr/bin/python3 -B -m unittest -q outputs/fx6-on-fx3-closure/tests/test_realhw_milestone375_master_gate.py` | **98/98 OK**（`34.426s`） |
| Phase 375 单测（`FX3_CLEAN_ROOM_TEST=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_CLEAN_ROOM_TEST=1 PYTHONPATH="outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm" /usr/bin/python3 -B -m unittest -q outputs/fx6-on-fx3-closure/tests/test_realhw_milestone375_master_gate.py` | **98/98 OK**（`31.608s`） |
| Phase 375 单测（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH="outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm" /usr/bin/python3 -B -m unittest -q outputs/fx6-on-fx3-closure/tests/test_realhw_milestone375_master_gate.py` | **98/98 OK**（`29.694s`） |
| Make 总闸门（Normal + `--force-clean-room`） | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-375` | **PASS**（双模 `status=OK pillars=6/6 gate160=157/160 recovery=68/68 auditors=45/45 vm_stages=86/86 preflights=25/25 qemu=51/51(153/153) pngs=102/102(max=27467B) leaked=0`） |
| Make 总闸门（强制 Clean-Room 环境变量） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 make verify-milestone-375` | **PASS**（双模 `status=OK mode=CLEAN_ROOM_SYNTHETIC pillars=6/6 preflights=25/25 leaked=0`） |
| Phase 364 向后兼容总闸门 | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-364` | **PASS**（双模 `status=OK pillars=6/6 preflights=22/22 leaked=0`） |
| 仓库卫生与 Clean-Room 审计 | `PYTHONDONTWRITEBYTECODE=1 make clean-audit` | **ALL GREEN**（`0.08s`，零专有固件 / 零 `.pyc` 污染） |
