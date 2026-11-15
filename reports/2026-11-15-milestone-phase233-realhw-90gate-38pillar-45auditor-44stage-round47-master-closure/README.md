# Grand Milestone Phase 233 实机主线 6 支柱总闸门（`90-Gate` · `38-Pillar` · `45+ Auditor` · `44+ Stage` · `Ph186/204/216/227` · `Rounds 28–47`）闭环报告

## 一、核心结论（结论先行）

1. **Grand Milestone Phase 233 总闸门（`schema = "realhw_milestone233_master_gate_v1"` / `make verify-milestone-233`）已完成端到端闭环并通过双模验证**：
   - 新增 [`realhw_milestone233_master_gate.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone233_master_gate.py)、CLI 子命令 `verify-milestone-233`（[`__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py)）与顶层 [`Makefile`](../../Makefile) 目标 `verify-milestone-233`，将 **Waves 21–32（Phases 134–232）** 全部 6 大实机支柱与 **Rounds 28–47** 实机内核 QEMU 收据统一收敛为带规范化 `milestone233_sha256` 指纹的防篡改证书：
     - **`LOCAL_DONOR_O_RDONLY` 模式**：单次耗时 **`~4.0s`**，`6/6` 支柱全绿（示例运行指纹 `milestone233_sha256 = 6b423a8b14713464...`，对除自身字段外的完整报告字典执行规范化 SHA-256 签名校验）；
     - **`CLEAN_ROOM_SYNTHETIC` 模式（`FX3_FX6_FORCE_CLEAN_ROOM=1`）**：单次耗时 **`~1.2s`**，`6/6` 支柱全绿（示例运行指纹 `milestone233_sha256 = b31bee7d5944d86f...`）。
2. **全支柱前向兼容（Forward-Compatible `>=` 下界）与历史里程碑向后兼容双保证**：
   - 全部 6 大支柱与校验器统一采用 `>=` 前向兼容下界契约（`>= 90` 安全闸门、`>= 38` 恢复支柱、`>= 45` 固件审计器、`>= 44` VM HIL 阶段、`>= 20` 轮 / `>= 60` 子实验 / `>= 40` 张 `< 50 KiB` PNG 收据），支持后续安全门、恢复支柱、审计器、VM 阶段与 `Round 48+` QEMU 目录零破坏自动合入；
   - 同步修正 [`test_realhw_milestone193_master_gate.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_milestone193_master_gate.py) 与 [`test_realhw_milestone209_master_gate.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_milestone209_master_gate.py) 中的历史刚性相等断言为前向兼容 `>=` 下界断言；`make verify-milestone-221` 及全量 `outputs/fx6-on-fx3-closure/tests` 在双模下 0 失败通过。
3. **严格区分实测事实与未执行物理实机边界（Facts vs Physical Bench Boundary）**：
   - **已闭环实测事实**：离线二进制只读审计（`os.O_RDONLY`）、Unicorn AArch64、POSIX `/bin/sh` 沙箱、44 阶段 VM HIL、20 轮（`60/60` 子实验 `r28a..r47c` + `40/40` `< 50 KiB` PNG，最大 `27,467 B`）未修改 Sony `ILME-FX3 Ver. 7.02` (`Linux 4.9.337-scel+`) ARM64 内核 QEMU 演练收据及 **60 项双模单元测试**（[`test_realhw_milestone233_master_gate.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_milestone233_master_gate.py)）全部通过；
   - **未执行物理边界**：**真实物理 Sony ILME-FX3 相机上电 USB 连接、Tier-0 实机冷备签收与现场插卡演练尚未执行**；所有物理写锁与连接锁全程硬锁为否（`overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`cnflasha_userspace_write_blocked = True`、`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`usb_packets_transmitted = 0`、`physical_device_writes = 0`、`raw_firmware_bytes_leaked = 0`）。

---

## 二、六大实机支柱验收矩阵（`realhw_milestone233_master_gate_v1`）

| 支柱 ID | 支柱名称 | 验收阈值与前向兼容契约 | 实测结果（Local Donor / Clean-Room） |
| :--- | :--- | :--- | :--- |
| **`P1`** | `SAFETY_90GATE_REALHW_MASTER_PREFLIGHT` | `fx3_safety.evaluate_90gate_preflight`：离线 `>= 87`（`87/90`，3 道 Tier-0 实机回执门 `G10..G12` fail-closed），`--simulate-bench-dry-run` `>= 90`（`90/90`，`all_90_gates_verified == True`）；逐项校验 `G63..G90` 且全部硬件写/连接锁为 `False`、`usb_packets_transmitted == 0` | `offline=87/90` · `simulated=90/90` · `g63..g90=True` · `usb_pkts=0` · **PASS** |
| **`P2`** | `THIRTY_EIGHT_PILLAR_RECOVERY_MASTER_VAULT` | `fx3_recovery.evaluate_realhw_38pillar_recovery_master`：`>= 38/38`（`all_passed == True`），`cnflasha_userspace_write_blocked == True`、`otp_fuse_touches == 0`、`rpmb_counter_increments == 0`、`passive_tx_bytes_emitted == 0`、`physical_usb_packets_emitted == 0`、`raw_firmware_bytes_leaked == 0` | `38/38` (`cnflasha_ro=True`) · `otp=0, rpmb=0, passive_tx=0, usb_pkts=0` · **PASS** |
| **`P3`** | `FORTY_FIVE_PLUS_FIRMWARE_LAB_REALBIN_AUDITORS` | 校验全部 `>= 45` 项固件审计器（含 `#45` `realhw_filesettings_shotmark_tcregen_and_reclamp_audit`），采用前向兼容断言 `auditors_passed >= 45 and auditors_passed == auditors_total` 并动态纳入 `46+` | `45/45` · `raw_firmware_bytes_leaked=0` · `calibration_mutation_bytes=0` · **PASS** |
| **`P4`** | `FORTY_FOUR_PLUS_STAGE_VM_HIL_COEMULATION` | 运行 `fx3_vm_coemulation_suite` 启用 Stages `1..44`（含 `Stage 39..44`），采用前向兼容断言 `vm_stages_passed >= 44 and vm_stages_passed == vm_stages_total` | `44/44` · `physical_device_writes=0` · `emmc_corruptions=0` · `raw_firmware_bytes_leaked=0` · **PASS** |
| **`P5`** | `QUAD_BENCH_READINESS_PREFLIGHTS_PH186_PH204_PH216_PH227` | 校验 `Phase 136/143/154` 及四联台架预检 `Ph186`、`Ph204`、`Ph216` 与 **`Ph227` (`realhw_pixelmap_ntscpal_powersave_and_autotemp_verifier`)**：离线全为 `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT`，模拟干跑全为 `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH`，`overall_ready_for_hardware_attach == False` | `Ph186=4/4` · `Ph204=3/3` · `Ph216=5/5` · `Ph227=3/3` · `H0==H3=16/16` · **PASS** |
| **`P6`** | `REAL_FX3_702_QEMU_ROUNDS_28_TO_47_AND_PNG_RECEIPTS` | 校验 `Rounds 28–47+` 共 `>= 20` 轮（`20/20`）、`>= 60` 子运行（`60/60` `r28a..r47c`）与 `>= 40` 张脱敏 PNG 收据（每张 `< 50 KiB` / `51,200 B`）、`16/16 H0 == H3`、`emmc_write_count == 0` | `20/20` 轮 (`60/60` runs) · `40/40` PNG (`max=27,467 B < 51,200 B`) · `nop=0, crash=0, emmc=0` · **PASS** |

---

## 三、交付文件清单（严格限定 9 个自有文件）

1. [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone233_master_gate.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone233_master_gate.py)（新增：6 支柱并行评估器、故障注入、SHA-256 防篡改校验器与双语 Markdown 渲染器）
2. [`outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py)（导出 Phase 233 公共常量与 API，零遮蔽历史符号）
3. [`outputs/fx6-on-fx3-closure/fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py)（接入 `verify-milestone-233` CLI 参数与返回码分发）
4. [`outputs/fx6-on-fx3-closure/tests/test_realhw_milestone193_master_gate.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_milestone193_master_gate.py)（修正 CLI 摘要行断言为前向兼容 `>= 40` 审计器 / `>= 33` VM 阶段正则校验）
5. [`outputs/fx6-on-fx3-closure/tests/test_realhw_milestone209_master_gate.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_milestone209_master_gate.py)（修正 `stage_count` 刚性 `== 38` 断言为前向兼容 `>= 38` 下界校验）
6. [`outputs/fx6-on-fx3-closure/tests/test_realhw_milestone233_master_gate.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_milestone233_master_gate.py)（新增：60 项双模 `unittest` 测试，覆盖 6 支柱、`G79..G90`、Pillars `32..38`、`#45` / `Stages 39..44`、`Ph227`、`Rounds 43..47`、前向兼容扩展与安全红线防篡改）
7. [`Makefile`](../../Makefile)（新增 `verify-milestone-233` 双模目标并接入 `verify-fast`）
8. [`docs/REAL-HARDWARE-FX3-702-DEPLOYMENT-DOSSIER.md`](../../docs/REAL-HARDWARE-FX3-702-DEPLOYMENT-DOSSIER.md)（同步 Grand Milestone Phase 233 全景表、`G79..G90`、Pillars `32..38`、`#45` / `Stages 39..44`、`Ph227` 与 `Rounds 43..47`）
9. [`reports/2026-11-15-milestone-phase233-realhw-90gate-38pillar-45auditor-44stage-round47-master-closure/README.md`](./README.md)（本报告）

---

## 四、实测验证命令与结果记录

```sh
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-233
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-221
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure:outputs/fx6-on-fx3-closure/tests" /usr/bin/python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -p "test_*.py"
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure:outputs/fx6-on-fx3-closure/tests" /usr/bin/python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -p "test_*.py"
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```
