# Phase 129 — Live FX6-on-FX3 交互控制台：XAVC MXF OP1a <-> MP4 RDD-18/UMID 容器桥接、SMPTE ST 2059-2 PTPv2 vs LTC 帧相位伺服，以及有线 P12 安全 TSL UMD v5.0 演播室红/绿 Tally + 16 字符动态相机 UMD HUD

> **Phase 129 — Live QEMU FX6-on-FX3 XAVC MXF OP1a <-> MP4 RDD-18/UMID Container Bridge, SMPTE ST 2059-2 PTPv2 vs LTC Frame-Phase Servo, & Wired P12-Safe TSL UMD v5.0 Studio Broadcast Red/Green Tally + 16-Char Dynamic Camera UMD HUD (`'MXFT'` `mb[64..67]` + `mb[68..71]`)**

- **日期 / Date**: 2026-11-14
- **任务分支 / Branch**: `codex/h137-phase129-vm-trial-mxf-ptpv2-tsl-tally-live`
- **隔离验证端口 / Isolated Port**: `http://127.0.0.1:18784/`（`--workdir /private/tmp/fx6_p129_trial_18784 --no-browser`，实测完成后已通过 `POST /api/stop` 停止该隔离 QEMU 会话、仅终止子进程 `PID=974` 并彻底删除 `/private/tmp/fx6_p129_trial_18784`；实时端口 `8768` 全程零接触、零干扰）

---

## 1. 交付概览 / Executive Summary

本阶段在不触动实时服务端口 `8768` 与既有 `P4/P10/P11/P12/G31` 硬件契约的前提下，完成了面向广播演播室流程的 XAVC MXF/MP4 无损元数据桥接、`SMPTE ST 2059-2` `PTPv2` 亚微秒伺服 / 无毛刺 `LTC` 保持与有线 `P12` 安全 `TSL UMD v5.0` 红绿 Tally 边框及 16 字符动态铭牌 HUD：

1. **XAVC `MXF OP1a (RDD-09)` <-> `MP4 ISOBMFF (RTMD)` 无损容器与元数据桥接 / Container & RDD-18/UMID Bridge**
   - 支持 `MP4_ISOBMFF_RTMD`、`MXF_OP1A_RDD09_WRAP` 与 `DUAL_MP4_PLUS_MXF_SIDECAR` 三种容器桥接模式。
   - 生成符合 `SMPTE 330M` 规范的 32 字节（64 十六进制字符）UMID，以及附带 IEEE CRC-32 完整性校验的 `SMPTE RDD-18` KLV 负载（实时联动当前 `Cine EI ExposureIndex` 与 `CaptureGammaEquation`）。
   - 硬锁定 `essence_reencode_loss == 0` 与 `emmc_mutation_bytes == 0`；Fail-Closed 拦截未经转译直接写入 MP4 卡槽的裸 MXF（HTTP `400` `raw_mxf_slot_write_blocked`）、`SPVC` 证书伪造/eMMC 篡改（HTTP `400` `spvc_cert_spoof_blocked`）以及跨编码有损重包装（HTTP `400` `cross_codec_lossless_rewrap_blocked`）。

2. **`SMPTE ST 2059-2` `PTPv2` 亚微秒伺服、无毛刺 `LTC` 保持与 `P12` Wi-Fi-OFF 强锁 / PTPv2 Servo & LTC Holdover**
   - 支持 `OFF`、`PTPV2_SLAVE_WIRED` 与 `LTC_MULTITERMINAL_FALLBACK`。
   - 当有线网口断开（`ethernet_link_up=False`）且 Multi-Terminal `LTC` 接入时，主机状态机与客体邮箱确定性进入 `LTC_MULTITERMINAL_FALLBACK`（`ltc_holdover_active=True`、`holdover_slip_frames <= 0.02`），网口恢复即无毛刺重锁回亚微秒 `PTPv2` 伺服。
   - 客体 `fx6_live_guest.c` 与主机双端硬强制 `P12` Wi-Fi-OFF（`p12_wlan_off=1`、`wf12_00342260_hits=0`），Fail-Closed 拦截任何试图通过 `wlan0`/Wi-Fi/蓝牙同步 `PTPv2` 的请求（HTTP `400` `p12_wlan_off_enforced`）以及将 `PTP-IP 15740` 误当作 `ST 2059` 同步的请求。

3. **演播室广播级 `TSL UMD v5.0` 红/绿 Tally 与 16 字符动态相机 UMD / Studio TSL UMD v5.0 & Stealth Mute**
   - 实现完整 `TSL UMD v5.0` 编解码与往返校验（同时支持标准 `UDP` 报文与 `TCP DLE/STX 0xFE 0x02` 转义成帧）。
   - 支持 `OFF`、`PVW_GREEN`、`PGM_RED` 与 `PGM_PLUS_PVW`，8 机位槽位 `CAM1..CAM8` 与 16 字节可清洗动态标签 `umd_label`（映射至 `mb[68..71]`）。
   - 支持暗场隐身模式 `stealth_led_mute`（切断物理机身 LED `fx3_front_led_on == False`，同时按 `osd_tally_indicator` 保留取景器红/绿提示），并硬锁定 `fx6_green_gpio_faults == 0`。

4. **`NonRealTimeMeta M01.XML`、`CAMSET` 往返与四语紧凑折叠控制台 / XML Sidecar, CAMSET & 4-Language Collapsed Console**
   - `GET /api/xml_sidecar` 自动将 `TargetMaterial umidRef` 对齐至 64-Hex `SMPTE 330M` UMID，并在 `<AcquisitionRecord>` 注入 `<Group name="MxfRdd18Ptpv2TslTallyBridge">`。
   - `GET/POST /api/camset` 完整支持 Phase 129 状态导出与严格篡改拦截导入（拦截 `emmc_mutation_bytes != 0`、`essence_reencode_loss != 0`、`fx6_green_gpio_faults != 0`）。
   - Web 控制台将支持 **EN / 简体中文 / 繁體中文 / 日本語** 的 `#phase129-mxf-ptpv2-tally-card` 置于原生 FX6 页面/菜单导航下方，并默认折叠于紧凑 `<details id="p129-details">` 内（带实时状态摘要胶囊 `#p129-summary-pill`），不挤压核心原生控件布局。

5. **客体 `GPE0` (`0x41e001000`) `'MXFT'` 原生 ARGB8888 边框与 HUD / Guest GPE0 Overlay (`mb[64..67]` + `mb[68..71]`)**
   - 在 [fx6_live_guest.c](../../outputs/fx3-vm-trial/src/fx6_live_guest.c) 中扩展 `mb[64..67]`（偏移 `256..271`，魔数 `0x4d584654` `'MXFT'`）与 16 字符 UMD 邮箱 `mb[68..71]`（偏移 `272..287`，默认 `"FX3-CAM1-STUDIO\0"`），由邮箱 `bit31`（`0x80000000u`）显式门控（支持清零 `bit31` 关闭叠加）。
   - `fx6_render_phase129_mxf_ptpv2_tsl_tally_overlay()` 零堆分配绘制 7px 全周长 `PGM` 红 / `PVW` 绿 / 红绿双色 Tally 边框、第 1 行 `y=350` 三联状态徽章（`MXF/MP4 + RDD18/UMID`、`ST2059 PTPv2/LTC + P12`、`TSL5 CAM# PGM/PVW`）及第 2 行 `y=382` 全宽动态 16 字符 UMD 护栏条，随 `FX6_LIVE_FRAME ... MXFT=0x%08x:0x%08x:0x%08x` 实时回传。

---

## 2. 邮箱协议寄存器契约 / Mailbox Register Contract (`mb[64..67]` `'MXFT'` + `mb[68..71]` UMD)

| Word | 物理地址偏移 / Physical Offset | 关键字段位域布局 / Bit Layout | 默认引导值 / Boot Default |
|---|---|---|---|
| `mb[64]` | `0x41e000e00 + 0x100` (`256`) | `[1:0] container_mode` · `[11:2] rdd18_ei_div10` · `[14:12] gamma_code` · `[15] klv_crc_ok(1)` · `[16] zero_loss(1)` · `[17] emmc_zero(1)` · `[23:18] mxf_blk_cnt` · `[30:24] umid_digest7` · `[31] valid` | `0x870203C4` |
| `mb[65]` | `0x41e000e00 + 0x104` (`260`) | `[1:0] sync_req` · `[3:2] sync_eff` · `[4] eth_link` · `[5] servo_locked` · `[6] ltc_holdover` · `[7] ltc_att` · `[19:8] offset_ns` · `[20] p12_wlan_off(1)` · `[21] wf12_zero(1)` · `[22] cdc_ncm(1)` · `[29:23] p12_blk_cnt` · `[30] domain0` · `[31] valid` | `0x80000070` |
| `mb[66]` | `0x41e000e00 + 0x108` (`264`) | `[1:0] tally_state` · `[2] stealth_mute` · `[3] osd_ind` · `[4] front_led` · `[7:5] cam_idx0` · `[8] tcp_dle_stx` · `[19:9] tsl_crc11` · `[20] tsl_rx_ok` · `[21] green_gpio_zero(1)` · `[29:22] umd_hash8` · `[30] tsl_pkt_valid` · `[31] valid` | `0xB3B11858` |
| `mb[67]` | `0x41e000e00 + 0x10C` (`268`) | 协议魔数 / Magic `'MXFT'` | `0x4D584654` |
| `mb[68..71]` | `0x41e000e00 + 0x110..0x11C` (`272..287`) | 小端打包 16 字节可清洗 ASCII `umd_label`（`\0` 填充） | `"FX3-CAM1-STUDIO\0"` |

---

## 3. 隔离端口实机 QEMU 渲染与自动化验证证据 / Verification Receipts

### 3.1 隔离端口 `--port 18784` 实机 QEMU `GPE0` 像素差异实测 / Live QEMU GPE0 Pixel Delta Proof

在完全隔离工作目录 `/private/tmp/fx6_p129_trial_18784`（`--port 18784 --workdir /private/tmp/fx6_p129_trial_18784 --no-browser`，进程 `PID=974`）启动完整 FX3+FX6 QEMU 虚拟机（`40.82s` 就绪，分辨率 `1024x540`）：

| 验证阶段 / Scenario | 关键状态与遥测结果 / Telemetry | `ack_seq` | `GPE0` 真实像素变化 / Pixel Delta | `APPFW_SEGV` |
|---|---|---|---|---|
| **Baseline Boot** | `boot_crashed=false`, `frame_dims=[1024, 540]` | `1` | 基线帧 | `0` |
| **Step 1 — `PGM_RED` + `PTPV2_SLAVE_WIRED` (`142ns`) + `MXF_OP1A_RDD09_WRAP` + `CAM-A WIDE 24GM`** | `effective_sync_mode=PTPV2_SLAVE_WIRED`, `servo_locked=true`, `fx3_front_led_on=true`, `p12_wlan_off=true`, `wf12_00342260_hits=0`, `emmc_mutation_bytes=0`, `MXFT=0x870203c5:0x80002c75:0xb3b11a7f` | `1 -> 2` | **`73,536` pixels** vs 基线（含 **`24,611`** 红域像素） | `0` |
| **Step 2 — 网线拔除 `PVW_GREEN` + `LTC_MULTITERMINAL_FALLBACK` + `DUAL_MP4_PLUS_MXF_SIDECAR` + `CAM-B CRANE 50GM` (`TCP_DLE_STX`)** | `effective_sync_mode=LTC_MULTITERMINAL_FALLBACK`, `ltc_holdover_active=true`, `holdover_slip_frames=0.0173`, `tsl_packet_hex_prefix=fe021a00000000000300ea00` | `2 -> 3` | **`73,533` pixels** vs 基线；**`64,178` pixels** vs `PGM_RED` | `0` |
| **Step 3 — `PGM_PLUS_PVW` + `stealth_led_mute=True` + `CAM5-STEALTH`** | `fx3_front_led_on=false`, `osd_tally_border_color=RED_GREEN`, `MXFT=0x9f0203c5:0x82002c75:0xb3b11a7f` | `3 -> 4` | **`72,997` pixels** vs 基线（含 **`15,138`** 红域像素） | `0` |
| **Step 4 — XML Sidecar, CAMSET Roundtrip & Fail-Closed HTTP 400** | XML 含 `MxfRdd18Ptpv2TslTallyBridge` 与 `CAM5-STEALTH`；`/api/camset` 往返无损；`use_wifi` -> `400 p12_wlan_off_enforced`，`raw_mxf_on_mp4_slot` -> `400 raw_mxf_slot_write_blocked` | 往返同步 | `final_crashed=false`, `final_p12_wlan_off=true` | `0` |

> **实测串口遥测抽样 / Live Serial Telemetry Sample (`serial.log`, `mxft_line_count=7`, `APPFW_SEGV=0`)**:
> ```text
> FX6_LIVE_FRAME seq=4 page=0 ... UVCS=0x820000c0:0x80660788:0x8000043c MXFT=0x870203c5:0x80002c75:0xb3b11a7f
> FX6_LIVE_FRAME seq=6 page=0 ... UVCS=0x820000c0:0x80660788:0x8020043c MXFT=0x870203c5:0x80002c75:0xb3b11a7f
> FX6_LIVE_FRAME seq=8 page=0 ... UVCS=0x820000c0:0x80660788:0x8020043c MXFT=0x9f0203c5:0x82002c75:0xb3b11a7f
> ```

实测结束后已通过 `POST /api/stop` 停止该隔离会话并仅终止子进程 `PID=974`，同时彻底删除 `/private/tmp/fx6_p129_trial_18784`（`exists=False`），全程未触碰 `8768` 端口，也未使用 `pkill`/`killall`。

### 3.2 离线双模单元测试与全仓洁净门禁 / Dual-Mode Unit & Clean-Only Gates

- **本地供体模式 / Local Donor Mode** (`PYTHONPATH=outputs/fx3-vm-trial PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm-trial/tests`): **399 / 399 PASSED**（含新增 32 项 `test_phase129_mxf_ptpv2_tsl_tally.py`）
- **洁净室模式 / Clean-Room Mode** (`FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm-trial PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm-trial/tests`): **399 / 399 PASSED**（`skipped=2` 仅限于既有供体语言包校验项，Phase 129 全部 32/32 通过）
- **全仓干净测试门禁 / Lab Clean-Only Gate** (`PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only`): 全部通过，仓库内零 `.o`、`.elf`、`.cpio`、`.pyc` 残留。

---

## 4. 变更文件清单 / Owned Files

1. [outputs/fx3-vm-trial/src/fx6_live_guest.c](../../outputs/fx3-vm-trial/src/fx6_live_guest.c)
2. [outputs/fx3-vm-trial/run_fx6_menu_trial.py](../../outputs/fx3-vm-trial/run_fx6_menu_trial.py)
3. [outputs/fx3-vm-trial/README.md](../../outputs/fx3-vm-trial/README.md)
4. [outputs/fx3-vm-trial/tests/test_phase129_mxf_ptpv2_tsl_tally.py](../../outputs/fx3-vm-trial/tests/test_phase129_mxf_ptpv2_tsl_tally.py)
5. [reports/2026-11-14-phase129-vm-trial-mxf-ptpv2-tsl-tally/README.md](README.md)
