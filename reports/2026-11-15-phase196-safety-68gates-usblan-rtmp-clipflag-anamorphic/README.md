# Phase 196：真机主线安全门 `G67` & `G68`（`ILME-FX3` `Ver. 7.02` 开机 `USB-LAN` 自动连接与 `RTMP/RTMPS/SRT <= 38 Mbps`、`Creators' Cloud` Clip-Flag `OK/NG/KEEP`、变形宽银幕 `1.5x/1.6x` 与高亮度监看对焦放大共存）及 68 门总预检

## 1. 结论先行

基于已合入的 Phase 191（`66` 门预检）与 [Wave-24 索尼真机情报](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h214-phase196-safety-68gates-usblan-rtmp-clipflag-anamorphic/reports/2026-11-15-global-sony-wave24-uvc-absence-dcc1-usb-pd-user-lut-path-split-intel/README.md)，本阶段在保持 [`evaluate_58gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h214-phase196-safety-68gates-usblan-rtmp-clipflag-anamorphic/outputs/fx3-safety/fx3_safety/realhw_dualmedia_bench_interlock_and_58gate_guard.py)、[`evaluate_60gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h214-phase196-safety-68gates-usblan-rtmp-clipflag-anamorphic/outputs/fx3-safety/fx3_safety/realhw_ssboot_wbi2_slot1_ufu_and_60gate_guard.py)、[`evaluate_62gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h214-phase196-safety-68gates-usblan-rtmp-clipflag-anamorphic/outputs/fx3-safety/fx3_safety/realhw_emount_info3d_hdmi_braw_and_62gate_guard.py)、[`evaluate_64gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h214-phase196-safety-68gates-usblan-rtmp-clipflag-anamorphic/outputs/fx3-safety/fx3_safety/realhw_fx3a_firewall_xlrh1_mishoe_and_64gate_guard.py) 与 [`evaluate_66gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h214-phase196-safety-68gates-usblan-rtmp-clipflag-anamorphic/outputs/fx3-safety/fx3_safety/realhw_nouvc_dcc1_pd_lut_path_and_66gate_guard.py) 100% 完整兼容的前提下，新增实现 **Gate `G67`**、**Gate `G68`** 及 **68 门主安全预检 [`run_68_gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h214-phase196-safety-68gates-usblan-rtmp-clipflag-anamorphic/outputs/fx3-safety/fx3_safety/realhw_usblan_rtmp_clipflag_anamorphic_and_68gate_guard.py)**（别名 `evaluate_68gate_preflight` / `evaluate_68_master_safety_gates`，CLI：`verify-68-gates`）：

- **Gate `G67`（`GATE_G67_FX3_USBLAN_AUTOCONNECT_AND_RTMP_SRT_STREAMING_GUARD`）**：
  - 审计并强制 `ILME-FX3`（`0x91030080`）`Ver. 7.00 / 7.02` 开机 USB Type-C 有线网卡自动连接（`CDC-NCM` / `ASIX` `AX88179` / `RTL8153` / `RNDIS`，供电满足 `NP-FZ100 >= 51%` 或 `DC-C1 >= 65W` + `5A` e-Marked 线缆，拒绝未支持的 `AX88179A/B` / `RTL8156` / `CDC-ECM`）。
  - 硬阻断 Stage-B 覆盖 Stock `/setting`（含 `p2:/setting`、`/dev/nflasha2`）网络配置；强制 Network Streaming 协议（`RTMP` / `RTMPS` / `SRT`）码率上限 `<= 38.0 Mbps`、分辨率 `<= 3840×2160`、`<= 60.0 fps`（标称 `59.94p`）、编码 `H.265/HEVC` 或 `H.264/AVC`，并对 `RTMPS` TLS 证书执行 `EROFS` / `MS_RDONLY` 零修改只读校验。
- **Gate `G68`（`GATE_G68_CREATORS_CLOUD_CLIPFLAG_ANAMORPHIC_AND_BRIGHT_MAGNIFIER_GUARD`）**：
  - 强制 `Creators' App >= 3.1.0` / `Monitor & Control >= 2.4.0` 下 MXF/XML sidecar Clip-Flag（`OK` / `NG` / `KEEP`）非破坏式筛选，确保录制视频 essence `video_essence_modified == False`、`0 B` 修改且 SHA-256 前后一致。
  - 强制 `1.3x / 1.5x / 1.6x / 2.0x` 变形宽银幕反挤压仅作用于监看，且在开启 HDMI RAW 输出时自动禁用以保持 `4264×2408` 线性 RAW 零缩放；同时校验 `CXD90057` 平台上 Bright Monitoring（高亮度监看）与 Focus Magnifier（`1x/2x/4x/8x` 对焦放大）安全共存且不污染录制画面与测光。
- **安全红线硬锁**：离线默认模式实测通过 `65/68`（`G10..G12` 保持物理未挂载阻断，`offline_65_gates_verified = True`），`--dry-run-simulated` 模式实测通过 `68/68`（`all_68_gates_verified = True`），两种模式下 `overall_ready_for_hardware_attach = False`、`human_hardware_attach_token = False`、`persistent_emmc_writes_authorized = False`、`persistent_write_release = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`physical_usb_packets_emitted = 0`、`raw_firmware_bytes_leaked = 0` 全部硬锁不变。

---

## 2. 交付清单（严格限定 6 个受控文件）

1. 核心模块：[realhw_usblan_rtmp_clipflag_anamorphic_and_68gate_guard.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h214-phase196-safety-68gates-usblan-rtmp-clipflag-anamorphic/outputs/fx3-safety/fx3_safety/realhw_usblan_rtmp_clipflag_anamorphic_and_68gate_guard.py)
2. 包导出：[fx3_safety/__init__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h214-phase196-safety-68gates-usblan-rtmp-clipflag-anamorphic/outputs/fx3-safety/fx3_safety/__init__.py)（导出 `G67`、`G68`、`run_68_gate_preflight`、`evaluate_68gate_preflight` 等 Phase 196 全部公共符号）
3. CLI 入口：[fx3_safety/__main__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h214-phase196-safety-68gates-usblan-rtmp-clipflag-anamorphic/outputs/fx3-safety/fx3_safety/__main__.py)（新增 `verify-g67-usblan-rtmp`、`verify-g68-clipflag-anamorphic`、`verify-68-gates`）
4. 模块文档：[outputs/fx3-safety/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h214-phase196-safety-68gates-usblan-rtmp-clipflag-anamorphic/outputs/fx3-safety/README.md)（第 3.3 节导出索引与第 34 节 Phase 196 说明）
5. 双模单元测试：[test_phase196_usblan_rtmp_clipflag_anamorphic_68gate_guard.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h214-phase196-safety-68gates-usblan-rtmp-clipflag-anamorphic/outputs/fx3-safety/tests/test_phase196_usblan_rtmp_clipflag_anamorphic_68gate_guard.py)（52 项双模单测）
6. 交付报告：本文件

---

## 3. 实测验证结果（全部使用 `/usr/bin/python3 -B`）

| 验证项 | 命令摘要 | 实测结果 |
|---|---|---|
| 68 门默认离线 CLI | `verify-68-gates --json` | `65/68` 通过（`VERIFIED_65_OF_68_AWAITING_PHYSICAL_TIER0`，`LOCAL_DONOR_O_RDONLY`，全红线 `False / 0`） |
| 68 门模拟演练 CLI | `verify-68-gates --dry-run-simulated --json` | `68/68` 通过（`VERIFIED_ALL_68_GATES_DRY_RUN_SIMULATED_BACKUP`，`overall_ready_for_hardware_attach=False`） |
| `G67` / `G68` 单门 CLI | `verify-g67-usblan-rtmp` & `verify-g68-clipflag-anamorphic` | 均返回 `exit 0` 与 `valid=True` |
| Phase 196 专项单测（本地 donor） | `test_phase196_usblan_rtmp_clipflag_anamorphic_68gate_guard.py` | **52/52 通过**（`11.640s`；单次 `evaluate_68gate_preflight < 6.0s`） |
| Phase 196 专项单测（Clean-Room） | `FX3_FX6_FORCE_CLEAN_ROOM=1 ... test_phase196_...py` | **52/52 通过**（`7.785s`） |
| `fx3-safety` 全量单测（本地 donor） | `unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` | **1337/1337 通过**（`61.070s`，含 `verify-58/60/62/64/66-gates` 向后兼容） |
| `fx3-safety` 全量单测（Clean-Room） | `FX3_FX6_FORCE_CLEAN_ROOM=1 ... discover` | **1337 项通过**（`skipped=1`，`50.223s`） |
| Clean-Room 卫生审计 | `scripts/run_all_lab_tests.py --clean-only` | `ALL GREEN`（`0.03s`，零 `.pyc` / 二进制污染） |

---

## 4. 实测事实与未执行物理动作边界

- **已实测离线事实**：通过 `os.O_RDONLY` 只读校验本地 `fx3/cpapp-b.bin`（`15,980,568 B`，SHA-256 `c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba`）、`fx3/appFw.so`（`79,015,712 B`，`545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f`）与 `fx3/libNetServiceEther.so`（`114,384 B`，`203b084190a968c732d09fd45e304c406a32eb664d98626114dcf7f178675375`）全部完整匹配；`FX3_FX6_FORCE_CLEAN_ROOM=1` 清洁室与本地只读双模均已实测通过；`G67` / `G68` 故障注入与 `58/60/62/64/66` 门向后兼容全部实测通过。
- **未执行物理动作**：未连接任何真实 `ILME-FX3` / `ILME-FX3A` 机身、USB-LAN 有线网卡、HDMI RAW 外录机或物理存储卡；未发送任何物理 USB 数据包；未执行任何 eMMC / SPI-NOR 持久化写入或跨机型分区刷写。
