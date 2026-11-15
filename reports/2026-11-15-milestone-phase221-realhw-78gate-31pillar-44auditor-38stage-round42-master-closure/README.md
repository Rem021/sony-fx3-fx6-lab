# Grand Milestone Phase 221 实机主线 6 支柱总闸门（`78-Gate` · `31-Pillar` · `44+ Auditor` · `38+ Stage` · `Ph186/204/216` · `Rounds 28–42`）闭环报告

## 一、核心结论（结论先行）

1. **Grand Milestone Phase 221 总闸门（`schema = "realhw_milestone221_master_gate_v1"` / `make verify-milestone-221`）已完成端到端闭环并通过双模验证**：
   - 新增 [`realhw_milestone221_master_gate.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone221_master_gate.py)、CLI 子命令 `verify-milestone-221`（[`__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py)）与顶层 [`Makefile`](../../Makefile) 目标 `verify-milestone-221`，将 **Waves 21–29（Phases 134–220）** 全部 6 大实机支柱与 **Rounds 28–42** 实机内核 QEMU 收据统一收敛为带规范化 `milestone221_sha256` 指纹的防篡改证书：
     - **`LOCAL_DONOR_O_RDONLY` 模式**：单次耗时 **`~2.59s`（`< 5.0s` 预算）**，`6/6` 支柱全绿，`milestone221_sha256 = 819a7b7c27526d65...`；
     - **`CLEAN_ROOM_SYNTHETIC` 模式（`FX3_FX6_FORCE_CLEAN_ROOM=1`）**：单次耗时 **`~1.19s`（`< 5.0s` 预算）**，`6/6` 支柱全绿，`milestone221_sha256 = 66615328a664d70f...`。
2. **前向兼容（Forward-Compatible）与向后兼容双保证**：
   - Pillar 3（`auditors_passed >= 44 and auditors_passed == auditors_total`）支持未来第 `45+` 号 `fx3_firmware_lab/realhw_*_auditor.py` 动态发现与合并零破坏；Pillar 4（`vm_stages_passed >= 38 and vm_stages_passed == vm_stages_total`）支持未来 `Stage 39+` VM HIL 阶段合并零破坏；
   - 历史里程碑 `make verify-milestone-209`、`make verify-milestone-193`、`make verify-milestone-175` 及三项台架预检 CLI 100% 保持原样绿灯。
3. **严格区分实测事实与未执行物理实机边界（Facts vs Physical Bench Boundary）**：
   - **已闭环实测事实**：离线二进制只读审计（`os.O_RDONLY`）、Unicorn AArch64、POSIX `/bin/sh` 沙箱、38 阶段 VM HIL、15 轮（`45/45` 子实验 + `30/30` `< 28 KiB` PNG）未修改 Sony `ILME-FX3 Ver. 7.02` (`Linux 4.9.337-scel+`) ARM64 内核 QEMU 演练收据及 **56 项双模单元测试**（[`test_realhw_milestone221_master_gate.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_milestone221_master_gate.py)）全部通过；
   - **未执行物理边界**：**真实物理 Sony ILME-FX3 相机上电 USB 连接、Tier-0 实机冷备签收与现场插卡演练尚未执行**；所有物理写锁与连接锁全程硬锁为否（`hardware_live_attachment_authorized = False`、`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`）。

---

## 二、六大实机支柱验收矩阵（`realhw_milestone221_master_gate_v1`）

| 支柱 ID | 支柱名称 | 验收阈值与前向兼容契约 | 实测结果（Local Donor / Clean-Room） |
| :--- | :--- | :--- | :--- |
| **`P1`** | `SAFETY_78GATE_REALHW_MASTER_PREFLIGHT` | `evaluate_78gate_preflight`：离线 `75/78`（3 道 Tier-0 实机回执门 `G10..G12` fail-closed），模拟干跑 `78/78`；逐项校验 `G73..G78`（`De-Squeeze 1.65x`、外置 `M&C Focus Map <150fps`、`Simult+AutoSwitch`、`Shockless WB`、`HDMI Log 1080p vs Off(HDMI Only) 4K`、`Px Proxy Vault`、`FocusMag x BrightMon`、`File Settings 37-char/SDHC`、`TC Regenerate Slot-1`、耦合 `REC Lamp`） | `offline=75/78` · `simulated=78/78` · `g63..g78=True` · `e_nd_tx=0` · **PASS** |
| **`P2`** | `THIRTY_ONE_PILLAR_RECOVERY_MASTER_VAULT` | `evaluate_realhw_31pillar_recovery_master`：`>= 31/31`（`VERIFIED_31OF31_PILLAR_RECOVERY_MASTER`），校验 Pillars `29..31`（`CAMSET`/Simult、`Px` 代理/`HDMI Only`、`File Settings`/`ShotMark`/`TC Regenerate` Slot-1），`otp_fuse_writes == 0`、`rpmb_writes == 0`、`passive_tx_bytes == 0` | `31/31` (`31A=True, 31B=True`) · `otp=0, rpmb=0, passive_tx=0, usb_pkts=0` · **PASS** |
| **`P3`** | `FORTY_FOUR_PLUS_FIRMWARE_LAB_REALBIN_AUDITORS` | 校验全部 `44` 项固件审计器（含 Phase 205 `#43` 与 Phase 211 `#44`），采用前向兼容断言 `auditors_passed >= 44 and auditors_passed == auditors_total` 并支持动态发现 `45+` | `44/44` · `raw_firmware_bytes_leaked=0` · `calibration_mutation_bytes=0` · **PASS** |
| **`P4`** | `THIRTY_EIGHT_PLUS_STAGE_VM_HIL_COEMULATION` | 运行 `fx3_vm_coemulation_suite` 校验 Stage 37（Phase 207）与 Stage 38（Phase 213），采用前向兼容断言 `vm_stages_passed >= 38 and vm_stages_passed == vm_stages_total` | `38/38` · `emmc_corruptions=0` · `cp_mutation_bytes=0` · `wf12_hits=0` · **PASS** |
| **`P5`** | `TRIPLE_BENCH_READINESS_PREFLIGHTS_PH186_PH204_PH216` | 校验 `Phase 136/143/154` 及三联台架预检 `preflight-card-insert`（Ph186）、`preflight-bench-cable-fan-slot1`（Ph204）、`preflight-hdmi-proxy-desqueeze-and-simult`（Ph216）：离线全为 `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT`，模拟干跑全为 `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `Ph186=4/4` · `Ph204=3/3` · `Ph216=5/5` · `H0==H3=16/16` · `live_attach_auth=False` · **PASS** |
| **`P6`** | `REAL_FX3_702_QEMU_ROUNDS_28_TO_42_AND_PNG_RECEIPTS` | 校验 `Rounds 28–42` 共 `15/15` 轮（`45/45` 子运行 `r28a..r42c`）与 `30/30` 张脱敏 PNG 收据（每张 `< 28 KiB`）、`16/16 H0 == H3`、`emmc_write_count == 0`、`e_nd_actuator_tx_count == 0` | `15/15` 轮 (`45/45` runs) · `30/30` PNG (`max=27,467 B < 28,672 B`) · `nop=0, crash=0, emmc=0` · **PASS** |

---

## 三、交付文件清单（严格限定 8 个自有文件）

1. [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone221_master_gate.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone221_master_gate.py)（新增：6 支柱并行评估器、故障注入、SHA-256 防篡改校验器与双语 Markdown 渲染器）
2. [`outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py)（导出 Phase 221 常量与 API）
3. [`outputs/fx6-on-fx3-closure/fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py)（接入 `verify-milestone-221` CLI 参数与返回码分发）
4. [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md)（同步模块架构说明与 `#40` 验证命令）
5. [`outputs/fx6-on-fx3-closure/tests/test_realhw_milestone221_master_gate.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_milestone221_master_gate.py)（新增：56 项双模单元测试，覆盖 `G73..G78`、Pillars `29..31`、Auditors `44/44+`、VM Stages `38/38+`、`Ph216 S1..S5`、`Rounds 41..42` 及安全红线防篡改）
6. [`Makefile`](../../Makefile)（新增 `verify-milestone-221` 双模目标并接入 `verify-fast`）
7. [`docs/REAL-HARDWARE-FX3-702-DEPLOYMENT-DOSSIER.md`](../../docs/REAL-HARDWARE-FX3-702-DEPLOYMENT-DOSSIER.md)（同步 Grand Milestone Phase 221 全景表、`G73..G78`、Pillars `29..31`、`#43..#44` / `Stages 37..38`、`Ph216` 与 `Rounds 41..42`）
8. [`reports/2026-11-15-milestone-phase221-realhw-78gate-31pillar-44auditor-38stage-round42-master-closure/README.md`](./README.md)（本报告）

---

## 四、实测验证命令与结果记录

```sh
make verify-milestone-221
make verify-milestone-209
make verify-milestone-193
make verify-milestone-175
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure:outputs/fx6-on-fx3-closure/tests" /usr/bin/python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm:outputs/fx6-on-fx3-closure:outputs/fx6-on-fx3-closure/tests" /usr/bin/python3 -B -m unittest discover -s outputs/fx6-on-fx3-closure/tests -p "test_*.py"
/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```
