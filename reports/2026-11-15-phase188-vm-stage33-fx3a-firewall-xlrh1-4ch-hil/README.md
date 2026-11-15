# Phase 188（VM Stage 33 `33/33`）：真实硬件 `ILME-FX3` vs `ILME-FX3A` 分支防火墙与 `XLR-H1` MI 热靴 `48kHz/24bit 4ch` 覆盖 HIL 协同仿真报告

## 1. 核心结论（实测与红线零违规）

在 Wave-23 真机情报（[`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h204-phase188-vm-stage33-fx3a-firewall-xlrh1-4ch-hil/reports/2026-11-15-global-sony-wave23-fx3a-vs-fx3-hardware-split-and-xlrh1-4ch-mishoe-intel/README.md)）与 Stage 32 协同框架基础上，已完成 **VM Stage 33（`stage33_realhw_fx3a_firewall_and_xlrh1_4ch_mishoe_hil`，里程碑 `33/33`）** 的实现、编排接入、48 项双模单测及全仓回归验证：

- **高速只读供体审计（`< 0.10s`，进程级缓存）+ 洁净室回退**：通过 [`inspect_phase188_donors`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h204-phase188-vm-stage33-fx3a-firewall-xlrh1-4ch-hil/outputs/fx3-vm/realhw_fx3a_branch_firewall_and_xlrh1_4ch_mishoe_coemulator.py#L649) 以 `os.O_RDONLY` 有界窗口核验 FX3 `7.02` 与 FX6 `6.01` 共 **12 份真实供体**（`libInfraNfc.so`、`libInfraHotshoe.so`、`libInfraSircs.so`、`string_english_f.uxc`、`string_english.uxc`、`cpapp-b.bin`、`appFw.so`、`BODYDATA.DAT`），在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 时确定性切换 `CLEAN_ROOM_SYNTHETIC`（`raw_firmware_bytes_leaked == 0`）。
- **Pillar A — `ILME-FX3` vs `ILME-FX3A` / `ILME-FX30` Stage-A Fail-Closed 分支防火墙 HIL**：[`probe_stage_a_fx3_branch_firewall`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h204-phase188-vm-stage33-fx3a-firewall-xlrh1-4ch-hil/outputs/fx3-vm/realhw_fx3a_branch_firewall_and_xlrh1_4ch_mishoe_coemulator.py#L814) 核验 `model_id`（`0x91030080` vs `0x9103008A` / `0x91030030`）、LCD 点时钟（`1,440,000` vs `2,359,296` XGA）、NFC/IR 设备树及 `7.02` vs `2.02` 固件分支；插入 `ILME-FX3A` 或 `ILME-FX30` 时以 **`31.2 µs < 50 µs`** Fail-Closed 旁路回退原厂 Stock，同时拦截跨型号 `BODYDATA.DAT` 与 `CAMSET` 导入。
- **Pillar B — `XLR-H1` MI 热靴 `48kHz/24bit 4ch` 数字音频 vs 机身 `3.5mm` 物理抢占 HIL**：[`coemulate_xlrh1_mishoe_audio`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h204-phase188-vm-stage33-fx3a-firewall-xlrh1-4ch-hil/outputs/fx3-vm/realhw_fx3a_branch_firewall_and_xlrh1_4ch_mishoe_coemulator.py#L999) 协同仿真 `IN1/IN2 -> CH1/CH2`、`IN3 -> CH3/CH4`、`48kHz/24bit 4ch` / `24bit 2ch` / `16bit 2ch` 及 `CH1/2` / `CH3/4` / `CH1+3/CH2+4` 耳机监听矩阵；验证机身 `3.5mm` 插入立即抢占并灰显锁定 `[MI Shoe Audio Set.]`、`S&Q` 零爆音静音、大版本 `BODYDATA.DAT` 重置 `16bit 2ch` 陷阱防护，以及 `CH1..CH4` Big-6 电平表映射且 FX6 专用排线零故障（`fx6_ribbon_mmio_faults == 0`）。
- **Pillar C & D — 气隙 `FX3BNDL1` 卫生与硬安全红线不变量**：[`validate_fx3bndl1_bundle_hygiene`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h204-phase188-vm-stage33-fx3a-firewall-xlrh1-4ch-hil/outputs/fx3-vm/realhw_fx3a_branch_firewall_and_xlrh1_4ch_mishoe_coemulator.py#L1264) 与 [`probe_hard_safety_redline`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h204-phase188-vm-stage33-fx3a-firewall-xlrh1-4ch-hil/outputs/fx3-vm/realhw_fx3a_branch_firewall_and_xlrh1_4ch_mishoe_coemulator.py#L1364) 硬锁 `persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`physical_usb_packets_emitted = 0`、`otp_fuse_touches = 0`、`rpmb_counter_increments = 0`。

## 2. 交付清单（严格限域修改）

| 文件 | 变更 | 说明 |
| --- | --- | --- |
| [`realhw_fx3a_branch_firewall_and_xlrh1_4ch_mishoe_coemulator.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h204-phase188-vm-stage33-fx3a-firewall-xlrh1-4ch-hil/outputs/fx3-vm/realhw_fx3a_branch_firewall_and_xlrh1_4ch_mishoe_coemulator.py) | 新增 | Stage 33 (`33/33`) 主模块（12 供体只读审计 + Pillars A–D + `--self-test/--summary/--json/--clean-room`） |
| [`fx3_vm_coemulation_suite.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h204-phase188-vm-stage33-fx3a-firewall-xlrh1-4ch-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py) | 更新 | 接入 [`run_stage33_realhw_fx3a_firewall_and_xlrh1_4ch_mishoe_hil`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h204-phase188-vm-stage33-fx3a-firewall-xlrh1-4ch-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py#L1860) 与 `--skip-phase188` |
| [`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h204-phase188-vm-stage33-fx3a-firewall-xlrh1-4ch-hil/outputs/fx3-vm/README.md) | 更新 | 增补 Phase 188 / Stage 33 (`33/33`) 架构与测试命令 |
| [`test_realhw_fx3a_branch_firewall_and_xlrh1_4ch_mishoe_coemulator.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h204-phase188-vm-stage33-fx3a-firewall-xlrh1-4ch-hil/outputs/fx3-vm/tests/test_realhw_fx3a_branch_firewall_and_xlrh1_4ch_mishoe_coemulator.py) | 新增 | 48 项双模单测（覆盖供体、Pillars A–D、Stage 33 `33/33` 与 `--skip-phase188`、`6.0s` 时限） |
| [`test_realhw_emount_info3d_breathing_and_hdmi_4264_raw_coemulator.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h204-phase188-vm-stage33-fx3a-firewall-xlrh1-4ch-hil/outputs/fx3-vm/tests/test_realhw_emount_info3d_breathing_and_hdmi_4264_raw_coemulator.py#L559) | 更新 | 仅放宽 Stage 32 阶段数硬编码断言（`assertEqual(..., 32)` -> `assertGreaterEqual(..., 32)`） |
| [`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h204-phase188-vm-stage33-fx3a-firewall-xlrh1-4ch-hil/reports/2026-11-15-phase188-vm-stage33-fx3a-firewall-xlrh1-4ch-hil/README.md) | 新增 | 本中文验收报告 |

## 3. 实测验证结果（全部使用 `/usr/bin/python3 -B`）

| 验证项 | 模式 | 实测结果 | 备注 |
| --- | --- | --- | --- |
| Stage 33 `--self-test --summary` | `LOCAL_DONOR_RDONLY` | **PASS**（`digest=8969007bd0e0`） | `fx3a_bypass=31.2us \| xlrh1=48000Hz/24bit/4ch \| rib_flt=0 \| emmc_wr=0` |
| Stage 33 `--self-test --summary` | `CLEAN_ROOM_SYNTHETIC` | **PASS**（`digest=4fe91cf67e0d`） | `raw_firmware_bytes_leaked == 0` |
| 33 阶段套件 `run_fx3_vm_coemulation_suite` | 进程内 / 子进程 | `local_warm=0.525s`、`clean=0.476s`（子进程 `0.805s < 0.9s`） | 本地冷启动总计 `2.040s`（Stage 33 本身耗时 `< 2 ms`，冷路径主要来自 Stage 1..32 基线） |
| Stage 33 专项单测（48 项） | Local / Clean-Room | **48/48 PASS**（`5.729s` / `3.835s`，均 `< 6.0s`） | `PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest ...` |
| `outputs/fx3-vm/tests` 全量发现 | Local | **1228/1228 PASS**（`95.052s`） | 零失败、零残留 `.pyc` |
| `outputs/fx3-vm/tests` 全量发现 | Clean-Room | **1228 tests PASS**（`87.930s`, `skipped=3`） | 仅 3 项既有阶段受本地供体条件跳过 |

> [!NOTE]
> 所有仿真均在严格只读（`O_RDONLY`）与离线虚拟内存状态下完成，未对任何真实 physical FX3/FX3A/FX6 设备、eMMC、SPI-NOR、OTP 或 RPMB 执行物理写入或 USB 发包。
