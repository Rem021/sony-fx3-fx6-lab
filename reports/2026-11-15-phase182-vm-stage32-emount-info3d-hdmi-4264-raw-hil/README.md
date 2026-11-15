# Phase 182（VM Stage 32 `32/32`）— Real-Hardware `MIRA_CETUS2` E-Mount `info7/info8/info3D` + `0x02cf0232` 呼吸补偿 & Type-A HDMI `4264x2408` 16-bit RAW（`BRAW` / `ProRes RAW`）HIL 协同仿真交付报告

## 1. 结论摘要
- **交付状态**：**PASS（`32/32` 全板阶段通过）**，严格遵循“仅触及授权目录 + 只读 `os.O_RDONLY` 供体校验 + 零原始索尼固件字节泄漏（`raw_firmware_bytes_leaked == 0`）+ 物理硬件零写入红线”。
- **核心实现**：
  - [realhw_emount_info3d_breathing_and_hdmi_4264_raw_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h198-phase182-vm-stage32-emount-info3d-hdmi-4264-raw-hil/outputs/fx3-vm/realhw_emount_info3d_breathing_and_hdmi_4264_raw_coemulator.py)
  - [fx3_vm_coemulation_suite.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h198-phase182-vm-stage32-emount-info3d-hdmi-4264-raw-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py)（新增 `stage32_realhw_emount_info3d_breathing_hdmi_4264_raw_hil` 与 `--skip-phase182`）
  - [test_realhw_emount_info3d_breathing_and_hdmi_4264_raw_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h198-phase182-vm-stage32-emount-info3d-hdmi-4264-raw-hil/outputs/fx3-vm/tests/test_realhw_emount_info3d_breathing_and_hdmi_4264_raw_coemulator.py)（48 项双模单测）
  - [outputs/fx3-vm/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h198-phase182-vm-stage32-emount-info3d-hdmi-4264-raw-hil/outputs/fx3-vm/README.md)

## 2. 四大支柱（Pillars A–D）实测核验
1. **双模高速只读供体审计（`O_RDONLY` `< 0.10s` + 进程级缓存 + 洁净室回退）**：
   - 核验 12 份真实 FX3 `7.02` & FX6 `6.01` 供体：`libInfraLensCommunicator.so`（`14,544 B` 零差异大小与符号）、`libInfraAdjMedia.so`（`318,152 B` / `334,536 B`）、4 份 `string_english*.uxc`（`uxc\x07` 魔数及 `4264x2408`、`Breathing Comp`、`Focus Map`、`ProRes`、`RAW Output Format`），并对 `cpapp-b.bin` 与 `appFw.so` 使用 `<= 4096 B` 有界窗口锁定 `Draw Widget <FocusMap>`、`fixed_lensfile`、`uc_BreathingCorrectionLensType`、`HDMI_RAW_CONNECTSTATE_NOT_SET`、`info7`/`info8` 与 LE `0x02cf0232`。
   - `FX3_FX6_FORCE_CLEAN_ROOM=1` 下切换至确定性 `CLEAN_ROOM_SYNTHETIC`，四大支柱输出与安全红线完全一致。
2. **Pillar A — `MIRA_CETUS2` E-Mount `info7/info8/info3D` & `0x02cf0232` 呼吸补偿 HIL**：
   - 校验白名单谓词 `((lens_id >> 14) == 3) && ((lens_id & 0x0FFF) != 0x0FFF)`：对 `SELP1635G`（`0xC120`）、`SEL2470GM2`（`0xC135`）放行 `0x02cf0232` 呼吸补偿、Catalyst 元数据注入与 M&C `2.1.0+` Focus Map；门控拦截副厂 `0x4210`、保留位陷阱 `0xCFFF` 与手动 PL 转接环 `0xFFFF`；HDMI RAW 激活时强制 `1.0x` 旁路，且 `p18:/lens/LENSFILE.BIN` 锁定 `BLKROSET=1`（`lens_partition_writes == 0`）。
3. **Pillar B — Type-A HDMI `4264x2408`（`<= 60p`）16-bit Linear RAW vs 屏蔽 `12G-SDI` HIL**：
   - CTA-861 EDID + Sony VSIF（`0x81`）握手：`Video Assist 12G HDR 3.22+` 接纳 16->12-bit `.braw`（Capture-Locked ISO），拒绝 `Video Assist 3G`；`Atomos Ninja V/Ultra`（`AtomOS 10.64+`）封装 WB + ISO 偏移输出 `ProRes RAW`；同步机内双卡槽 `XAVC S-I / HS + Proxy`，`1.5x/1.6x` 变形反挤压仅渲染于 OSD 严禁烘焙入 RAW，且 `12G-SDI` BNC MMIO 零故障（`sdi_bnc_mmio_faults == 0`）。
4. **Pillar C & D — `WPA2/WPA3` 网络净化与硬安全红线不变式**：
   - 仅放行 `WPA2`、`WPA3`、`WIRED_USB_CDC_NCM`，拦截 `WEP`/`WPA1`/`OPEN`/`TKIP`/`IPsec` 与路径穿越/控制字符；硬锁定 `persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`physical_usb_packets_emitted = 0`、`otp_fuse_touches = 0`、`rpmb_counter_increments = 0`。

## 3. 验证记录（严格 `/usr/bin/python3 -B`）
- `PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_emount_info3d_breathing_and_hdmi_4264_raw_coemulator.py` -> **48 tests OK (`6.631s`)**
- `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_emount_info3d_breathing_and_hdmi_4264_raw_coemulator.py` -> **48 tests OK (`4.114s`)**
- `PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"` -> **1180 tests OK (`90.421s`)**
- `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"` -> **1180 tests OK (`84.640s`, `skipped=3`)**
- `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` -> **`ALL GREEN in 0.04s`**（`git status --porcelain binary/pyc audit: CLEAN`）
- `fx3_vm_coemulation_suite.py`（32 阶段）：本地缓存后热态 `0.543s`（冷盘首扫 `2.074s`），洁净室 `0.490s < 0.85s`；支持 `--skip-phase182`。

