# Phase 191：真机主线安全门 `G65` & `G66`（`ILME-FX3` 无 UVC 防火墙、`USB-PD` / `DC-C1` 供电互锁、双介质 `.cube` User LUT 路径分裂、`Cine EI` `800/12800` 与 `RMT-P1BT` 蓝牙互斥）与 66 门总预检

## 1. 结论先行

基于已合入的 Phase 187（`64` 门预检）与 [Wave-24 索尼真机情报](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h208-phase191-safety-66gates-no-uvc-dcc1-pd-lut-path-split/reports/2026-11-15-global-sony-wave24-uvc-absence-dcc1-usb-pd-user-lut-path-split-intel/README.md)，本阶段在保持 [`evaluate_58gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h208-phase191-safety-66gates-no-uvc-dcc1-pd-lut-path-split/outputs/fx3-safety/fx3_safety/realhw_dualmedia_bench_interlock_and_58gate_guard.py)、[`evaluate_60gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h208-phase191-safety-66gates-no-uvc-dcc1-pd-lut-path-split/outputs/fx3-safety/fx3_safety/realhw_ssboot_wbi2_slot1_ufu_and_60gate_guard.py)、[`evaluate_62gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h208-phase191-safety-66gates-no-uvc-dcc1-pd-lut-path-split/outputs/fx3-safety/fx3_safety/realhw_emount_info3d_hdmi_braw_and_62gate_guard.py) 与 [`evaluate_64gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h208-phase191-safety-66gates-no-uvc-dcc1-pd-lut-path-split/outputs/fx3-safety/fx3_safety/realhw_fx3a_firewall_xlrh1_mishoe_and_64gate_guard.py) 100% 完整兼容的前提下，新增实现 **Gate `G65`**、**Gate `G66`** 及 **66 门主安全预检 [`run_66_gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h208-phase191-safety-66gates-no-uvc-dcc1-pd-lut-path-split/outputs/fx3-safety/fx3_safety/realhw_nouvc_dcc1_pd_lut_path_and_66gate_guard.py)**（别名 `evaluate_66gate_preflight` / `evaluate_66_master_safety_gates`，CLI：`verify-66-gates`）。

- **Gate `G65`（`GATE_G65_FX3_NOUVC_GADGET_AND_USBPD_DCC1_ELECTRICAL_GUARD`）**：
  - 在 `ILME-FX3`（`0x91030080`）/ `ILME-FX3A`（`4.9.337-scel+`）Stage-B 中硬阻断任何 UVC/UAC `[USB Streaming]` 复合 gadget 配置与绑定，仅放行 `Sel. When Connect`、`MassStorage(MSC)`、`MTP`、`Remote Shooting` 与 `USB-LAN`（`RNDIS`/`CDC-NCM`），并强制 4K 推流走 Network Streaming（`RTMP/RTMPS/SRT <= 38 Mbps`）或 Type-A HDMI。
  - 在 Tier-0 冷备与 Stage-B 演练前执行物理供电互锁：`USB_PD_BODY` 必须同时满足 `np_fz100_inserted == True`、`battery_pct >= 51`（`>= 3` 格）且拒绝 Micro-USB 供电；`DC_C1_COUPLER` 必须满足 `usb_pd_watts >= 65W` 且配备 `5A` e-Marked 线缆（`emarked_5a_cable == True`、`cable_max_amps >= 5.0`），拦截 `<65W` 或 `3A` 线引发的 `DC-C1` 闪灯欠压掉电风险。
- **Gate `G66`（`GATE_G66_DUALMEDIA_CUBE_LUT_PATH_CINEEI_AND_RMT_P1BT_BT_GUARD`）**：
  - 校验 `.cube` User LUT 规格（`LUT_3D_SIZE` 严格为 `17` 或 `33`、含 `.cube` 后缀的 ASCII 文件名 `<= 63` 字节、最多 `16` 槽位 `User1..User16`、`AE Level Offset` `0.0..+2.0 EV` 按 `1/3 EV` 步进），同时强制 **SD / SDXC**（`/Private/Sony/PRO/LUT/`）与 **CFexpress Type A**（`/Sony/PRO/LUT/`）路径不对称，拦截互换路径或直接写入 Stock `p2:/setting`。
  - 校验 `Cine EI` 双基准感光度边界（`800 -> 200..3200 EI`、`12800 -> 3200..51200 EI`，`±2 EV` 且零 CMOS 模拟增益篡改）与 `Bluetooth Rmt Ctrl = On`（`RMT-P1BT` BT `4.2`）下红外遥控与智能手机 GPS 位置关联自动禁用互斥锁。
- **安全红线硬锁**：`overall_ready_for_hardware_attach = False`、`human_hardware_attach_token = False`、`persistent_emmc_writes_authorized = False`、`persistent_write_release = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`physical_usb_packets_emitted = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 2. 交付清单（严格限定 6 个受控文件）

1. 核心模块：[realhw_nouvc_dcc1_pd_lut_path_and_66gate_guard.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h208-phase191-safety-66gates-no-uvc-dcc1-pd-lut-path-split/outputs/fx3-safety/fx3_safety/realhw_nouvc_dcc1_pd_lut_path_and_66gate_guard.py)
2. 包导出：[fx3_safety/__init__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h208-phase191-safety-66gates-no-uvc-dcc1-pd-lut-path-split/outputs/fx3-safety/fx3_safety/__init__.py)（导出 `G65`、`G66`、`run_66_gate_preflight`、`evaluate_66gate_preflight` 等 Phase 191 全部公共符号）
3. CLI 入口：[fx3_safety/__main__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h208-phase191-safety-66gates-no-uvc-dcc1-pd-lut-path-split/outputs/fx3-safety/fx3_safety/__main__.py)（新增 `verify-g65-nouvc-dcc1-pd`、`verify-g66-lut-path-cineei-bt`、`verify-66-gates`）
4. 模块文档：[outputs/fx3-safety/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h208-phase191-safety-66gates-no-uvc-dcc1-pd-lut-path-split/outputs/fx3-safety/README.md)（第 3.3 节导出索引与第 33 节 Phase 191 说明）
5. 双模单元测试：[test_phase191_nouvc_dcc1_pd_lut_path_66gate_guard.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h208-phase191-safety-66gates-no-uvc-dcc1-pd-lut-path-split/outputs/fx3-safety/tests/test_phase191_nouvc_dcc1_pd_lut_path_66gate_guard.py)（52 项双模单测）
6. 交付报告：本文件

---

## 3. 实测验证结果（全部使用 `/usr/bin/python3 -B`）

| 验证项 | 命令摘要 | 实测结果 |
|---|---|---|
| 66 门默认离线 CLI | `verify-66-gates --json` / 文本 | `63/66` 通过（`LOCAL_DONOR_O_RDONLY`，`G10..G12` 保持物理未挂载阻断，全红线 `False / 0`） |
| 66 门模拟演练 CLI | `verify-66-gates --dry-run-simulated` | `66/66` 通过，`overall_ready_for_hardware_attach=False`，`human_hardware_attach_token=False` |
| `G65` / `G66` 单门 CLI | `verify-g65-nouvc-dcc1-pd` & `verify-g66-lut-path-cineei-bt` | 均返回 `exit 0` 与 `valid=True` |
| Phase 191 专项单测（本地 donor） | `test_phase191_nouvc_dcc1_pd_lut_path_66gate_guard.py` | **52/52 通过**（`9.132s`；单次 `evaluate_66gate_preflight < 6.0s`） |
| Phase 191 专项单测（Clean-Room） | `FX3_FX6_FORCE_CLEAN_ROOM=1 ... test_phase191_...py` | **52/52 通过**（`5.309s`） |
| `fx3-safety` 全量单测（本地 donor） | `unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | **1285/1285 通过**（`49.627s`，含 `verify-58/60/62/64-gates` 向后兼容） |
| `fx3-safety` 全量单测（Clean-Room） | `FX3_FX6_FORCE_CLEAN_ROOM=1 ... discover` | **1285 项通过**（`skipped=1`，`42.986s`） |
| Clean-Room 卫生审计 | `scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN / CLEAN`（`0.05s`，零 `.pyc` / 二进制污染） |

---

## 4. 实测事实与未执行物理动作边界

- **已实测离线事实**：通过 `os.O_RDONLY` 只读校验本地 `fx3/cpapp-b.bin`（`15,980,568 B`，SHA-256 `c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba`）、`fx3/appFw.so`（`79,015,712 B`，`545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f`）与 `fx3/libUsbBusPower.so`（`48,232 B`，`c606880c92ecf6028c436233b50e0b08791ff8cf0d9dbae748359b38013f5748`）全部完整匹配；`FX3_FX6_FORCE_CLEAN_ROOM=1` 清洁室与本地只读双模通过，`G65` / `G66` 故障注入、向后兼容及包命名空间一致性（复用 `MEDIA_TYPE_CFEXPRESS_A = "CFEXPRESS_TYPE_A"`）均已实测通过。
- **未执行物理动作**：未连接任何真实 `ILME-FX3`、`ILME-FX3A` 机身、`DC-C1` 假电池、`RMT-P1BT` 遥控器或物理存储卡；未发送任何物理 USB 数据包；未执行任何 eMMC / SPI-NOR 持久化写入或跨机型分区刷写。
