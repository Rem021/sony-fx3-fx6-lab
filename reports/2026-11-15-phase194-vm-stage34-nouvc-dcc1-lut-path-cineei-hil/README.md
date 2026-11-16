# Phase 194（VM Stage 34 `34/34`）：真实硬件 `ILME-FX3` No-UVC USB Gadget 防火墙、`USB-PD`（`NP-FZ100`）vs `DC-C1`（`>=65W / 5A`）功耗预算、双卡 `.cube` LUT 路径非对称与 `RMT-P1BT` BT/IR HIL 协同仿真报告

## 1. 核心结论（实测与红线零违规）

在 Wave-24 真机情报（[`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h212-phase194-vm-stage34-nouvc-dcc1-lut-path-cineei-hil/reports/2026-11-15-global-sony-wave24-uvc-absence-dcc1-usb-pd-user-lut-path-split-intel/README.md)）与 Stage 33 协同框架基础上，已完成 **VM Stage 34（`stage34_realhw_nouvc_dcc1_lut_path_cineei_hil`，里程碑 `34/34`）** 的实现、编排接入、48 项双模单测及全仓回归验证：

- **高速只读供体审计（`< 0.10s`，进程级缓存）+ 洁净室回退**：[`inspect_phase194_donors`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h212-phase194-vm-stage34-nouvc-dcc1-lut-path-cineei-hil/outputs/fx3-vm/realhw_nouvc_dcc1_lut_path_cineei_coemulator.py#L718) 以严格 `os.O_RDONLY` 有界窗口核验 FX3 `7.02` 与 FX6 `6.01` 共 **12 份真实供体**（`libUsbControl.so`、`cdc_ncm.ko`、`rndis_host.ko`、`libInfraBluetoothCore.so`、`string_english_f.uxc`、`appFw.so`、`cpapp-b.bin`、`libmpr.so`），在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 时确定性切换 `CLEAN_ROOM_SYNTHETIC`（`raw_firmware_bytes_leaked == 0`）。
- **Pillar A — `ILME-FX3`（`0x91030080`）No-UVC USB Gadget 防火墙 & `USB-LAN` / 网络推流（`<= 38 Mbps`）HIL**：[`probe_usb_nouvc_gadget_firewall`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h212-phase194-vm-stage34-nouvc-dcc1-lut-path-cineei-hil/outputs/fx3-vm/realhw_nouvc_dcc1_lut_path_cineei_coemulator.py#L923) 协同仿真 `[USB Connection Mode]`（`Sel. When Connect`、`MassStorage(MSC)`、`MTP`、`Remote Shooting`）及 `USB-LAN`（`CDC-NCM` / `RNDIS`）开机自动连接；对不支持的 `[USB Streaming]` UVC/UAC 复合 Gadget 返回 `EOPNOTSUPP`（`95`）且零 USB PHY 挂死，并将 `4K 59.94p` 实时输出路由至 `RTMP/RTMPS/SRT`（`<= 38 Mbps` HEVC/AVC）或 Type-A HDMI（以及 `1024x576` 无音频旧版 `Remote Shooting` Webcam）。
- **Pillar B — `USB Power Supply`（`NP-FZ100` 强制在位）vs `DC-C1`（`>=65W + 5A` e-Marked 线缆）电气 HIL**：[`probe_power_supply_budget`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h212-phase194-vm-stage34-nouvc-dcc1-lut-path-cineei-hil/outputs/fx3-vm/realhw_nouvc_dcc1_lut_path_cineei_coemulator.py#L1246) 协同仿真机身 Type-C PD 供电开启时拔出 `NP-FZ100` 的瞬时断电风险与开机暂停内充 / 关机续充状态机、Micro-USB 供电拒绝，以及 `DC-C1` 电源门控（`<65W` 或 `3A` 非 e-Marker 线缆触发红灯闪烁欠压拦截；达标则释放机身 Type-C 数据口并锁定 LCD 最大亮度）。
- **Pillar C & D — 双卡 `.cube` User LUT 路径非对称、`Cine EI`、`RMT-P1BT` BT/IR 互斥与硬安全红线**：[`validate_dual_media_cube_lut_path`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h212-phase194-vm-stage34-nouvc-dcc1-lut-path-cineei-hil/outputs/fx3-vm/realhw_nouvc_dcc1_lut_path_cineei_coemulator.py#L1511)、[`evaluate_cine_ei_exposure`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h212-phase194-vm-stage34-nouvc-dcc1-lut-path-cineei-hil/outputs/fx3-vm/realhw_nouvc_dcc1_lut_path_cineei_coemulator.py#L1630)、[`probe_rmtp1bt_and_clip_flag_mutex`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h212-phase194-vm-stage34-nouvc-dcc1-lut-path-cineei-hil/outputs/fx3-vm/realhw_nouvc_dcc1_lut_path_cineei_coemulator.py#L1670) 与 [`probe_hard_safety_redline`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h212-phase194-vm-stage34-nouvc-dcc1-lut-path-cineei-hil/outputs/fx3-vm/realhw_nouvc_dcc1_lut_path_cineei_coemulator.py#L1728) 严格校验 `SD: /Private/Sony/PRO/LUT/` vs `CFexpress-A: /Sony/PRO/LUT/`（`17pt/33pt`、`<=63B`、`16` 槽位、`0..+2EV`）、`Cine EI`（`800/12800`、`3200..51200 EI`）零 CMOS 模拟增益污染、`RMT-P1BT`（BT 4.2）开启禁用 IR (`SIRCS`) 与 GPS 联动（以及 `FX3A` 无 IR/NFC）、`Creators' Cloud` `OK/NG/KEEP`（`H0 == H3`），并硬锁 `persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`physical_usb_packets_emitted = 0`、`otp_fuse_touches = 0`、`rpmb_counter_increments = 0`。

## 2. 交付清单（严格限域修改）

| 文件 | 变更 | 说明 |
| --- | --- | --- |
| [`realhw_nouvc_dcc1_lut_path_cineei_coemulator.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h212-phase194-vm-stage34-nouvc-dcc1-lut-path-cineei-hil/outputs/fx3-vm/realhw_nouvc_dcc1_lut_path_cineei_coemulator.py) | 新增 | Stage 34 (`34/34`) 主模块（12 供体只读审计 + Pillars A–D + `--self-test/--summary/--json/--clean-room`） |
| [`fx3_vm_coemulation_suite.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h212-phase194-vm-stage34-nouvc-dcc1-lut-path-cineei-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py) | 更新 | 接入 [`run_stage34_realhw_nouvc_dcc1_lut_path_cineei_hil`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h212-phase194-vm-stage34-nouvc-dcc1-lut-path-cineei-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py#L2003) 与 `--skip-phase194` |
| [`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h212-phase194-vm-stage34-nouvc-dcc1-lut-path-cineei-hil/outputs/fx3-vm/README.md) | 更新 | 增补 Phase 194 / Stage 34 (`34/34`) 架构与测试命令 |
| [`test_realhw_nouvc_dcc1_lut_path_cineei_coemulator.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h212-phase194-vm-stage34-nouvc-dcc1-lut-path-cineei-hil/outputs/fx3-vm/tests/test_realhw_nouvc_dcc1_lut_path_cineei_coemulator.py) | 新增 | 48 项双模单测（覆盖供体、Pillars A–D、Stage 34 `34/34` 与 `--skip-phase194`、`6.0s` 时限） |
| [`test_realhw_fx3a_branch_firewall_and_xlrh1_4ch_mishoe_coemulator.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h212-phase194-vm-stage34-nouvc-dcc1-lut-path-cineei-hil/outputs/fx3-vm/tests/test_realhw_fx3a_branch_firewall_and_xlrh1_4ch_mishoe_coemulator.py#L573) | 更新 | 仅放宽 Stage 33 阶段数硬编码断言（`assertEqual(..., 33/32)` -> `assertGreaterEqual(..., 33/32)`） |
| [`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h212-phase194-vm-stage34-nouvc-dcc1-lut-path-cineei-hil/reports/2026-11-15-phase194-vm-stage34-nouvc-dcc1-lut-path-cineei-hil/README.md) | 新增 | 本中文验收报告 |

## 3. 实测验证结果（全部使用 `/usr/bin/python3 -B`）

| 验证项 | 模式 | 实测结果 | 备注 |
| --- | --- | --- | --- |
| Stage 34 `--self-test --summary` | `LOCAL_DONOR_RDONLY` | **PASS**（`digest=a3f11f5ad22e`） | `uvc_errno=95 \| srt=3840x2160@59.94p/38.0Mbps \| dcc1=65W/5A \| emmc_wr=0` |
| Stage 34 `--self-test --summary` | `CLEAN_ROOM_SYNTHETIC` | **PASS**（`digest=68584ba7f4ba`） | `raw_firmware_bytes_leaked == 0` |
| 34 阶段套件 `run_fx3_vm_coemulation_suite` | 进程内 / 子进程 | `local_warm=1.8345s`（`< 2.1s`）、`clean_warm=0.2428s`、`clean_subproc=0.7369s`（`< 1.0s`） | 本地子进程冷启动 `2.2712s`，Stage 34 本身耗时 `< 2 ms` |
| Stage 34 专项单测（48 项） | Local / Clean-Room | **48/48 PASS**（`5.031s` / `3.473s`，均 `< 6.0s`） | `PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest ...` |
| `outputs/fx3-vm/tests` 全量发现 | Local | **1276/1276 PASS**（`90.456s`） | 零失败、零残留 `.pyc` |
| `outputs/fx3-vm/tests` 全量发现 | Clean-Room | **1276 tests PASS**（`82.752s`, `skipped=3`） | 仅 3 项既有阶段受本地供体条件跳过 |
| `scripts/run_all_lab_tests.py --clean-only` | 仓库卫生审计 | **ALL GREEN**（`0.04s`） | `git status --porcelain` 二进制/pyc 审计 `CLEAN` |

> [!NOTE]
> 所有仿真均在严格只读（`O_RDONLY`）与离线虚拟内存状态下完成，未对任何真实 physical FX3/FX3A/FX6 设备、eMMC、SPI-NOR、OTP 或 RPMB 执行物理写入或 USB 发包。
